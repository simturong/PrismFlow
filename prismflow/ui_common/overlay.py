from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint

class TranslucentOverlay(QWidget):
    """
    투명 오버레이 윈도우의 공통 베이스 클래스.
    프레임리스, 투명 배경, 항상 위 설정을 가지며, 마우스 호버 페이드 효과 및 드래그 이동을 지원합니다.
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
        
        # 드래그 관련 변수
        self._drag_position = QPoint()
        self._is_dragging = False
        
        # 페이드 애니메이션 설정 (기본 불투명도 0.5, 마우스 호버 시 0.95)
        self.normal_opacity = 0.5
        self.hover_opacity = 0.95
        self.setWindowOpacity(self.normal_opacity)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 반투명 어두운 회색 배경 (아름다운 Glassmorphism 기초)
        painter.setBrush(QColor(30, 30, 30, 180))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def enterEvent(self, event):
        # 마우스 진입 시 투명도를 hover_opacity로 서서히 변경
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(self.hover_opacity)
        self.fade_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 마우스 이탈 시 투명도를 normal_opacity로 서서히 변경
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(self.normal_opacity)
        self.fade_animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 드래그 시작 시점의 오프셋 저장 (Qt6 기준 globalPosition() 권장)
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._is_dragging:
            # 드래그 시 마우스 위치에 맞게 윈도우 이동
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            event.accept()
