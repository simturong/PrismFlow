from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QRect, QEvent

class TranslucentOverlay(QWidget):
    """
    투명 오버레이 윈도우의 공통 베이스 클래스.
    프레임리스, 투명 배경, 항상 위 설정을 가지며, 마우스 호버 페이드 효과 및 드래그 이동을 지원합니다.
    마우스 드래그 크기 조절(Resize) 및 우측 상단 창 조작 버튼(최소화, 최대화, 닫기)을 지원합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 윈도우 플래그 설정: 프레임리스, 항상 위, 도구 창 스타일(작업 표시줄 아이콘 제외)
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        # 투명 배경 설정
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 마우스 추적 활성화 (클릭하지 않아도 hover 감지 및 커서 변경을 위함)
        self.setMouseTracking(True)
        
        # 드래그 및 크기 조절 관련 변수
        self._drag_position = QPoint()
        self._is_dragging = False
        self._is_resizing = False
        self._resize_edge = None
        self._press_geometry = self.geometry()
        self._press_global_pos = QPoint()
        self.resize_margin = 8  # 가장자리 8픽셀 이내 감지
        
        # 페이드 애니메이션 설정 (기본 불투명도 0.5, 마우스 호버 시 0.95)
        self.normal_opacity = 0.5
        self.hover_opacity = 0.95
        self.setWindowOpacity(self.normal_opacity)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms
        
        # 창 조작 버튼 초기화
        self._init_control_buttons()

    def _init_control_buttons(self):
        # 컨트롤 버튼들을 포함하는 플로팅 위젯
        self.control_widget = QWidget(self)
        self.control_widget.setObjectName("overlay-controls")
        # 레이아웃 위에 얹히도록 z-order 상위 배치
        self.control_widget.raise_()
        
        layout = QHBoxLayout(self.control_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 최소화 버튼
        self.btn_minimize = QPushButton(self.control_widget)
        self.btn_minimize.setFixedSize(28, 20)
        self.btn_minimize.setToolTip("최소화")
        self.btn_minimize.clicked.connect(self.showMinimized)
        
        # 최대화/복원 버튼
        self.btn_maximize = QPushButton(self.control_widget)
        self.btn_maximize.setFixedSize(28, 20)
        self.btn_maximize.setToolTip("최대화")
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        
        # 닫기 버튼
        self.btn_close = QPushButton(self.control_widget)
        self.btn_close.setFixedSize(28, 20)
        self.btn_close.setToolTip("닫기")
        self.btn_close.clicked.connect(self.close)
        
        # QSS 스타일 초기 적용 (윈도우 표준 플랫 스타일)
        self.btn_minimize.setStyleSheet(self._button_style("#cbd5e1", "transparent", "rgba(255, 255, 255, 0.08)", "—"))
        self.btn_close.setStyleSheet(self._button_style("#cbd5e1", "transparent", "#e81123", "✕"))
        self._update_maximize_button_style()
        
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)
        
        # 위젯 전체 크기 고정 (28 * 3 + 4 * 2 = 92)
        self.control_widget.setFixedSize(92, 20)

    def _button_style(self, color, bg, hover_bg, text):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: none;
                border-radius: 0px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10px;
                font-weight: normal;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: #ffffff;
            }}
        """

    def _update_maximize_button_style(self):
        """최대화/복원 상태에 맞게 버튼 글자와 스타일을 갱신합니다."""
        if self.isMaximized():
            self.btn_maximize.setStyleSheet(self._button_style("#cbd5e1", "transparent", "rgba(255, 255, 255, 0.08)", "❐"))
            self.btn_maximize.setToolTip("이전 크기로 복원")
        else:
            self.btn_maximize.setStyleSheet(self._button_style("#cbd5e1", "transparent", "rgba(255, 255, 255, 0.08)", "□"))
            self.btn_maximize.setToolTip("최대화")

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_maximize_button_style()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self._update_maximize_button_style()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 우측 상단 배치 (우측 14px, 상단 12px 여백)
        self.control_widget.move(self.width() - self.control_widget.width() - 14, 12)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 반투명 어두운 회색 배경 (아름다운 Glassmorphism 기초)
        painter.setBrush(QColor(30, 30, 30, 180))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def enterEvent(self, event):
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(self.hover_opacity)
        self.fade_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(self.normal_opacity)
        self.fade_animation.start()
        super().leaveEvent(event)

    def _get_resize_edge(self, pos):
        margin = self.resize_margin
        w = self.width()
        h = self.height()
        x = pos.x()
        y = pos.y()
        
        left = x < margin
        right = x > w - margin
        top = y < margin
        bottom = y > h - margin
        
        if left and top: return Qt.TopLeftSection
        if right and top: return Qt.TopRightSection
        if left and bottom: return Qt.BottomLeftSection
        if right and bottom: return Qt.BottomRightSection
        if left: return Qt.LeftSection
        if right: return Qt.RightSection
        if top: return Qt.TopSection
        if bottom: return Qt.BottomSection
        return None

    def _get_cursor_for_edge(self, edge):
        if edge in (Qt.TopLeftSection, Qt.BottomRightSection):
            return Qt.SizeFDiagCursor
        if edge in (Qt.TopRightSection, Qt.BottomLeftSection):
            return Qt.SizeBDiagCursor
        if edge in (Qt.LeftSection, Qt.RightSection):
            return Qt.SizeHorCursor
        if edge in (Qt.TopSection, Qt.BottomSection):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
            edge = self._get_resize_edge(pos)
            
            if edge is not None:
                self._is_resizing = True
                self._resize_edge = edge
                self._press_geometry = self.geometry()
                self._press_global_pos = global_pos
            else:
                self._is_resizing = False
                self._resize_edge = None
                self._drag_position = global_pos - self.frameGeometry().topLeft()
                self._is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()
        
        if event.buttons() == Qt.NoButton:
            edge = self._get_resize_edge(pos)
            self.setCursor(self._get_cursor_for_edge(edge))
        elif event.buttons() & Qt.LeftButton:
            if self._is_resizing:
                rect = self.geometry()
                min_w = self.minimumSizeHint().width() if self.minimumWidth() == 0 else self.minimumWidth()
                min_h = self.minimumSizeHint().height() if self.minimumHeight() == 0 else self.minimumHeight()
                min_w = max(min_w, 200)
                min_h = max(min_h, 200)
                
                diff_x = global_pos.x() - self._press_global_pos.x()
                diff_y = global_pos.y() - self._press_global_pos.y()
                
                new_rect = QRect(self._press_geometry)
                
                # Left
                if self._resize_edge in (Qt.LeftSection, Qt.TopLeftSection, Qt.BottomLeftSection):
                    new_w = self._press_geometry.width() - diff_x
                    if new_w >= min_w:
                        new_rect.setLeft(self._press_geometry.left() + diff_x)
                # Right
                if self._resize_edge in (Qt.RightSection, Qt.TopRightSection, Qt.BottomRightSection):
                    new_w = self._press_geometry.width() + diff_x
                    if new_w >= min_w:
                        new_rect.setRight(self._press_geometry.right() + diff_x)
                # Top
                if self._resize_edge in (Qt.TopSection, Qt.TopLeftSection, Qt.TopRightSection):
                    new_h = self._press_geometry.height() - diff_y
                    if new_h >= min_h:
                        new_rect.setTop(self._press_geometry.top() + diff_y)
                # Bottom
                if self._resize_edge in (Qt.BottomSection, Qt.BottomLeftSection, Qt.BottomRightSection):
                    new_h = self._press_geometry.height() + diff_y
                    if new_h >= min_h:
                        new_rect.setBottom(self._press_geometry.bottom() + diff_y)
                        
                self.setGeometry(new_rect)
                event.accept()
            elif self._is_dragging:
                self.move(global_pos - self._drag_position)
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._is_resizing = False
            self._resize_edge = None
            event.accept()
