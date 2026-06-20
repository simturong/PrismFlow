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
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker

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
        
        # 에이전트 및 검출기 홀더
        self.stt_worker = None
        self.flow_agent = None
        self.screen_detector = None
        
        # 싱글톤 컨텍스트 상태 변화 연결
        self.context.signals.meeting_started.connect(self._on_meeting_started)
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)
        
        # 오버레이 초기 위치 배치 (화면 우측 상단 여백)
        screen = self.app.primaryScreen().geometry()
        x = screen.width() - self.flow_ui.width() - 40
        y = 50
        self.flow_ui.move(x, y)
        self.flow_ui.show()

    def _on_meeting_started(self, session_id: str):
        logger.info(f"Meeting session {session_id} started. Launching Phase 3 agents...")
        
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
        self.stt_worker.start()

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
            
        # UI 초기 메시지 리셋
        self.flow_ui.web_view.setHtml(self.flow_ui.web_view.page().html() or "")

def main():
    app = QApplication(sys.argv)
    
    # 트레이 호환성 검증
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "오류", "시스템 트레이가 지원되지 않는 환경입니다.")
        sys.exit(1)
        
    app.setQuitOnLastWindowClosed(False)
    
    # 코디네이터 기동
    coordinator = AppCoordinator(app)
    coordinator.tray.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
