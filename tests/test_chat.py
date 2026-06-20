import pytest
import time
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QEventLoop, QTimer

from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.agents.chat.chat_agent import ChatAgent
from prismflow.agents.chat.chat_ui import ChatUI, markdown_to_html

def test_markdown_to_html():
    """마크다운 변환 함수 동작 테스트"""
    md = "# Hello\nThis is **bold** and `code`.\n```python\nprint(123)\n```"
    html_res = markdown_to_html(md)
    assert "Hello" in html_res
    assert "bold" in html_res
    assert "code" in html_res
    assert "print(123)" in html_res
    assert "background-color" in html_res

def test_chat_ui_init(q_app, temp_config):
    """ChatUI 기본 초기화 및 메인 레이블, 컴포넌트 검증"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    
    agent = ChatAgent(context=context, ingest_interval_ms=100)
    ui = ChatUI(agent=agent)
    
    assert ui.windowTitle() == "PrismFlow - AI Assistant"
    assert ui.chat_history is not None
    assert ui.input_field is not None
    assert ui.loading_label is not None
    
    ui.close()
    context.reset()

def test_chat_agent_ingestion_free_on_meeting_start(temp_config):
    """(Phase 9-4) 회의 시작 시 백그라운드 CLI 주입 없이 세션 초기화 신호만 방출되는지 검증.

    3분 주기 IngestWorker가 폐지되었으므로, 회의가 시작돼도 execute_command/stream 호출은
    0회여야 하며(Ingestion-free), 대신 session_initialized 신호로 UI 입력창이 열려야 한다.
    """
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)

    context.start_meeting("session_test_ingest_free", "주입 없는 세션")
    context.add_transcript("Speaker_00", "첫 번째 발화입니다.")
    context.add_transcript("Speaker_01", "두 번째 발화입니다.")

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False

    agent = ChatAgent(context=context, cli_controller=mock_cli)

    initialized = []
    agent.session_initialized.connect(lambda: initialized.append(True))

    # 회의 시작 신호를 다시 발생시켜 세션 초기화 경로를 트리거
    agent.on_meeting_started(context.current_session_id)

    # 비동기 이벤트를 흘려보냄 (혹시 모를 백그라운드 주입이 일어나는지 관찰)
    loop = QEventLoop()
    QTimer.singleShot(150, loop.quit)
    loop.exec()

    # 1. 백그라운드 CLI 주입이 전혀 발생하지 않아야 함 (Ingestion-free One-shot 구조)
    assert mock_cli.execute_command.call_count == 0
    assert mock_cli.execute_command_stream.call_count == 0
    # 2. 세션 초기화 신호가 방출되어 UI 입력창이 열릴 수 있어야 함
    assert initialized == [True]
    # 3. 주기적 주입 인덱스는 갱신되지 않고 초기값(-1)을 유지해야 함
    assert agent.last_ingested_idx == -1

    context.end_meeting()
    context.reset()

def test_chat_agent_qna_and_unsubmitted_merge(temp_config):
    """질문 시점의 미주입 실시간 잔여 발화와 쿼리 병합 및 스트리밍 테스트"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_qna", "QNA 테스트")
    
    context.add_transcript("Speaker_00", "주입할 첫 번째 대화")
    
    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    
    def fake_stream(prompt, session_id, model, system_prompt=None):
        yield "이것은 "
        yield "답변"
        yield "입니다."
        
    mock_cli.execute_command_stream = fake_stream
    
    # 주기는 50000ms로 길게 설정하여 백그라운드 주입 타이머 실행을 지연
    agent = ChatAgent(context=context, cli_controller=mock_cli, ingest_interval_ms=50000)
    agent.last_ingested_idx = -1
    
    delivered_tokens = []
    agent.token_delivered.connect(delivered_tokens.append)
    
    qna_finished = False
    final_resp = ""
    def on_finished(resp):
        nonlocal qna_finished, final_resp
        qna_finished = True
        final_resp = resp
        
    agent.finished.connect(on_finished)
    
    # 질문 실행
    agent.ask_question("이 회의의 주제는 무엇인가요?")
    
    # QThread 실행 대기
    loop = QEventLoop()
    for _ in range(20):
        if qna_finished:
            break
        QTimer.singleShot(50, loop.quit)
        loop.exec()
        
    assert qna_finished is True
    assert final_resp == "이것은 답변입니다."
    assert delivered_tokens == ["이것은 ", "답변", "입니다."]
    assert agent.last_ingested_idx == 0
    
    # DB 저장 확인
    chat_logs = context.db_manager.get_chat_logs("session_test_qna")
    assert len(chat_logs) == 1
    assert chat_logs[0]['query'] == "이 회의의 주제는 무엇인가요?"
    assert chat_logs[0]['response'] == "이것은 답변입니다."
    
    context.end_meeting()
    context.reset()

def test_chat_ui_integration(q_app, temp_config):
    """UI와 Agent의 스트리밍 통합 및 컴포넌트 잠금/활성화 상태 테스트"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_ui", "UI 통합 테스트")
    
    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    
    def fake_stream(prompt, session_id, model, system_prompt=None):
        yield "안녕"
        yield "하세요"
        
    mock_cli.execute_command_stream = fake_stream
    
    agent = ChatAgent(context=context, cli_controller=mock_cli, ingest_interval_ms=50000)
    ui = ChatUI(agent=agent)
    ui.show()  # 윈도우를 띄워야 자식 위젯의 isVisible()이 정상 작동합니다.
    
    ui.input_field.setText("안녕?")
    ui.send_query()
    
    # 입력 비활성화 및 로딩 레이블 표시 확인
    assert ui.input_field.isEnabled() is False
    assert ui.loading_label.isVisible() is True

    
    # QThread 작업 대기
    loop = QEventLoop()
    for _ in range(20):
        if ui.input_field.isEnabled():
            break
        QTimer.singleShot(50, loop.quit)
        loop.exec()
        
    assert ui.input_field.isEnabled() is True
    assert ui.loading_label.isVisible() is False
    assert "안녕하세요" in ui.chat_history.toPlainText()
    
    ui.close()
    context.end_meeting()
    context.reset()

def test_chat_agent_cleanup(temp_config):
    """(Phase 9-4) ChatAgent.cleanup이 활성 Q&A 워커를 안전하게 합류·종료하는지 검증.

    ingest_timer가 폐지되었으므로 cleanup은 그 참조 없이도 예외 없이 완료되어야 하며,
    진행 중인 ChatQNAWorker(QThread)를 wait()로 안전하게 종료한 뒤 active_workers를 비워야 한다.
    """
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_cleanup", "클린업 테스트")

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False

    # Q&A 스트림이 잠시 지속되도록 가짜 스트림 구성 (cleanup이 실제로 합류 대기하는지 확인)
    def fake_stream(prompt, session_id, model, system_prompt=None):
        for _ in range(3):
            time.sleep(0.05)
            yield "토큰"
    mock_cli.execute_command_stream = fake_stream

    agent = ChatAgent(context=context, cli_controller=mock_cli)

    # 질문을 던져 QNA 워커 1개를 기동
    agent.ask_question("정리 대상 질문")
    assert len(agent.active_workers) == 1
    worker = agent.active_workers[0]

    # cleanup 호출 (ingest_timer 참조 없이 정상 동작해야 함)
    agent.cleanup()

    assert len(agent.active_workers) == 0
    assert worker.isRunning() is False

    context.end_meeting()
    context.reset()

def test_chat_ui_initial_lock_and_unlock(q_app, temp_config):
    """UI 초기화 시 입력창이 잠기고 session_initialized에 의해 열리는지 검증"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_lock", "잠금 테스트")
    
    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    
    agent = ChatAgent(context=context, cli_controller=mock_cli, ingest_interval_ms=50000)
    ui = ChatUI(agent=agent)
    ui.show()
    
    # 처음에 입력창이 비활성화 상태이고 초기화 메시지가 떠 있는지 확인
    assert ui.input_field.isEnabled() is False
    assert "준비하고 있습니다" in ui.chat_history.toPlainText()
    
    # 강제로 세션 초기화 완료 시그널 발생시킴
    agent.session_initialized.emit()
    
    # 입력창 활성화 확인
    assert ui.input_field.isEnabled() is True
    assert "활성화되었습니다" in ui.chat_history.toPlainText()
    
    ui.close()
    context.end_meeting()
    context.reset()

