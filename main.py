import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PySide6.QtCore import Qt

from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.screen_detector import ScreenTransitionDetector
from prismflow.ui_common.tray import SystemTrayManager
from prismflow.agents.flow.flow_ui import FlowUI
from prismflow.agents.flow.flow_agent import FlowAgent
from prismflow.agents.chat.chat_agent import ChatAgent
from prismflow.agents.chat.chat_ui import ChatUI
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.report.report_agent import ReportAgent

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PrismFlowMain")

class AppCoordinator:
    """회의 라이프사이클에 따라 에이전트와 UI 스레드를 오케스트레이션하는 전체 관리자 클래스."""
    
    def __init__(self, app: QApplication):
        self.app = app
        self.config = AppConfig.load_default()
        self.context = MeetingContext()
        self.cli_controller = ClaudeCLIController(self.config)
        
        # UI 컴포넌트
        self.tray = SystemTrayManager()
        self.flow_ui = FlowUI()
        
        # Chat Agent 및 UI 기동
        self.chat_agent = ChatAgent(self.context, self.cli_controller)
        self.chat_ui = ChatUI(self.chat_agent)

        # Report Agent 기동 (회의 종료 시 최종 회의록 자동 컴파일)
        self.report_agent = ReportAgent(self.context, self.cli_controller)
        self.report_agent.report_generated.connect(self._on_report_generated)
        self.report_agent.error_occurred.connect(self._on_report_error)

        # 에이전트 및 검출기 홀더
        self.stt_worker = None
        self.flow_agent = None
        self.screen_detector = None
        
        # 싱글톤 컨텍스트 상태 변화 연결
        self.context.signals.meeting_started.connect(self._on_meeting_started)
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)
        self.context.signals.transcript_updated.connect(self._on_transcript_updated)
        
        # 오버레이 초기 위치 배치
        screen = self.app.primaryScreen().geometry()
        
        # Flow UI (우측 상단)
        flow_x = screen.width() - self.flow_ui.width() - 40
        flow_y = 50
        self.flow_ui.move(flow_x, flow_y)
        self.flow_ui.show()
        
        # Chat UI (우측 하단)
        chat_x = screen.width() - self.chat_ui.width() - 40
        chat_y = screen.height() - self.chat_ui.height() - 100
        self.chat_ui.move(chat_x, chat_y)
        self.chat_ui.show()

    def _on_meeting_started(self, session_id: str):
        logger.info(f"Meeting session {session_id} started. Launching Phase 3 & 4 agents...")
        
        # 1. 스마트 화면 감지기 기동 (확인 테스트 편의를 위해 5.0초 디바운스로 설정)
        self.screen_detector = ScreenTransitionDetector(debounce_sec=5.0)
        self.screen_detector.transition_detected.connect(self._on_screen_transition)
        self.screen_detector.start()
        
        # 2. Flow Agent 기동 (30초마다 갱신)
        self.flow_agent = FlowAgent(self.context, self.cli_controller, check_interval_sec=30.0)
        self.flow_agent.diagram_updated.connect(self.flow_ui.update_diagram)
        self.flow_agent.start()
        
        # 3. STT Worker (Mock 발화 또는 Real 오디오 추론) 기동
        self.stt_worker = RealTimeEngineWorker()
        self.stt_worker.status_changed.connect(self._on_stt_status_changed)
        self.stt_worker.error_occurred.connect(self._on_stt_error)
        self.stt_worker.start()

    def _on_stt_status_changed(self, status: str):
        logger.info(f"STT Engine Status changed: {status}")
        if status == "loading":
            msg = "엔진 준비 중... (OpenVINO 로컬 가중치 로딩 중, 10~30초 소요)"
            self.flow_ui.update_status_text(f"⏳ {msg}")
            self.tray.setToolTip(f"PrismFlow AI Assistant - {msg}")
            self.tray.showMessage("PrismFlow", "STT 엔진을 백그라운드에서 초기화하는 중입니다. 마이크는 이미 캡처를 시작하여 로딩 중 발화도 안전하게 버퍼링됩니다.", QSystemTrayIcon.Information, 4000)
        elif status == "running":
            msg = "엔진 준비 완료. 음성 대기 중..."
            self.flow_ui.update_status_text(f"🎙️ {msg}")
            self.tray.setToolTip(f"PrismFlow AI Assistant - {msg}")
            self.tray.showMessage("PrismFlow", "STT 엔진 초기화가 완료되었습니다. 대화 내용을 실시간 인식합니다.", QSystemTrayIcon.Information, 3000)
        elif status == "idle":
            self.flow_ui.update_status_text("회의를 대기 중입니다.")
            self.tray.setToolTip("PrismFlow AI Assistant")
        elif status == "error":
            msg = "STT 엔진 오류 발생"
            self.flow_ui.update_status_text(f"❌ {msg} (설정 혹은 모델 존재를 확인하세요)")
            self.tray.setToolTip(f"PrismFlow AI Assistant - {msg}")

    def _on_stt_error(self, err_msg: str):
        logger.error(f"STT Worker Error: {err_msg}")
        self.tray.showMessage("PrismFlow 에러", err_msg, QSystemTrayIcon.Warning, 5000)

    def _on_transcript_updated(self, item: dict):
        speaker = item.get("speaker", "Speaker")
        text = item.get("text", "")
        self.flow_ui.show_subtitle(speaker, text)

    def _on_screen_transition(self, ttype: str, info: object):
        logger.info(f"Screen transition detected: Type={ttype}, Info={info}")
        self.context.update_screen_info(ttype, info)

    def _on_meeting_ended(self, session_id: str):
        logger.info(f"Meeting session {session_id} ended. Cleaning up agents...")
        
        # 1. STT Worker 종료
        if self.stt_worker:
            self.stt_worker.stop()
            self.stt_worker = None
            
        # 2. Flow Agent 종료
        if self.flow_agent:
            self.flow_agent.stop()
            self.flow_agent = None
            
        # 3. 화면 감지기 종료
        if self.screen_detector:
            self.screen_detector.stop()
            self.screen_detector = None
            
        # 흐름도 오버레이를 초기 안내 화면으로 리셋
        self.flow_ui.reset_diagram()

        # 참고: 최종 회의록 컴파일은 ReportAgent가 동일한 meeting_ended 신호를
        # 독립 구독하여 백그라운드 워커로 처리하므로 여기서 별도 호출은 불필요합니다.

    def _on_report_generated(self, filepath: str):
        logger.info(f"Final meeting report generated and opened: {filepath}")

    def _on_report_error(self, msg: str):
        logger.error(f"Failed to generate final meeting report: {msg}")

    def cleanup(self):
        """프로그램 종료 시 백그라운드 리소스와 스레드를 안전하게 정리합니다."""
        logger.info("Cleaning up coordinator resources...")
        if self.chat_agent:
            self.chat_agent.cleanup()
        if self.report_agent:
            self.report_agent.cleanup()
        if self.stt_worker:
            try:
                self.stt_worker.stop()
            except Exception:
                pass
        if self.flow_agent:
            try:
                self.flow_agent.stop()
            except Exception:
                pass
        if self.screen_detector:
            try:
                self.screen_detector.stop()
            except Exception:
                pass

def main():
    app = QApplication(sys.argv)
    
    # 로컬 Pretendard 폰트 로드 시도
    import os
    from PySide6.QtGui import QFontDatabase, QFont
    
    font_path = os.path.join(os.path.dirname(__file__), "prismflow", "resources", "Pretendard-Regular.ttf")
    font_family = "Segoe UI"
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                font_family = families[0]
                logger.info(f"Loaded local font: {font_family}")
    else:
        logger.debug("Local Pretendard font file not found. Fallback to system default fonts.")
        
    # 명시적 기본 폰트 및 포인트 크기 설정하여 QFont::setPointSize <= 0 (-1) 경고 방지
    app_font = QFont(font_family)
    app_font.setPointSize(9)
    app.setFont(app_font)
    
    # 트레이 호환성 검증
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "오류", "시스템 트레이가 지원되지 않는 환경입니다.")
        sys.exit(1)
        
    app.setQuitOnLastWindowClosed(False)
    
    # 코디네이터 기동
    coordinator = AppCoordinator(app)
    coordinator.tray.show()
    
    # 종료 시 자원 회수 핸들러 등록
    app.aboutToQuit.connect(coordinator.cleanup)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
