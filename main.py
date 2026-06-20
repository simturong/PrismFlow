import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PySide6.QtCore import Qt

from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.screen_detector import ScreenTransitionDetector
from prismflow.ui_common.tray import SystemTrayManager
from prismflow.ui_common.cli_log_window import CliLogWindow
from prismflow.agents.flow.flow_ui import FlowUI
from prismflow.agents.flow.flow_agent import FlowAgent
from prismflow.agents.chat.chat_agent import ChatAgent
from prismflow.agents.chat.chat_ui import ChatUI
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.report.report_agent import ReportAgent
from prismflow.core.agent_status import AgentStatusHub, AgentState

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
        
        # 에이전트 상태 집계 허브 (Phase 10) — 모든 에이전트 상태를 한 곳에 모아 UI 뱃지로 배포
        self.status_hub = AgentStatusHub()
        self._transcript_count = 0

        # UI 컴포넌트
        self.tray = SystemTrayManager()
        self.flow_ui = FlowUI(hub=self.status_hub)

        # Chat Agent 및 UI 기동
        self.chat_agent = ChatAgent(self.context, self.cli_controller)
        self.chat_ui = ChatUI(self.chat_agent)

        # Chat Agent 동작 상태를 허브에 반영 (자동 입출력/사용자 입력 수신 가시화)
        self.chat_agent.session_initialized.connect(
            lambda: self.status_hub.set_status("chat", AgentState.OK, "준비"))
        self.chat_agent.question_received.connect(
            lambda q: self.status_hub.set_status("chat", AgentState.WORKING, "질문수신"))
        self.chat_agent.token_delivered.connect(
            lambda t: self.status_hub.set_status("chat", AgentState.WORKING, "응답중"))
        self.chat_agent.finished.connect(
            lambda r: self.status_hub.set_status("chat", AgentState.OK, "응답완료"))
        self.chat_agent.error_occurred.connect(
            lambda e: self.status_hub.set_status("chat", AgentState.ERROR, self._first_word(e)))

        # CLI 디버그 로그 창 (개발용) — 백그라운드 에이전트들의 CLI 주고받기를 한 곳에서 관찰
        self.cli_log_window = CliLogWindow()

        # 트레이 매니저에 UI 핸들 주입
        self.tray.set_ui_handlers(self.flow_ui, self.chat_ui, self.cli_log_window)

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

        # 녹음(회의 진행) 인디케이터 점멸 시작 — 두 반투명 오버레이 모두 좌상단 표시
        self.flow_ui.set_recording(True)
        self.chat_ui.set_recording(True)

        # 에이전트 상태 초기화 (대시보드 뱃지)
        self._transcript_count = 0
        self.status_hub.set_status("stt", AgentState.WORKING, "기동")
        self.status_hub.set_status("flow", AgentState.IDLE, "대기")
        self.status_hub.set_status("i2t", AgentState.WORKING, "감지중")
        self.status_hub.set_status("report", AgentState.IDLE, "대기")

        # 1. 스마트 화면 감지기(i2t) 기동 (확인 테스트 편의를 위해 5.0초 디바운스로 설정)
        self.screen_detector = ScreenTransitionDetector(debounce_sec=5.0)
        self.screen_detector.transition_detected.connect(self._on_screen_transition)
        self.screen_detector.start()

        # 2. Flow Agent 기동 + 상태 가시화 신호 연결
        #    정기 갱신은 15초 주기, 단 직전 분석 이후 발화 3개 이상이 쌓이면(주제 전환 신호)
        #    8초 바닥 간격만 지키면 주기를 기다리지 않고 즉시 흐름도를 갱신한다(실시간성↑, CLI 폭주 방지).
        self.flow_agent = FlowAgent(self.context, self.cli_controller,
                                    check_interval_sec=15.0, burst_threshold=3, min_interval_sec=8.0)
        self.flow_agent.diagram_updated.connect(self.flow_ui.update_diagram)
        self.flow_agent.analysis_started.connect(
            lambda: self.status_hub.set_status("flow", AgentState.WORKING, "생성중"))
        self.flow_agent.diagram_updated.connect(
            lambda code: self.status_hub.set_status("flow", AgentState.OK, "갱신✓"))
        self.flow_agent.analysis_failed.connect(
            lambda e: self.status_hub.set_status("flow", AgentState.ERROR, "CLI오류"))
        self.flow_agent.start()

        # 3. STT Worker (Mock 발화 또는 Real 오디오 추론) 기동
        self.stt_worker = RealTimeEngineWorker()
        self.stt_worker.status_changed.connect(self._on_stt_status_changed)
        self.stt_worker.error_occurred.connect(self._on_stt_error)
        self.stt_worker.start()

    def _on_stt_status_changed(self, status: str):
        logger.info(f"STT Engine Status changed: {status}")
        if status == "loading":
            self.status_hub.set_status("stt", AgentState.WORKING, "로딩")
            self.tray.setToolTip("PrismFlow AI Assistant - 엔진 준비 중...")
            self.tray.showMessage("PrismFlow", "STT 엔진을 백그라운드에서 초기화하는 중입니다. 마이크는 이미 캡처를 시작하여 로딩 중 발화도 안전하게 버퍼링됩니다.", QSystemTrayIcon.Information, 4000)
        elif status == "running":
            # 정상 동작 + 교정 DB 정상 여부를 함께 표기 (DB 점검은 기동 시 1회만 수행 → 발화당 비용 없음)
            self.status_hub.set_status("stt", AgentState.OK, self._correction_db_detail())
            self.tray.setToolTip("PrismFlow AI Assistant - 음성 대기 중")
            self.tray.showMessage("PrismFlow", "STT 엔진 초기화가 완료되었습니다. 대화 내용을 실시간 인식합니다.", QSystemTrayIcon.Information, 3000)
        elif status == "idle":
            self.status_hub.set_status("stt", AgentState.IDLE, "대기")
            self.tray.setToolTip("PrismFlow AI Assistant")
        elif status == "error":
            self.status_hub.set_status("stt", AgentState.ERROR, "엔진오류")
            self.tray.setToolTip("PrismFlow AI Assistant - STT 엔진 오류 발생")

    def _on_stt_error(self, err_msg: str):
        logger.error(f"STT Worker Error: {err_msg}")
        # 비정상 동작 시 핵심 1단어 에러를 STT 뱃지에 표시
        self.status_hub.set_status("stt", AgentState.ERROR, self._first_word(err_msg))
        self.tray.showMessage("PrismFlow 에러", err_msg, QSystemTrayIcon.Warning, 5000)

    def _on_transcript_updated(self, item: dict):
        speaker = item.get("speaker", "Speaker")
        text = item.get("text", "")
        self.flow_ui.add_transcript(speaker, text)
        # 확정 전사 산출 → STT 정상 동작 표시(누적 카운트는 O(1) 로컬 카운터로 집계)
        self._transcript_count += 1
        self.status_hub.set_status("stt", AgentState.OK, f"전사 {self._transcript_count}")

    def _on_screen_transition(self, ttype: str, info: object):
        logger.info(f"Screen transition detected: Type={ttype}, Info={info}")
        self.context.update_screen_info(ttype, info)
        # i2t(화면감지)가 맥락을 컨텍스트에 전달 → 정상 동작 표시
        detail = f"PPT p{info[1]}" if ttype == "PPT" and isinstance(info, (list, tuple)) and len(info) >= 2 else "화면전환"
        self.status_hub.set_status("i2t", AgentState.OK, detail)

    def _on_meeting_ended(self, session_id: str):
        logger.info(f"Meeting session {session_id} ended. Cleaning up agents...")

        # 녹음 인디케이터 정지 — 두 오버레이 모두
        self.flow_ui.set_recording(False)
        self.chat_ui.set_recording(False)

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

        # 입력 생산 에이전트는 종료, 보고서는 비동기 생성 시작 상태로 표기
        self.status_hub.set_status("stt", AgentState.IDLE, "종료")
        self.status_hub.set_status("flow", AgentState.IDLE, "종료")
        self.status_hub.set_status("i2t", AgentState.IDLE, "종료")
        # 최종 회의록은 ReportAgent가 동일 meeting_ended 신호로 비동기 컴파일 → '생성중' 표기
        self.status_hub.set_status("report", AgentState.WORKING, "생성중")

        # 흐름도 오버레이를 초기 안내 화면으로 리셋
        self.flow_ui.reset_diagram()

    def _on_report_generated(self, filepath: str):
        logger.info(f"Final meeting report generated and opened: {filepath}")
        self.status_hub.set_status("report", AgentState.OK, "완료")

    def _on_report_error(self, msg: str):
        logger.error(f"Failed to generate final meeting report: {msg}")
        self.status_hub.set_status("report", AgentState.ERROR, self._first_word(msg))

    @staticmethod
    def _first_word(msg: str) -> str:
        """오류 메시지에서 핵심 1단어를 추출한다(뱃지 상세 표기용)."""
        if not msg:
            return "오류"
        keywords = ["마이크", "모델", "타임아웃", "커넥션", "한도", "권한", "네트워크", "세션"]
        for kw in keywords:
            if kw in msg:
                return kw
        parts = msg.strip().split()
        return parts[0][:8] if parts else "오류"

    def _correction_db_detail(self) -> str:
        """교정 DB 정상 동작 여부를 점검하여 STT 뱃지 상세 문구를 반환한다."""
        try:
            db = self.context.db_manager
            if db is not None:
                db.get_corrections()
                return "교정DB✓"
        except Exception:
            return "교정DB✗"
        return "정상"

    def cleanup(self):
        """프로그램 종료 시 백그라운드 리소스와 스레드를 안전하게 정리합니다.

        각 정리 단계를 개별 try/except로 격리하여, 한 에이전트의 정리 실패가 나머지 스레드
        종료를 가로막지 않도록 보장합니다. (스레드가 종료되지 못하고 누수되면 프로세스 종료 시점에
        SQLite 등 네이티브 자원 접근 위반(access violation)을 유발할 수 있어, 전 단계 완주가 핵심입니다.)
        """
        logger.info("Cleaning up coordinator resources...")
        # 가장 먼저 싱글톤 컨텍스트 구독을 해제하여 좀비 코디네이터가 이후 회의 신호에 반응하지 못하게 합니다.
        # 그다음 DB·CLI 워커 보유 에이전트(Chat/Report)를 합류 대기시키고, 입력 생산자(STT/Flow/화면감지)를 정지합니다.
        cleanup_steps = [
            ("context_signals", self._disconnect_context_signals),
            ("chat_agent", lambda: self.chat_agent and self.chat_agent.cleanup()),
            ("report_agent", lambda: self.report_agent and self.report_agent.cleanup()),
            ("stt_worker", lambda: self.stt_worker and self.stt_worker.stop()),
            ("flow_agent", lambda: self.flow_agent and self.flow_agent.stop()),
            ("screen_detector", lambda: self.screen_detector and self.screen_detector.stop()),
        ]
        for name, step in cleanup_steps:
            try:
                step()
            except Exception as e:
                logger.error(f"Error while cleaning up {name}: {e}")

    def _disconnect_context_signals(self):
        """싱글톤 컨텍스트에 남는 슬롯 누수를 방지하기 위해 코디네이터의 구독을 해제합니다.

        해제하지 않으면 코디네이터가 소멸해도 컨텍스트가 슬롯(바운드 메서드)을 붙들어 살아남고,
        이후 다른 컴포넌트가 회의를 시작/종료할 때 이 '좀비' 코디네이터가 반응해 STT(PyAudio)·Flow
        스레드를 중복 생성합니다. 이는 네이티브 접근 위반(access violation)의 직접 원인이 됩니다.
        """
        for sig, slot in (
            (self.context.signals.meeting_started, self._on_meeting_started),
            (self.context.signals.meeting_ended, self._on_meeting_ended),
            (self.context.signals.transcript_updated, self._on_transcript_updated),
        ):
            try:
                sig.disconnect(slot)
            except (RuntimeError, TypeError):
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
