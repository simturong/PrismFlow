"""CLI 디버그 로그 창 (개발용).

FlowAgent·ChatAgent·ReportAgent가 각자의 백그라운드 CLI 세션으로 claude에 주고받는
프롬프트/응답을 실시간으로 보여주는 개발 디버깅용 창이다. 전역 CliActivityLog 허브의
entry_added 신호를 구독하여 한 곳에 모아 표시한다.

(일반 오버레이가 아니라 표준 창 데코레이션을 가진 보조 창으로 둔다 — 디버깅 중 자유롭게
이동·최소화·크기조절하고 작업 표시줄에서 찾을 수 있어야 하기 때문이다.)
"""
import html
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QCheckBox, QTextBrowser,
)
from PySide6.QtCore import Qt

from prismflow.core.cli_activity import get_cli_activity_log

# 에이전트별 뱃지 색 (상태 패널과 톤을 맞춘 가독성 높은 색)
_AGENT_COLORS = {
    "Flow": "#38bdf8",
    "Chat": "#a78bfa",
    "Report": "#f59e0b",
    "CLI": "#94a3b8",
}
# 디버그 표시용 프롬프트/응답 최대 길이(메모리·렌더 비용 상한)
_MAX_FIELD_CHARS = 4000


class CliLogWindow(QWidget):
    """전역 CliActivityLog를 구독해 CLI 주고받기를 시간순으로 표시하는 디버그 창."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PrismFlow - CLI 디버그 로그")
        self.resize(640, 560)

        self._filter = "전체"
        self._entries = []  # 허브에서 수신한 엔트리 미러(필터 재렌더용)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # 상단 툴바: 안내 + 에이전트 필터 + 자동 스크롤 + 지우기
        toolbar = QHBoxLayout()
        title = QLabel("CLI 주고받기 (개발 디버깅용)", self)
        title.setStyleSheet("color: #e2e8f0; font-weight: bold; font-size: 12px;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        toolbar.addWidget(self._dim_label("에이전트"))
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItems(["전체", "Flow", "Chat", "Report", "CLI"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_combo)

        self.autoscroll_check = QCheckBox("자동 스크롤", self)
        self.autoscroll_check.setChecked(True)
        self.autoscroll_check.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        toolbar.addWidget(self.autoscroll_check)

        self.clear_btn = QPushButton("지우기", self)
        self.clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(self.clear_btn)
        root.addLayout(toolbar)

        # 본문: 로그 뷰
        self.view = QTextBrowser(self)
        self.view.setStyleSheet(
            "QTextBrowser { background-color: #0b0b10; color: #d6d6e0;"
            " border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px;"
            " font-family: 'Consolas', 'D2Coding', monospace; font-size: 11px; }"
        )
        root.addWidget(self.view)

        self.setStyleSheet(
            "CliLogWindow { background-color: #15151b; }"
            " QComboBox { background:#1e1e26; color:#e2e8f0; border:1px solid rgba(255,255,255,0.1);"
            " border-radius:4px; padding:2px 6px; font-size:11px; }"
            " QPushButton { background:#2a2a35; color:#e2e8f0; border:none; border-radius:4px;"
            " padding:4px 10px; font-size:11px; } QPushButton:hover { background:#3a3a48; }"
        )

        # 기존 누적분 로드 후 신규 엔트리 구독
        hub = get_cli_activity_log()
        for e in hub.entries():
            self._entries.append(e)
        self._render_all()
        hub.entry_added.connect(self._on_entry_added)

    def _dim_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self)
        lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        return lbl

    def _on_filter_changed(self, text: str):
        self._filter = text
        self._render_all()

    def _on_clear(self):
        get_cli_activity_log().clear()
        self._entries = []
        self.view.clear()

    def _on_entry_added(self, entry: dict):
        self._entries.append(entry)
        if len(self._entries) > 600:
            self._entries = self._entries[-600:]
        if self._matches(entry):
            self.view.append(self._format_entry(entry))
            self._maybe_autoscroll()

    def _matches(self, entry: dict) -> bool:
        return self._filter == "전체" or entry.get("agent") == self._filter

    def _render_all(self):
        blocks = [self._format_entry(e) for e in self._entries if self._matches(e)]
        self.view.setHtml("".join(blocks))
        self._maybe_autoscroll()

    def _maybe_autoscroll(self):
        if self.autoscroll_check.isChecked():
            sb = self.view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _format_entry(self, entry: dict) -> str:
        agent = entry.get("agent", "CLI")
        color = _AGENT_COLORS.get(agent, "#94a3b8")
        is_err = entry.get("kind") == "error"
        head_resp_color = "#ff6b6b" if is_err else "#7ee787"
        resp_label = "오류" if is_err else "응답"

        def trunc(s: str) -> str:
            s = s or ""
            if len(s) > _MAX_FIELD_CHARS:
                return s[:_MAX_FIELD_CHARS] + f"\n… (생략 {len(s) - _MAX_FIELD_CHARS}자)"
            return s

        prompt = html.escape(trunc(entry.get("prompt", "")))
        response = html.escape(trunc(entry.get("response", "")))
        pre = ("white-space: pre-wrap; word-wrap: break-word; margin: 2px 0 6px 0;"
               " padding: 4px 6px; background: rgba(255,255,255,0.03); border-radius: 4px;")
        return (
            "<div style='margin-top:8px; border-top:1px solid rgba(255,255,255,0.06); padding-top:6px;'>"
            f"<div><span style='color:#64748b;'>{html.escape(str(entry.get('time','')))}</span> "
            f"<b style='color:{color};'>[{html.escape(agent)}]</b> "
            f"<span style='color:#64748b;'>model={html.escape(str(entry.get('model','-')))}</span></div>"
            f"<div style='color:#7aa2f7; margin-top:2px;'>▶ 요청</div>"
            f"<div style='color:#c9d1d9; {pre}'>{prompt}</div>"
            f"<div style='color:{head_resp_color};'>◀ {resp_label}</div>"
            f"<div style='color:#c9d1d9; {pre}'>{response}</div>"
            "</div>"
        )
