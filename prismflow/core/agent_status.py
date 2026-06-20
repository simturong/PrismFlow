"""에이전트 동작 상태 집계 허브 (Phase 10).

5개 에이전트(STT·Flow·Chat·i2t·Report)의 실시간 동작 상태를 한 곳에서 집계하고,
구독 UI(AgentStatusPanel)로 신호 기반 푸시한다. 폴링이 없어 오버헤드가 사실상 0이며,
에이전트와 UI를 느슨하게 결합(decouple)하여 테스트가 용이하다.
"""
import logging
from enum import Enum
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """에이전트의 4단계 동작 상태."""
    IDLE = "idle"        # 대기/비활성
    OK = "ok"            # 정상 동작/직전 작업 성공
    WORKING = "working"  # 현재 처리 중(CLI 호출·추론 등)
    ERROR = "error"      # 직전 작업 실패(상세에 핵심 1단어)


# 상태별 표시 메타데이터 (색상 점 + 기본 라벨)
STATE_META = {
    AgentState.IDLE:    {"color": "#6b7280", "label": "대기"},
    AgentState.OK:      {"color": "#22c55e", "label": "정상"},
    AgentState.WORKING: {"color": "#38bdf8", "label": "작동"},
    AgentState.ERROR:   {"color": "#ef4444", "label": "오류"},
}

# 표시 순서 및 라벨 (key, 화면 표기)
AGENTS = [
    ("stt",    "STT"),
    ("flow",   "Flow"),
    ("chat",   "Chat"),
    ("i2t",    "i2t"),
    ("report", "Report"),
]
AGENT_KEYS = {k for k, _ in AGENTS}


class AgentStatusHub(QObject):
    """각 에이전트의 (상태, 상세) 를 보관하고 변경 시 status_changed로 방출한다."""

    # (agent_key, AgentState, detail_text)
    status_changed = Signal(str, object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._states = {k: (AgentState.IDLE, "") for k, _ in AGENTS}

    def set_status(self, agent_key: str, state: AgentState, detail: str = ""):
        """에이전트 상태를 갱신하고 구독자에게 방출한다. 동일 (상태, 상세)면 중복 방출하지 않는다."""
        if agent_key not in AGENT_KEYS:
            logger.warning(f"Unknown agent_key for status: {agent_key}")
            return
        detail = detail or ""
        if self._states.get(agent_key) == (state, detail):
            return
        self._states[agent_key] = (state, detail)
        self.status_changed.emit(agent_key, state, detail)

    def get_status(self, agent_key: str):
        """현재 (AgentState, detail) 튜플을 반환한다."""
        return self._states.get(agent_key, (AgentState.IDLE, ""))

    def reset_all(self):
        """모든 에이전트를 대기(IDLE) 상태로 되돌린다."""
        for k, _ in AGENTS:
            self.set_status(k, AgentState.IDLE, "")
