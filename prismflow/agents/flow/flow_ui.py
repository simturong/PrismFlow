import os
import re
import base64
import html
import logging
from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextBrowser, QLabel
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

# 헤드라인 핵심어 강조용 숫자/날짜/수량 토큰 패턴 (예: 30%, 2026년, 3일, 5개, 1,200, 12:30, 3.5억)
# 한글 단위/접미어를 함께 묶어 '5개', '2026년'처럼 의미 단위로 강조한다.
_NUMERIC_PATTERN = (
    r"\d[\d,\.:]*\s?%"                       # 퍼센트
    r"|\d[\d,\.:]*\s?(?:년|월|일|시|분|초|개|명|건|원|억|만|천|배|차|위|등|km|kg|m|cm)"  # 수량+단위
    r"|\d[\d,\.:]*\d|\d"                     # 일반 숫자(천단위/소수/시각 포함)
)


class FlowUI(TranslucentOverlay):
    """흐름도(블록도)가 세로의 ~90%를 차지하고, 그 아래 얇은 확정 전사 스트립 + 한 줄 에이전트 상태를 둔 투명 오버레이.

    창 이름은 'PrismFlow Agent'로, 좌상단에 떠 있는 라벨로 표기한다.
    """

    def __init__(self, hub=None, parent=None, chat_panel=None):
        super().__init__(parent)
        self.setWindowTitle("PrismFlow Agent")
        self.hub = hub
        self.chat_panel = chat_panel
        self._transcript_lines = []
        self._interim_text = ""

        # 좌측 Flow 콘텐츠를 담는 컨테이너. (chat_panel이 주어지면 우측에 분할 배치)
        left = QWidget(self)
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # [0] 뉴스 요약 자막바 (News Headline Label) — 중앙정렬·대형 폰트(2배)·핵심어 색강조
        self.headline_label = QLabel("회의 흐름을 실시간 요약 중입니다...", self)
        self.headline_label.setFixedHeight(56)
        self.headline_label.setWordWrap(True)
        self.headline_label.setAlignment(Qt.AlignCenter)
        self.headline_label.setTextFormat(Qt.RichText)
        self.headline_label.setStyleSheet(
            "background-color: rgba(124, 77, 255, 30);"
            "color: #ffcc00;"
            "border: 1px solid rgba(124, 77, 255, 60);"
            "border-radius: 4px;"
            "padding: 2px 10px;"
            "font-family: 'Pretendard', sans-serif;"
            "font-size: 26px;"
            "font-weight: bold;"
        )
        layout.addWidget(self.headline_label, 0)

        # [1] Mermaid 차트 — QWebEngineView. 유일한 신축(stretch) 영역이라 늘어난 세로 공간을 거의 다 흡수한다.
        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.page().setBackgroundColor(Qt.transparent)
        self.web_view.setHtml(get_mermaid_html(), _RESOURCES_BASE_URL)
        layout.addWidget(self.web_view, 1)

        # [2] 확정 전사 기록 — 얇은 스트립(높이 85px 확대)
        self.transcript_view = QTextBrowser(self)
        self.transcript_view.setStyleSheet(_TRANSCRIPT_STYLE)
        self.transcript_view.setMaximumHeight(85)
        layout.addWidget(self.transcript_view, 0)

        # [3] 에이전트 상태 대시보드 — 한 줄(가로) 최소 높이
        self.status_panel = AgentStatusPanel(hub=hub, parent=self)
        self.status_panel.setFixedHeight(28)
        layout.addWidget(self.status_panel, 0)

        # 외곽 좌/우 분할: 좌=Flow 콘텐츠(stretch), [토글], 우=Chat 패널(옵션, 접기/펼치기)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 32, 10, 8)
        outer.setSpacing(6)
        outer.addWidget(left, 1)

        if self.chat_panel is not None:
            # 얇은 세로 토글 핸들 ( '>' 접기 / '<' 펼치기 )
            self.chat_toggle_btn = QPushButton("›", self)
            self.chat_toggle_btn.setFixedWidth(18)
            self.chat_toggle_btn.setToolTip("채팅 패널 접기/펼치기")
            self.chat_toggle_btn.setStyleSheet(
                "QPushButton { background: rgba(124,77,255,0.18); color:#e2e8f0;"
                " border:1px solid rgba(255,255,255,0.10); border-radius:6px; font-size:14px; font-weight:bold; }"
                " QPushButton:hover { background: rgba(124,77,255,0.40); }"
            )
            self.chat_toggle_btn.clicked.connect(self.toggle_chat_panel)
            outer.addWidget(self.chat_toggle_btn, 0)

            self.chat_panel.setFixedWidth(420)
            outer.addWidget(self.chat_panel, 0)
            self.resize(700 + 18 + 420, 680)
        else:
            self.chat_toggle_btn = None
            self.resize(700, 680)

        # 좌상단에 떠 있는 창 이름(레이아웃 공간을 차지하지 않도록 절대 배치) — 흐름도 90% 확보에 기여
        self.title_label = QLabel("PrismFlow Agent", self)
        self.title_label.setStyleSheet(
            "color: #e2e8f0; font-weight: bold; font-size: 12px; background: transparent;"
            " font-family: 'Segoe UI', Arial, sans-serif;"
        )
        self.title_label.move(16, 9)
        self.title_label.adjustSize()
        self.title_label.raise_()

        # 실시간 임시 전사 시그널 연동
        from prismflow.core.context import MeetingContext
        self.context = MeetingContext()
        self.context.signals.partial_transcript_updated.connect(self._on_partial_transcript_updated)

        self._render_transcripts()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 떠 있는 제목이 항상 보이도록 z-order 유지
        self.title_label.raise_()

    # -------------------- 확정 전사 기록 --------------------
    def _on_partial_transcript_updated(self, speaker: str, text: str):
        self._interim_text = text
        self._render_transcripts()

    def add_transcript(self, speaker: str, text: str):
        """확정된 전사 한 줄을 기록 뷰에 누적한다(최근 N개만 유지하여 비용 상한)."""
        self._interim_text = ""
        self._transcript_lines.append((speaker, text))
        if len(self._transcript_lines) > _MAX_TRANSCRIPT_LINES:
            self._transcript_lines = self._transcript_lines[-_MAX_TRANSCRIPT_LINES:]
        self._render_transcripts()

    def show_subtitle(self, speaker: str, text: str):
        """(하위호환) 라이브 자막 호출을 확정 전사 기록 누적으로 통합한다."""
        self.add_transcript(speaker, text)

    def _render_transcripts(self):
        rows = []
        for spk, txt in self._transcript_lines:
            rows.append(
                "<div style='margin:2px 0;'>"
                f"<span style='color:#00ffcc; font-weight:bold;'>[{html.escape(str(spk))}]</span> "
                f"<span style='color:#d6f5ec;'>{html.escape(str(txt))}</span></div>"
            )
        if self._interim_text:
            rows.append(
                "<div style='margin:2px 0; font-style:italic;'>"
                f"<span style='color:#a3b8cc; font-weight:bold;'>[말하는 중...]</span> "
                f"<span style='color:#a3b8cc;'>{html.escape(str(self._interim_text))}</span></div>"
            )
        if not rows:
            self.transcript_view.setHtml(
                "<div style='color:#5b6b78; font-size:11px;'>확정된 전사 기록이 여기에 표시됩니다.</div>"
            )
            return
        self.transcript_view.setHtml("\n".join(rows))
        sb = self.transcript_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    # -------------------- 채팅 패널 토글 --------------------
    def toggle_chat_panel(self):
        """우측 Chat 패널을 접고 펼친다(`›`/`‹`). 접으면 Flow가 전폭을 차지한다."""
        if self.chat_panel is None:
            return
        # isHidden(): 명시적으로 숨김 처리됐는지(창 표시 여부와 무관) → 토글 판정에 안전
        show = self.chat_panel.isHidden()
        self.set_chat_visible(show)

    def set_chat_visible(self, visible: bool):
        if self.chat_panel is None:
            return
        self.chat_panel.setVisible(visible)
        if self.chat_toggle_btn is not None:
            self.chat_toggle_btn.setText("›" if visible else "‹")
            self.chat_toggle_btn.setToolTip("채팅 패널 접기" if visible else "채팅 패널 펼치기")

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
        self.headline_label.setText("회의 흐름을 실시간 요약 중입니다...")

    def update_headline(self, text: str):
        """실시간 뉴스 헤드라인 자막을 핵심어 강조와 함께 갱신합니다."""
        if text:
            self.headline_label.setText(self._highlight_keywords(text))

    def _highlight_keywords(self, text: str) -> str:
        """핵심 단어(숫자·날짜·수량 + 회의 용어집 매칭어)를 색상 span으로 감싼 안전한 richtext를 만든다.

        규칙 기반(LLM 비의존)·결정적. 원문 위에서 단 한 번 스캔하여 매칭 구간만 강조하고 나머지는
        그대로 이스케이프하므로, 삽입된 마크업(색상 hex 등)을 재치환하는 사고가 없다.
        """
        hi = "<span style='color:#5eead4;'>{}</span>"  # 청록 강조

        # 회의 용어집(화면 추출 도메인 용어) — best-effort, 실패해도 무시
        try:
            terms = self.context._db_manager.get_glossary_terms() if self.context else None
        except Exception:
            terms = None
        # 숫자 패턴 + (긴 용어부터) 용어집 패턴을 하나의 alternation으로 결합해 단일 스캔
        pattern = _NUMERIC_PATTERN
        if terms:
            uniq = sorted({t for t in terms if t and len(t) >= 3}, key=len, reverse=True)
            if uniq:
                pattern += "|" + "|".join(re.escape(t) for t in uniq)
        combined = re.compile(pattern)

        out, last = [], 0
        for m in combined.finditer(text):
            out.append(html.escape(text[last:m.start()]))
            out.append(hi.format(html.escape(m.group(0))))
            last = m.end()
        out.append(html.escape(text[last:]))
        return "".join(out)

    def update_engine_mode(self, mode: str):
        """좌상단 타이틀 옆에 엔진 모드 (Claude 또는 Local)를 동적으로 표시합니다."""
        self.title_label.setText(f"PrismFlow Agent ({mode})")
        self.title_label.adjustSize()

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
