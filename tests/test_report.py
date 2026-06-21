import sys
import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEventLoop, QTimer

from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.agents.report.report_agent import (
    ReportAgent,
    ReportWorker,
    build_report_prompt,
    REPORT_MODEL,
    REPORT_TIMEOUT_SEC,
)

SAMPLE_REPORT = (
    "# 분기 전략 회의록\n\n"
    "## 회의 요약\n핵심 결론은 신규 시장 진출입니다.\n\n"
    "## 최종 Mermaid 소스\n```mermaid\ngraph TD\nA-->B\n```\n\n"
    "## Todo\n- [ ] 시장 조사 (담당: Speaker_01)\n"
)


def _seed_session(db: DatabaseManager, session_id: str = "report_test_001") -> str:
    """보고서 생성에 필요한 회의 세션/발화/채팅 더미 데이터를 적재합니다."""
    db.create_session(session_id, title="분기 전략 회의", start_time="2026-06-20T10:00:00")
    db.add_transcript(session_id, "Speaker_00", "올해 목표를 정합시다.", 0.0, 2.0)
    db.add_transcript(session_id, "Speaker_01", "신규 시장 진출이 우선입니다.", 2.0, 4.0)
    db.add_chat_log(session_id, "결정된 사항은 무엇인가요?", "신규 시장 진출", 1234567.0)
    # 회의 종료 시각을 먼저 기록 (실제 end_meeting 흐름과 동일)
    db.end_session(session_id, end_time="2026-06-20T11:00:00")
    return session_id


def test_build_report_prompt_merges_all_context():
    """프롬프트에 발화록·채팅·Mermaid·기본정보가 모두 융합되는지 검증합니다."""
    session = {"session_id": "s1", "title": "전략 회의", "start_time": "10:00", "end_time": "11:00"}
    transcripts = [{"speaker": "Speaker_00", "text": "첫 번째 발화입니다."}]
    chat_logs = [{"query": "질문입니다.", "response": "답변입니다."}]
    mermaid = "graph TD\nX-->Y"

    prompt = build_report_prompt(session, transcripts, chat_logs, mermaid)

    assert "전략 회의" in prompt
    assert "첫 번째 발화입니다." in prompt
    assert "질문입니다." in prompt
    assert "답변입니다." in prompt
    assert "graph TD\nX-->Y" in prompt
    # 작성 규칙 가이드라인이 포함되어 있어야 함
    assert "회의 요약" in prompt
    assert "Todo 리스트" in prompt


def test_build_report_prompt_handles_empty_context():
    """데이터가 비어 있어도 예외 없이 안내 문구로 대체되는지 검증합니다."""
    prompt = build_report_prompt({}, [], [], "")
    assert "전사된 발화 내용이 없습니다" in prompt
    assert "질의응답 내역이 없습니다" in prompt
    assert "생성된 흐름도가 없습니다" in prompt


def test_report_worker_full_pipeline(temp_config):
    """워커 동기 실행으로 CLI 인자·파일 저장·DB summary·startfile 호출을 엄격 검증합니다."""
    db = DatabaseManager(temp_config.db_path)
    session_id = _seed_session(db)

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    mock_cli.execute_command.return_value = SAMPLE_REPORT

    mermaid_code = "graph TD\nStart-->End"
    worker = ReportWorker(mock_cli, db, temp_config, session_id, mermaid_code)

    with patch("prismflow.agents.report.report_agent.os.startfile", create=True) as mock_start:
        worker.run()  # QThread.run()을 직접 호출하여 동기적으로 결정성 있게 검증

    # 1. Claude CLI 호출 인자 검증 (Opus 4.8, timeout 120, 컨텍스트 병합)
    assert mock_cli.execute_command.call_count == 1
    kwargs = mock_cli.execute_command.call_args.kwargs
    assert kwargs["model"] == REPORT_MODEL == "claude-opus-4-8"
    assert kwargs["timeout"] == REPORT_TIMEOUT_SEC == 120
    prompt = kwargs["prompt"]
    assert "올해 목표를 정합시다." in prompt
    assert "신규 시장 진출이 우선입니다." in prompt
    assert "결정된 사항은 무엇인가요?" in prompt
    assert "graph TD\nStart-->End" in prompt

    # 2. 날짜별 폴더 구조 + UTF-8 파일 저장 검증
    today = datetime.date.today().strftime("%Y-%m-%d")
    expected = Path(temp_config.docs_save_dir) / today / f"report_{session_id}.md"
    assert expected.exists()
    assert expected.read_text(encoding="utf-8") == SAMPLE_REPORT

    # 3. DB summary 업데이트 + 원본 end_time 보존 검증
    sess = db.get_session(session_id)
    assert sess["summary"] == SAMPLE_REPORT
    assert sess["end_time"] == "2026-06-20T11:00:00"

    # 4. os.startfile 호출 검증 (Windows 한정 — 가드 동작 확인)
    if sys.platform == "win32":
        mock_start.assert_called_once_with(str(expected))


def test_report_worker_emits_error_on_empty_response(temp_config):
    """CLI가 빈 응답을 반환하면 파일을 쓰지 않고 error 시그널을 방출하는지 검증합니다."""
    db = DatabaseManager(temp_config.db_path)
    session_id = _seed_session(db, "report_test_empty")

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    mock_cli.execute_command.return_value = "   "  # 공백만 반환

    errors = []
    worker = ReportWorker(mock_cli, db, temp_config, session_id, "graph TD")
    worker.error.connect(errors.append)

    with patch("prismflow.agents.report.report_agent.os.startfile", create=True):
        worker.run()

    assert len(errors) == 1
    today = datetime.date.today().strftime("%Y-%m-%d")
    not_expected = Path(temp_config.docs_save_dir) / today / f"report_{session_id}.md"
    assert not not_expected.exists()


def test_report_agent_triggered_by_meeting_ended(q_app, temp_config):
    """meeting_ended 시그널이 ReportAgent → ReportWorker 파이프라인을 가동하는지 검증합니다."""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)

    context.start_meeting("report_agent_wire", "배선 테스트")
    context.add_transcript("Speaker_00", "테스트 발화입니다.")
    context.update_mermaid_code("graph TD\nA-->B")

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.config = temp_config
    mock_cli.is_session_limited.return_value = False
    mock_cli.execute_command.return_value = SAMPLE_REPORT

    agent = ReportAgent(context=context, cli_controller=mock_cli)

    generated = []
    agent.report_generated.connect(generated.append)

    with patch("prismflow.agents.report.report_agent.os.startfile", create=True):
        context.end_meeting()  # meeting_ended 방출 → 워커 비동기 가동

        loop = QEventLoop()
        for _ in range(40):
            if generated:
                break
            QTimer.singleShot(50, loop.quit)
            loop.exec()

    assert len(generated) == 1

    expected = Path(temp_config.output_dir) / "report_agent_wire" / "report_report_agent_wire.md"
    assert expected.exists()
    assert expected.read_text(encoding="utf-8") == SAMPLE_REPORT

    sess = context.db_manager.get_session("report_agent_wire")
    assert sess["summary"] == SAMPLE_REPORT

    agent.cleanup()
    context.reset()
