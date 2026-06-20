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

def test_chat_agent_background_ingestion(temp_config):
    """3분 주기 백그라운드 발화 주입 동작 및 last_ingested_idx 갱신 테스트"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_ingest", "주입 테스트")
    
    context.add_transcript("Speaker_00", "첫 번째 발화입니다.")
    context.add_transcript("Speaker_01", "두 번째 발화입니다.")
    
    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    
    # 50ms 마다 자동 주입 타이머 실행하도록 설정
    agent = ChatAgent(context=context, cli_controller=mock_cli, ingest_interval_ms=50)
    
    # 초기 비동기 이벤트를 흘려보냄
    loop = QEventLoop()
    QTimer.singleShot(150, loop.quit)
    loop.exec()
    
    # 호출 횟수 검증 (초기화 시 1회 + 신규 추가 발화 1회)
    assert mock_cli.execute_command.call_count >= 2
    
    calls = mock_cli.execute_command.call_args_list
    prompts = [c[1].get('prompt', '') or c[0][0] for c in calls]
    
    assert any("회의 챗 세션을 시작합니다." in p for p in prompts)
    assert any("첫 번째 발화입니다." in p for p in prompts)
    assert any("두 번째 발화입니다." in p for p in prompts)
    
    assert agent.last_ingested_idx == 1
    
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
    """ChatAgent.cleanup 호출 시 모든 비동기 워커가 안전하게 종료되는지 검증"""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("session_test_cleanup", "클린업 테스트")
    
    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    
    # agent 생성 시 최초 세션 연결을 위해 IngestWorker가 하나 기동됨
    agent = ChatAgent(context=context, cli_controller=mock_cli, ingest_interval_ms=50000)
    
    assert len(agent.active_workers) == 1
    worker = agent.active_workers[0]
    
    # cleanup 호출
    agent.cleanup()
    
    assert len(agent.active_workers) == 0
    assert agent.ingest_timer.isActive() is False
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

