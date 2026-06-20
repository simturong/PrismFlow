import os
import base64
import html
import logging
from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from prismflow.ui_common.overlay import TranslucentOverlay
from prismflow.ui_common.status_panel import AgentStatusPanel
from prismflow.agents.flow.mermaid_html import get_mermaid_html

logger = logging.getLogger(__name__)

# setHtml에 file:// baseUrl을 주어야 페이지 origin이 로컬 콘텐츠로 인식되어
# `<script src="file:///.../mermaid.min.js">` 로컬 번들이 로드된다.
_RESOURCES_BASE_URL = QUrl.fromLocalFile(str(Path(__file__).parent / "resources") + os.sep)

_TRANSCRIPT_STYLE = """
    QTextBrowser {
        background-color: rgba(10, 10, 15, 200);
        color: #d6f5ec;
        border: 1px solid rgba(0, 255, 200, 35);
        border-radius: 8px;
        padding: 4px 8px;
        font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
        font-size: 12px;
    }
    QScrollBar:vertical { border: none; background: rgba(0,0,0,0.1); width: 6px; margin: 0px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); min-height: 20px; border-radius: 3px; }
    QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.3); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

# 전사 기록 뷰에 보관할 최대 라인 수 (메모리/렌더 비용 상한)
_MAX_TRANSCRIPT_LINES = 50


class FlowUI(TranslucentOverlay):
    """Mermaid 차트(4/6) + 확정 전사 기록(1/6) + 에이전트 상태(1/6) 3분할 투명 오버레이 GUI."""

    def __init__(self, hub=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PrismFlow - Meeting Map")
        self.resize(700, 680)
        self.hub = hub
        self._transcript_lines = []

        # 내부 레이아웃: 세로 4 : 1 : 1 (Mermaid : 전사 기록 : 에이전트 상태)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 32, 10, 10)
        layout.setSpacing(6)

        # [1] Mermaid 차트 (4/6) — QWebEngineView
        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(Qt.transparent)
        self.web_view.setHtml(get_mermaid_html(), _RESOURCES_BASE_URL)
        layout.addWidget(self.web_view, 4)

        # [2] 확정 전사 기록 (1/6) — 누적 스크롤 뷰
        self.transcript_view = QTextBrowser(self)
        self.transcript_view.setStyleSheet(_TRANSCRIPT_STYLE)
        layout.addWidget(self.transcript_view, 1)

        # [3] 에이전트 상태 대시보드 (1/6)
        self.status_panel = AgentStatusPanel(hub=hub, parent=self)
        layout.addWidget(self.status_panel, 1)

        self._render_transcripts()

    # -------------------- 확정 전사 기록 --------------------
    def add_transcript(self, speaker: str, text: str):
        """확정된 전사 한 줄을 기록 뷰에 누적한다(최근 N개만 유지하여 비용 상한)."""
        self._transcript_lines.append((speaker, text))
        if len(self._transcript_lines) > _MAX_TRANSCRIPT_LINES:
            self._transcript_lines = self._transcript_lines[-_MAX_TRANSCRIPT_LINES:]
        self._render_transcripts()

    def show_subtitle(self, speaker: str, text: str):
        """(하위호환) 라이브 자막 호출을 확정 전사 기록 누적으로 통합한다."""
        self.add_transcript(speaker, text)

    def _render_transcripts(self):
        if not self._transcript_lines:
            self.transcript_view.setHtml(
                "<div style='color:#5b6b78; font-size:11px;'>확정된 전사 기록이 여기에 표시됩니다.</div>"
            )
            return
        rows = []
        for spk, txt in self._transcript_lines:
            rows.append(
                "<div style='margin:2px 0;'>"
                f"<span style='color:#00ffcc; font-weight:bold;'>[{html.escape(str(spk))}]</span> "
                f"<span style='color:#d6f5ec;'>{html.escape(str(txt))}</span></div>"
            )
        self.transcript_view.setHtml("\n".join(rows))
        sb = self.transcript_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # -------------------- 상태 / 다이어그램 --------------------
    def update_status_text(self, text: str):
        """(하위호환) 엔진 상태 텍스트를 STT 뱃지 상세에 반영한다(점 색 상태는 유지)."""
        badge = self.status_panel.badges.get("stt")
        if badge is not None:
            badge.detail.setText(text[:18])
            badge.detail.setToolTip(text)

    def reset_diagram(self):
        """회의 종료 시 흐름도와 전사 기록을 초기 상태로 되돌린다."""
        self.web_view.setHtml(get_mermaid_html(), _RESOURCES_BASE_URL)
        self._transcript_lines = []
        self._render_transcripts()

    def update_diagram(self, mermaid_code: str):
        """새 Mermaid 코드를 수신하여 깜빡임 없이 동적으로 렌더링한다.

        JS 이스케이프 버그 방지를 위해 Python 단에서 Base64 인코딩 후 updateDiagram()에 전달한다.
        """
        if not mermaid_code.strip():
            return
        try:
            logger.debug("Updating flow diagram with new Mermaid code...")
            encoded_str = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
            self.web_view.page().runJavaScript(f"updateDiagram('{encoded_str}')")
        except Exception as e:
            logger.error(f"Failed to update Mermaid diagram: {str(e)}")
