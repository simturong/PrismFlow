import sys
from datetime import datetime
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QStyle, QApplication, QMessageBox
from PySide6.QtGui import QAction, QIcon
from prismflow.core.context import MeetingContext

class SystemTrayManager(QSystemTrayIcon):
    """
    시스템 트레이 아이콘 및 우클릭 컨텍스트 메뉴를 관리합니다.
    MeetingContext 싱글톤과 연동하여 회의 상태 전이에 따른 메뉴 활성화 상태를 조절합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 싱글톤 컨텍스트 획득
        self.context = MeetingContext()
        
        # 시스템 기본 아이콘으로 초기 아이콘 설정 (SP_ComputerIcon)
        self.default_icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
        self.active_icon = QApplication.style().standardIcon(QStyle.SP_MediaPlay)
        self.setIcon(self.default_icon)
        self.setToolTip("PrismFlow AI Assistant")
        
        self.init_menu()
        self.activated.connect(self._on_tray_activated)
        
        # UI 핸들 초기화
        self.flow_ui = None
        self.chat_ui = None
        self.cli_log_window = None
        
        # 컨텍스트 신호 연결
        self.context.signals.meeting_started.connect(self._on_meeting_started)
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)

    def init_menu(self):
        self.menu = QMenu()
        
        self.start_action = QAction("회의 시작", self)
        self.start_action.triggered.connect(self.start_meeting)
        self.menu.addAction(self.start_action)
        
        self.end_action = QAction("회의 종료", self)
        self.end_action.triggered.connect(self.end_meeting)
        self.end_action.setEnabled(False)  # 초기에는 비활성화
        self.menu.addAction(self.end_action)
        
        self.menu.addSeparator()
        
        # 창 표시 복원 액션 추가
        self.show_flow_action = QAction("회의 맵 표시 (Flow Map)", self)
        self.show_flow_action.triggered.connect(self.restore_flow_ui)
        self.menu.addAction(self.show_flow_action)
        
        self.show_chat_action = QAction("AI 채팅 표시 (AI Chat)", self)
        self.show_chat_action.triggered.connect(self.restore_chat_ui)
        self.menu.addAction(self.show_chat_action)

        # 개발 디버깅용: CLI 주고받기 로그 창
        self.show_cli_log_action = QAction("CLI 디버그 로그 (개발용)", self)
        self.show_cli_log_action.triggered.connect(self.restore_cli_log)
        self.menu.addAction(self.show_cli_log_action)

        self.menu.addSeparator()
        
        self.settings_action = QAction("설정", self)
        self.settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(self.settings_action)
        
        self.exit_action = QAction("종료", self)
        self.exit_action.triggered.connect(self.exit_app)
        self.menu.addAction(self.exit_action)
        
        self.setContextMenu(self.menu)

    def set_ui_handlers(self, flow_ui, chat_ui, cli_log_window=None):
        """오버레이 UI들의 핸들을 주입받아 복원 제어에 사용합니다."""
        self.flow_ui = flow_ui
        self.chat_ui = chat_ui
        if cli_log_window is not None:
            self.cli_log_window = cli_log_window

    def restore_flow_ui(self):
        if self.flow_ui:
            self.flow_ui.showNormal()
            self.flow_ui.raise_()
            self.flow_ui.activateWindow()

    def restore_chat_ui(self):
        if self.chat_ui:
            self.chat_ui.showNormal()
            self.chat_ui.raise_()
            self.chat_ui.activateWindow()

    def restore_cli_log(self):
        if self.cli_log_window:
            self.cli_log_window.show()
            self.cli_log_window.showNormal()
            self.cli_log_window.raise_()
            self.cli_log_window.activateWindow()

    def restore_all_windows(self):
        self.restore_flow_ui()
        self.restore_chat_ui()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_all_windows()

    def start_meeting(self):
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        success = self.context.start_meeting(session_id)
        if success:
            self.showMessage("PrismFlow", f"회의가 시작되었습니다. (ID: {session_id})", QSystemTrayIcon.Information, 2000)
            
    def end_meeting(self):
        success = self.context.end_meeting()
        if success:
            self.showMessage("PrismFlow", "회의가 종료되었습니다.", QSystemTrayIcon.Information, 2000)

    def show_settings(self):
        from prismflow.ui_common.settings_ui import SettingsDialog
        dialog = SettingsDialog()
        dialog.exec()

    def exit_app(self):
        if self.context.is_meeting_active:
            self.context.end_meeting()
        # 트레이 아이콘 명시적 숨김 (종료 시 트레이 아이콘 잔상 방지)
        self.hide()
        QApplication.quit()

    def _on_meeting_started(self, session_id: str):
        self.start_action.setEnabled(False)
        self.end_action.setEnabled(True)
        self.setIcon(self.active_icon)

    def _on_meeting_ended(self, session_id: str):
        self.start_action.setEnabled(True)
        self.end_action.setEnabled(False)
        self.setIcon(self.default_icon)
