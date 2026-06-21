"""Phase 10: 에이전트 상태 대시보드 · 녹음 인디케이터 · FlowUI 3분할 레이아웃 검증."""
import pytest

from prismflow.core.agent_status import AgentStatusHub, AgentState, AGENTS
from prismflow.ui_common.indicators import RecordingIndicator
from prismflow.ui_common.status_panel import AgentStatusPanel, AgentBadge
from prismflow.agents.flow.flow_ui import FlowUI


# ----------------------- AgentStatusHub (코어, GUI 불필요) -----------------------

def test_hub_set_and_get_status_emits():
    hub = AgentStatusHub()
    events = []
    hub.status_changed.connect(lambda k, s, d: events.append((k, s, d)))

    hub.set_status("stt", AgentState.OK, "전사 3")
    assert hub.get_status("stt") == (AgentState.OK, "전사 3")
    assert events[-1] == ("stt", AgentState.OK, "전사 3")


def test_hub_dedupes_identical_status():
    hub = AgentStatusHub()
    events = []
    hub.status_changed.connect(lambda k, s, d: events.append((k, s, d)))

    hub.set_status("flow", AgentState.WORKING, "생성중")
    hub.set_status("flow", AgentState.WORKING, "생성중")  # 동일 → 재방출 안 함
    assert len(events) == 1


def test_hub_ignores_unknown_agent():
    hub = AgentStatusHub()
    events = []
    hub.status_changed.connect(lambda k, s, d: events.append((k, s, d)))
    hub.set_status("does_not_exist", AgentState.OK, "x")
    assert events == []


def test_hub_reset_all_returns_idle():
    hub = AgentStatusHub()
    hub.set_status("report", AgentState.OK, "완료")
    hub.reset_all()
    for key, _ in AGENTS:
        assert hub.get_status(key) == (AgentState.IDLE, "")


# ----------------------- RecordingIndicator -----------------------

def test_recording_indicator_toggle(q_app):
    ind = RecordingIndicator()
    assert ind.is_recording() is False
    assert ind._blink_timer.isActive() is False

    ind.set_recording(True)
    assert ind.is_recording() is True
    assert ind._blink_timer.isActive() is True

    ind.set_recording(False)
    assert ind.is_recording() is False
    assert ind._blink_timer.isActive() is False


# ----------------------- AgentStatusPanel -----------------------

def test_status_panel_has_all_five_agents(q_app):
    hub = AgentStatusHub()
    panel = AgentStatusPanel(hub=hub)
    assert set(panel.badges.keys()) == {"stt", "flow", "chat", "i2t", "report"}


def test_status_panel_updates_on_hub_signal(q_app):
    hub = AgentStatusHub()
    panel = AgentStatusPanel(hub=hub)

    hub.set_status("flow", AgentState.WORKING, "생성중")
    assert panel.badges["flow"].detail.text() == "생성중"

    hub.set_status("stt", AgentState.ERROR, "마이크")
    assert panel.badges["stt"].detail.text() == "마이크"
    # 오류 상태면 점 색이 빨강 계열로 반영되어야 함
    assert "#ef4444" in panel.badges["stt"].dot.styleSheet()


def test_badge_defaults_to_idle_label(q_app):
    badge = AgentBadge("stt", "STT")
    # 상세 없이 IDLE이면 기본 라벨('대기')을 표시
    assert badge.detail.text() == "대기"


# ----------------------- FlowUI 3분할 레이아웃 -----------------------

def test_flow_ui_three_pane_layout(q_app):
    hub = AgentStatusHub()
    ui = FlowUI(hub=hub)
    try:
        assert ui.web_view is not None
        assert ui.transcript_view is not None
        assert ui.status_panel is not None

        # 흐름도(블록도)만 신축(stretch) 영역이라 세로 공간 대부분(~90%)을 흡수한다.
        # 전사 스트립/상태 줄은 고정/캡 높이(stretch 0)로 최소화한다.
        lay = ui.layout()
        assert lay.count() == 3
        assert lay.stretch(0) == 1   # web_view(흐름도) — 유일한 신축 영역
        assert lay.stretch(1) == 0   # 전사 스트립 (고정 캡)
        assert lay.stretch(2) == 0   # 상태 한 줄 (고정)
        # 상태 패널은 한 줄 최소 높이로 고정
        assert ui.status_panel.maximumHeight() <= 32
        # 전사 스트립도 흐름도를 침범하지 않도록 낮게 제한
        assert ui.transcript_view.maximumHeight() <= 48
    finally:
        ui.close()


def test_flow_ui_transcript_accumulates_and_caps(q_app):
    ui = FlowUI()
    try:
        for i in range(60):
            ui.add_transcript("Speaker_00", f"발화 {i}")
        # 최근 50개로 상한이 걸려야 함
        assert len(ui._transcript_lines) == 50
        assert ui._transcript_lines[-1] == ("Speaker_00", "발화 59")

        # show_subtitle는 확정 전사 누적의 별칭으로 동작
        ui.show_subtitle("Speaker_01", "마지막 발화")
        assert ui._transcript_lines[-1] == ("Speaker_01", "마지막 발화")

        # reset_diagram은 전사 기록을 비운다
        ui.reset_diagram()
        assert ui._transcript_lines == []
    finally:
        ui.close()


def test_flow_ui_recording_and_status_wiring(q_app):
    hub = AgentStatusHub()
    ui = FlowUI(hub=hub)
    try:
        # 베이스 오버레이의 녹음 인디케이터 위임
        ui.set_recording(True)
        assert ui.recording_indicator.is_recording() is True
        ui.set_recording(False)
        assert ui.recording_indicator.is_recording() is False

        # 허브 상태가 패널 뱃지에 반영
        hub.set_status("report", AgentState.OK, "완료")
        assert ui.status_panel.badges["report"].detail.text() == "완료"
    finally:
        ui.close()
