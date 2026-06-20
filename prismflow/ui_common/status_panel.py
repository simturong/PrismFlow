"""에이전트 상태 대시보드 패널 (Phase 10).

AgentStatusHub의 status_changed 신호를 구독하여 5개 에이전트의 상태 뱃지를 실시간 갱신한다.
FlowUI 하단 1/6 영역에 배치되어, 각 에이전트가 정상 동작하는지 한눈에 점검할 수 있게 한다.
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QGridLayout, QLabel
from PySide6.QtCore import Qt

from prismflow.core.agent_status import AgentState, STATE_META, AGENTS


class AgentBadge(QWidget):
    """단일 에이전트 상태 뱃지: [색점] 이름  상세."""

    def __init__(self, key: str, label: str, parent=None):
        super().__init__(parent)
        self.key = key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        layout.setSpacing(5)

        self.dot = QLabel("●", self)
        self.name = QLabel(label, self)
        self.name.setStyleSheet(
            "color: #cbd5e1; font-size: 11px; font-weight: bold; background: transparent;"
            " font-family: 'Pretendard', 'Malgun Gothic', sans-serif;"
        )
        self.detail = QLabel("", self)
        self.detail.setStyleSheet(
            "color: #94a3b8; font-size: 10px; background: transparent;"
            " font-family: 'Pretendard', 'Malgun Gothic', sans-serif;"
        )
        self.detail.setWordWrap(False)

        layout.addWidget(self.dot)
        layout.addWidget(self.name)
        layout.addWidget(self.detail)
        layout.addStretch()

        self.set_state(AgentState.IDLE, "")

    def set_state(self, state: AgentState, detail: str = ""):
        meta = STATE_META.get(state, STATE_META[AgentState.IDLE])
        self.dot.setStyleSheet(f"color: {meta['color']}; font-size: 12px; background: transparent;")
        text = detail.strip() if detail else meta["label"]
        self.detail.setText(text)
        self.detail.setToolTip(text)


class AgentStatusPanel(QWidget):
    """5개 에이전트 상태 뱃지를 2열 그리드로 컴팩트하게 표시하는 패널."""

    def __init__(self, hub=None, parent=None):
        super().__init__(parent)
        self.hub = hub
        self.badges = {}

        root = QGridLayout(self)
        root.setContentsMargins(6, 4, 6, 4)
        root.setHorizontalSpacing(6)
        root.setVerticalSpacing(2)

        # 헤더
        header = QLabel("에이전트 상태", self)
        header.setStyleSheet(
            "color: #64748b; font-size: 9px; font-weight: bold; background: transparent;"
            " font-family: 'Pretendard', 'Malgun Gothic', sans-serif;"
        )
        root.addWidget(header, 0, 0, 1, 2)

        # 5개 뱃지를 2열 그리드로 배치 (1/6 높이에 맞춤)
        for i, (key, label) in enumerate(AGENTS):
            badge = AgentBadge(key, label, self)
            self.badges[key] = badge
            root.addWidget(badge, 1 + i // 2, i % 2)

        self.setStyleSheet(
            "AgentStatusPanel {"
            " background-color: rgba(15, 15, 20, 180);"
            " border: 1px solid rgba(255, 255, 255, 20);"
            " border-radius: 8px; }"
        )

        if hub is not None:
            hub.status_changed.connect(self.on_status_changed)
            for key, _ in AGENTS:
                st, detail = hub.get_status(key)
                self.badges[key].set_state(st, detail)

    def on_status_changed(self, key: str, state, detail: str):
        badge = self.badges.get(key)
        if badge is not None:
            badge.set_state(state, detail)
