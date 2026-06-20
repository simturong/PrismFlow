import sys
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QMessageBox, QSystemTrayIcon
from PySide6.QtCore import Qt
from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.ui_common.tray import SystemTrayManager
from prismflow.ui_common.overlay import TranslucentOverlay

class DemoOverlay(TranslucentOverlay):
    """
    Phase 1 데모용 투명 오버레이 윈도우.
    회의 상태 변화에 따라 텍스트를 업데이트합니다.
    """
    def __init__(self):
        super().__init__()
        self.resize(320, 140)
        
        # UI 레이아웃 구성
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)
        
        self.label_title = QLabel("PrismFlow AI Assistant", self)
        self.label_title.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold; font-family: 'Malgun Gothic', sans-serif;")
        self.label_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_title)
        
        self.label_status = QLabel("대기 중 (트레이 메뉴에서 시작)", self)
        self.label_status.setStyleSheet("color: #AAAAAA; font-size: 12px; font-family: 'Malgun Gothic', sans-serif;")
        self.label_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_status)
        
        self.label_info = QLabel("마우스 드래그로 이동 가능 / 호버 시 선명해짐", self)
        self.label_info.setStyleSheet("color: #666666; font-size: 10px; font-family: 'Malgun Gothic', sans-serif;")
        self.label_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_info)
        
        # 싱글톤 컨텍스트 상태 연결
        self.context = MeetingContext()
        self.context.signals.meeting_started.connect(self._on_meeting_started)
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)

    def _on_meeting_started(self, session_id: str):
        self.label_status.setText(f"회의 진행 중 (ID: {session_id})")
        self.label_status.setStyleSheet("color: #FF5555; font-size: 12px; font-weight: bold; font-family: 'Malgun Gothic', sans-serif;")

    def _on_meeting_ended(self, session_id: str):
        self.label_status.setText("회의 종료됨 (대기 중)")
        self.label_status.setStyleSheet("color: #AAAAAA; font-size: 12px; font-family: 'Malgun Gothic', sans-serif;")

def main():
    # 1. 전역 설정 및 컨텍스트 초기화
    config = AppConfig.load_default()
    context = MeetingContext()
    
    # 2. QApplication 초기화
    app = QApplication(sys.argv)
    
    # 시스템 트레이 지원 여부 확인
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "오류", "시스템 트레이가 지원되지 않는 환경입니다.")
        sys.exit(1)
        
    # 마지막 창이 닫혀도 앱이 완전히 종료되지 않고 트레이에 상주하도록 설정
    app.setQuitOnLastWindowClosed(False)
    
    # 3. 시스템 트레이 매니저 기동
    tray = SystemTrayManager()
    tray.show()
    
    # 4. 데모 오버레이 윈도우 생성 및 배치
    overlay = DemoOverlay()
    
    # 기본 위치 지정 (화면 우측 하단 여백 공간)
    screen = app.primaryScreen().geometry()
    x = screen.width() - overlay.width() - 40
    y = screen.height() - overlay.height() - 80
    overlay.move(x, y)
    overlay.show()
    
    # 5. 이벤트 루프 기동
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
