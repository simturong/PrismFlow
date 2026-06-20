import os
import base64
import logging
from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from prismflow.ui_common.overlay import TranslucentOverlay
from prismflow.agents.flow.mermaid_html import get_mermaid_html

logger = logging.getLogger(__name__)

# setHtml에 file:// baseUrl을 주어야 페이지 origin이 로컬 콘텐츠로 인식되어
# `<script src="file:///.../mermaid.min.js">` 로컬 번들이 로드된다.
# (baseUrl 없이 setHtml하면 origin이 about:blank가 되어 QWebEngine이 file:// 서브리소스를 차단)
_RESOURCES_BASE_URL = QUrl.fromLocalFile(str(Path(__file__).parent / "resources") + os.sep)

class FlowUI(TranslucentOverlay):
    """QWebEngineView를 탑재하여 오프라인 Mermaid.js 다이어그램을 동적으로 렌더링하는 투명 오버레이 GUI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PrismFlow - Meeting Map")
        self.resize(700, 550)
        
        # 내부 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # QWebEngineView 생성 및 설정
        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        
        # 웹페이지 배경 투명 설정 (Glassmorphism이 제대로 비쳐 보이도록)
        page = self.web_view.page()
        page.setBackgroundColor(Qt.transparent)
        
        # HTML 로드 (로컬 mermaid.min.js 로드를 위해 file:// baseUrl 지정)
        self.web_view.setHtml(get_mermaid_html(), _RESOURCES_BASE_URL)
        layout.addWidget(self.web_view)
        
    def reset_diagram(self):
        """회의 종료 시 흐름도 오버레이를 초기 안내 화면으로 되돌립니다."""
        self.web_view.setHtml(get_mermaid_html(), _RESOURCES_BASE_URL)

    def update_diagram(self, mermaid_code: str):
        """새로운 Mermaid 코드를 수신하여 깜빡임 없이 동적으로 렌더링합니다.
        
        JS 이스케이프 버그 방지를 위해 Python 단에서 Base64 인코딩 후
        자바스크립트 updateDiagram() 인터페이스에 전송합니다.
        """
        if not mermaid_code.strip():
            return
            
        try:
            logger.debug("Updating flow diagram with new Mermaid code...")
            # UTF-8 바이트 -> Base64 바이트 -> 디코딩 문자열
            encoded_bytes = base64.b64encode(mermaid_code.encode('utf-8'))
            encoded_str = encoded_bytes.decode('utf-8')
            
            # JS 호출
            js_script = f"updateDiagram('{encoded_str}')"
            self.web_view.page().runJavaScript(js_script)
        except Exception as e:
            logger.error(f"Failed to update Mermaid diagram: {str(e)}")
