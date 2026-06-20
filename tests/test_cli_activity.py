import uuid
import pytest

from prismflow.core.cli_activity import (
    CliActivityLog, agent_label_for_session, get_cli_activity_log,
)
from prismflow.core.config import AppConfig
from prismflow.core.cli_controller import ClaudeCLIController


def test_agent_label_mapping():
    """원본 세션명 접두사로 호출 주체 에이전트를 식별한다."""
    assert agent_label_for_session("flow-session-20260101_010101") == "Flow"
    assert agent_label_for_session("chat-session-abc") == "Chat"
    assert agent_label_for_session("report-session-xyz") == "Report"
    assert agent_label_for_session(str(uuid.uuid4())) == "CLI"
    assert agent_label_for_session(None) == "CLI"


def test_activity_log_record_and_signal():
    """record가 엔트리를 보관하고 entry_added로 방출하는지 검증."""
    log = CliActivityLog()
    received = []
    log.entry_added.connect(received.append)

    log.record("flow-session-1", "claude-haiku-4-5", "프롬프트A", "응답A", "ok")
    log.record("chat-session-2", "claude-haiku-4-5", "프롬프트B", "에러B", "error")

    assert len(received) == 2
    assert received[0]["agent"] == "Flow"
    assert received[0]["kind"] == "ok"
    assert received[1]["agent"] == "Chat"
    assert received[1]["kind"] == "error"
    assert "time" in received[0]
    assert len(log.entries()) == 2

    log.clear()
    assert log.entries() == []


def test_activity_log_caps_entries():
    """보관 엔트리가 상한(_MAX_ENTRIES=300)을 넘지 않도록 가장 오래된 항목부터 버린다."""
    log = CliActivityLog()
    for i in range(350):
        log.record("flow-session-x", "m", f"p{i}", f"r{i}", "ok")
    entries = log.entries()
    assert len(entries) == 300
    # 가장 최근 항목이 남아 있어야 함
    assert entries[-1]["prompt"] == "p349"


def test_cli_controller_error_path_records_to_hub():
    """존재하지 않는 CLI 실행 실패가 전역 활동 로그에 'error'로 기록되는지 검증."""
    hub = get_cli_activity_log()
    hub.clear()

    config = AppConfig(db_path="non_existent_db_for_test.db",
                       claude_cli_cmd="invalid_non_existent_command_12345")
    controller = ClaudeCLIController(config)

    with pytest.raises(RuntimeError):
        controller.execute_command("Hello", session_id="flow-session-errcheck")

    entries = hub.entries()
    assert len(entries) >= 1
    last = entries[-1]
    assert last["agent"] == "Flow"
    assert last["kind"] == "error"
    hub.clear()


def test_cli_log_window_loads_and_filters(q_app):
    """CliLogWindow가 기존 엔트리를 로드하고, 신규 엔트리 수신·필터링을 처리하는지 검증."""
    from prismflow.ui_common.cli_log_window import CliLogWindow

    hub = get_cli_activity_log()
    hub.clear()
    hub.record("flow-session-1", "m", "flow 프롬프트", "flow 응답", "ok")

    win = CliLogWindow()
    # 초기 로드: 기존 1건이 본문에 보여야 함
    assert "flow 프롬프트" in win.view.toPlainText()

    # 신규 Chat 엔트리 수신 → 본문에 반영
    hub.record("chat-session-2", "m", "chat 프롬프트", "chat 응답", "ok")
    assert "chat 프롬프트" in win.view.toPlainText()

    # 필터를 Flow로 바꾸면 Chat 항목은 사라져야 함
    win.filter_combo.setCurrentText("Flow")
    text = win.view.toPlainText()
    assert "flow 프롬프트" in text
    assert "chat 프롬프트" not in text

    win.close()
    hub.clear()
