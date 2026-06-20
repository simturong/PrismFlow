import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QDoubleSpinBox, QLineEdit, QPushButton, QFileDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig

class SettingsDialog(QDialog):
    """PrismFlow 전역 설정을 동적으로 조정 및 저장할 수 있는 다이얼로그 GUI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.context = MeetingContext()
        self.config = AppConfig.load_default()
        
        self.setWindowTitle("PrismFlow - 설정")
        self.resize(400, 360)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
        self.load_settings()
        
    def paintEvent(self, event):
        # QSS를 렌더링하기 위해 투명 다이얼로그 위젯의 페인트를 허용
        pass

    def init_ui(self):
        # 1. 메인 레이아웃 및 프레임 컨테이너
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame(self)
        self.container.setObjectName("settings-container")
        self.container.setStyleSheet("""
            #settings-container {
                background-color: rgba(30, 30, 35, 235);
                border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.2), 
                    stop:1 rgba(255, 255, 255, 0.05));
                border-radius: 12px;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 12px;
                font-family: 'Pretendard', 'Segoe UI', Arial, sans-serif;
                background: transparent;
            }
            QComboBox, QLineEdit, QDoubleSpinBox {
                background-color: rgba(15, 15, 20, 200);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #ffffff;
                padding: 5px;
                font-size: 11px;
            }
            QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus {
                border: 1px solid #7c4dff;
            }
            QPushButton {
                font-size: 11px;
                font-weight: bold;
                font-family: 'Pretendard', 'Segoe UI', sans-serif;
            }
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 2. 타이틀바
        title_label = QLabel("PrismFlow 환경 설정", self.container)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title_label)
        layout.addWidget(QFrame(frameShape=QFrame.HLine, frameShadow=QFrame.Sunken, styleSheet="background-color: rgba(255,255,255,0.08);"))
        
        # 3. Whisper 모델 크기 선택
        model_layout = QHBoxLayout()
        model_label = QLabel("Whisper 모델 크기:", self.container)
        self.model_combo = QComboBox(self.container)
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # 4. 하드웨어 가속 방식
        accel_layout = QHBoxLayout()
        accel_label = QLabel("하드웨어 가속:", self.container)
        self.accel_combo = QComboBox(self.container)
        self.accel_combo.addItems(["CPU", "CUDA", "OpenVINO"])
        accel_layout.addWidget(accel_label)
        accel_layout.addWidget(self.accel_combo)
        layout.addLayout(accel_layout)
        
        # 5. VAD 감지 임계값
        vad_layout = QHBoxLayout()
        vad_label = QLabel("VAD 임계값 (0.1 ~ 1.0):", self.container)
        self.vad_spin = QDoubleSpinBox(self.container)
        self.vad_spin.setRange(0.1, 1.0)
        self.vad_spin.setSingleStep(0.05)
        self.vad_spin.setValue(0.5)
        vad_layout.addWidget(vad_label)
        vad_layout.addWidget(self.vad_spin)
        layout.addLayout(vad_layout)
        
        # 6. Claude CLI 경로
        path_layout = QVBoxLayout()
        path_label = QLabel("Claude CLI 실행 명령어 또는 파일 경로:", self.container)
        
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit(self.container)
        self.path_btn = QPushButton("찾기", self.container)
        self.path_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.path_btn.clicked.connect(self.browse_cli_path)
        
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(self.path_btn)
        
        path_layout.addWidget(path_label)
        path_layout.addLayout(path_input_layout)
        layout.addLayout(path_layout)
        
        layout.addSpacing(10)
        
        # 7. 버튼 (저장 / 취소)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("저장", self.container)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c4dff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #9066ff;
            }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("취소", self.container)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a1a1aa;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
    def load_settings(self):
        """SQLite settings 테이블에서 설정을 로드하여 UI 컴포넌트에 반영합니다."""
        db = self.context.db_manager
        if not db:
            # DB가 기동 전이면 Config 기본값 적용
            self.model_combo.setCurrentText("base")
            self.accel_combo.setCurrentText("CPU")
            self.vad_spin.setValue(self.config.vad_threshold)
            self.path_input.setText(self.config.claude_cli_cmd)
            return
            
        model = db.get_setting("whisper_model_size", "base")
        accel = db.get_setting("hardware_acceleration", "CPU")
        vad_val = float(db.get_setting("vad_threshold", str(self.config.vad_threshold)))
        claude_path = db.get_setting("claude_cli_cmd", self.config.claude_cli_cmd)
        
        self.model_combo.setCurrentText(model)
        self.accel_combo.setCurrentText(accel)
        self.vad_spin.setValue(vad_val)
        self.path_input.setText(claude_path)
        
    def browse_cli_path(self):
        """파일 브라우저를 통해 Claude CLI 파일 경로를 선택합니다."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Claude CLI 실행 파일 선택", 
            os.path.expanduser("~"), 
            "All Files (*);;Executables (*.exe *.bat *.cmd)"
        )
        if file_path:
            # Windows 백슬래시 통일
            self.path_input.setText(os.path.normpath(file_path))
            
    def save_settings(self):
        """UI에서 지정한 설정을 SQLite DB에 저장하고 Config 오브젝트를 갱신합니다."""
        whisper_model = self.model_combo.currentText()
        accel = self.accel_combo.currentText()
        vad_val = str(self.vad_spin.value())
        claude_path = self.path_input.text().strip()
        
        if not claude_path:
            QMessageBox.warning(self, "경고", "Claude CLI 명령어를 입력하십시오.")
            return
            
        db = self.context.db_manager
        if db:
            db.set_setting("whisper_model_size", whisper_model)
            db.set_setting("hardware_acceleration", accel)
            db.set_setting("vad_threshold", vad_val)
            db.set_setting("claude_cli_cmd", claude_path)
            
        # 전역 AppConfig 실시간 동기화
        self.config.claude_cli_cmd = claude_path
        self.config.vad_threshold = float(vad_val)
        
        QMessageBox.information(self, "설정", "설정이 성공적으로 저장되었습니다.")
        self.accept()
