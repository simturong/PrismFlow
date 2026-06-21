from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QRect, QEvent
from prismflow.ui_common.indicators import RecordingIndicator

class TranslucentOverlay(QWidget):
    """
    투명 오버레이 윈도우의 공통 베이스 클래스.
    프레임리스·투명 배경이며, 마우스 호버 페이드 효과 및 드래그 이동을 지원합니다.
    마우스 드래그 크기 조절(Resize) 및 우측 상단 창 조작 영역(녹음 표시·투명도 슬라이더·최소화·최대화·닫기)을 지원합니다.

    (정책) '항상 위(WindowStaysOnTopHint)'는 적용하지 않습니다. 다른 창이 포커스를 가지면
    오버레이는 자연스럽게 그 뒤로 가야 하므로, 일반 도구 창처럼 z-order를 OS에 맡깁니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # 윈도우 플래그 설정: 프레임리스 + 도구 창 스타일(작업 표시줄 아이콘 제외).
        # '항상 위'는 의도적으로 제외하여, 다른 앱을 선택하면 오버레이가 뒤로 물러나도록 한다.
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
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

        # 페이드 애니메이션 설정 (기본 불투명도 1.0(가장 불투명), 마우스 호버 시 1.0)
        self.normal_opacity = 1.0
        self.hover_opacity = 1.0
        self.setWindowOpacity(self.normal_opacity)

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms

        # 사용자가 슬라이더로 직접 투명도를 조절하는 동안에는 hover 페이드를 일시 양보한다.
        self._user_opacity_active = False

        # 싱글톤 컨텍스트 획득 및 신호 바인딩
        from prismflow.core.context import MeetingContext
        self.context = MeetingContext()

        # 우측 상단 창 조작 영역 초기화 (녹음 표시 + 투명도 슬라이더 + 최소/최대/닫기)
        self._init_control_buttons()

        self.context.signals.meeting_started.connect(self._on_meeting_started)
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)
        self.context.signals.meeting_paused.connect(self._on_meeting_paused)

        if self.context.is_meeting_active:
            self.btn_pause.setVisible(True)
            self.btn_stop.setVisible(True)
            if self.context.is_meeting_paused:
                self.btn_pause.setText("\uE768") # Play
                self.btn_pause.setToolTip("회의 재개")

    def _init_control_buttons(self):
        # 컨트롤(녹음 표시·슬라이더·버튼)을 한데 묶는 우측 상단 플로팅 위젯
        self.control_widget = QWidget(self)
        self.control_widget.setObjectName("overlay-controls")
        # 레이아웃 위에 얹히도록 z-order 상위 배치
        self.control_widget.raise_()

        layout = QHBoxLayout(self.control_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 녹음(회의 진행) 인디케이터 — 최소화 버튼 바로 왼쪽. 회의 시작 시 set_recording(True)로 점멸.
        self.recording_indicator = RecordingIndicator(self.control_widget)

        # 투명도 조절 슬라이더 — 녹음 표시 옆 작은 가로 슬라이더(20%~100%).
        self.opacity_slider = QSlider(Qt.Horizontal, self.control_widget)
        self.opacity_slider.setMinimum(20)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(int(self.normal_opacity * 100))
        self.opacity_slider.setFixedWidth(64)
        self.opacity_slider.setToolTip("창 투명도 조절")
        self.opacity_slider.setStyleSheet(self._slider_style())
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.opacity_slider.sliderPressed.connect(lambda: setattr(self, "_user_opacity_active", True))
        self.opacity_slider.sliderReleased.connect(self._on_opacity_slider_released)

        # 일시중지 버튼 — \uE769 (Pause) / \uE768 (Play)
        self.btn_pause = QPushButton(self.control_widget)
        self.btn_pause.setFixedSize(28, 20)
        self.btn_pause.setText("\uE769")
        self.btn_pause.setToolTip("회의 일시중지")
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        self.btn_pause.setVisible(False)

        # 정지 버튼 — \uE71A (Stop)
        self.btn_stop = QPushButton(self.control_widget)
        self.btn_stop.setFixedSize(28, 20)
        self.btn_stop.setText("\uE71A")
        self.btn_stop.setToolTip("회의 정지(종료)")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        self.btn_stop.setVisible(False)

        # 최소화 버튼 — Segoe MDL2 Assets  (ChromeMinimize)
        self.btn_minimize = QPushButton(self.control_widget)
        self.btn_minimize.setFixedSize(28, 20)
        self.btn_minimize.setText("")
        self.btn_minimize.setToolTip("최소화")
        self.btn_minimize.clicked.connect(self.showMinimized)

        # 최대화/복원 버튼 —  (ChromeMaximize) /  (ChromeRestore)
        self.btn_maximize = QPushButton(self.control_widget)
        self.btn_maximize.setFixedSize(28, 20)
        self.btn_maximize.setToolTip("최대화")
        self.btn_maximize.clicked.connect(self.toggle_maximize)

        # 닫기 버튼 — Segoe MDL2 Assets  (ChromeClose)
        self.btn_close = QPushButton(self.control_widget)
        self.btn_close.setFixedSize(28, 20)
        self.btn_close.setText("")
        self.btn_close.setToolTip("닫기")
        self.btn_close.clicked.connect(self.close)

        # QSS 스타일 초기 적용 (윈도우 표준 플랫 스타일, 고대비 색상)
        self.btn_minimize.setStyleSheet(self._button_style("#e2e8f0", "transparent", "rgba(255, 255, 255, 0.12)"))
        self.btn_pause.setStyleSheet(self._button_style("#e2e8f0", "transparent", "rgba(255, 255, 255, 0.12)"))
        self.btn_stop.setStyleSheet(self._button_style("#ff6b6b", "transparent", "#e81123"))
        self.btn_close.setStyleSheet(self._button_style("#ff6b6b", "transparent", "#e81123"))
        self._update_maximize_button_style()

        layout.addWidget(self.recording_indicator)
        layout.addWidget(self.opacity_slider)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

        # 녹음 인디케이터는 회의 중에만 보여 폭이 가변 → 고정 크기 대신 내용에 맞춘다.
        self.control_widget.adjustSize()

    def _slider_style(self) -> str:
        return """
            QSlider::groove:horizontal {
                height: 4px; border-radius: 2px;
                background: rgba(255, 255, 255, 0.18);
            }
            QSlider::sub-page:horizontal {
                height: 4px; border-radius: 2px;
                background: rgba(124, 77, 255, 0.85);
            }
            QSlider::handle:horizontal {
                width: 10px; height: 10px; margin: -4px 0; border-radius: 5px;
                background: #e2e8f0;
            }
            QSlider::handle:horizontal:hover { background: #ffffff; }
        """

    def _on_opacity_slider_changed(self, value: int):
        """슬라이더 값(20~100%)을 창의 기본(rest) 투명도로 적용하고 즉시 반영한다."""
        self.normal_opacity = max(0.2, min(1.0, value / 100.0))
        # 드래그 중에는 hover 페이드를 멈추고 선택 값을 라이브로 보여준다.
        self.fade_animation.stop()
        self.setWindowOpacity(self.normal_opacity)

    def _on_opacity_slider_released(self):
        self._user_opacity_active = False
        # 슬라이더에서 손을 뗀 시점에 커서가 창 위에 있으면 hover 투명도로 부드럽게 복귀한다.
        if self.underMouse():
            self._animate_opacity(self._effective_hover_opacity())

    def _effective_hover_opacity(self) -> float:
        """hover 시 목표 투명도. 사용자가 설정한 rest 값보다 항상 또렷하도록 보장한다."""
        return max(self.normal_opacity, self.hover_opacity)

    def _animate_opacity(self, target: float):
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(target)
        self.fade_animation.start()

    def _button_style(self, color, bg, hover_bg):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: none;
                border-radius: 0px;
                font-family: 'Segoe MDL2 Assets', 'Segoe UI Symbol', 'Segoe UI', Arial, sans-serif;
                font-size: 9px;
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
            self.btn_maximize.setText("")  # ChromeRestore
            self.btn_maximize.setStyleSheet(self._button_style("#e2e8f0", "transparent", "rgba(255, 255, 255, 0.12)"))
            self.btn_maximize.setToolTip("이전 크기로 복원")
        else:
            self.btn_maximize.setText("")  # ChromeMaximize
            self.btn_maximize.setStyleSheet(self._button_style("#e2e8f0", "transparent", "rgba(255, 255, 255, 0.12)"))
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

    def set_recording(self, recording: bool):
        """우측 상단 녹음 인디케이터의 점멸을 켜고 끈다 (회의 시작/종료 시 호출).

        녹음 표시가 보이고 숨겨질 때 컨트롤 영역의 폭이 달라지므로, 표시 변경 후
        컨트롤 묶음 크기를 다시 맞추고 우측 상단으로 재배치한다.
        """
        self.recording_indicator.set_recording(recording)
        self._reposition_controls()
        if recording:
            self.control_widget.raise_()

    def _reposition_controls(self):
        """컨트롤 묶음(녹음·슬라이더·버튼)을 내용 크기에 맞춰 우측 상단(우측 14px, 상단 12px)에 재배치한다."""
        self.control_widget.adjustSize()
        self.control_widget.move(self.width() - self.control_widget.width() - 14, 12)
        self.control_widget.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_controls()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 배경 채움은 '불투명'으로 둔다. 투명도는 전적으로 windowOpacity(투명도 슬라이더)가 제어하므로,
        # 슬라이더를 오른쪽 끝(100%)으로 올리면 창이 전혀 비치지 않고 완전히 불투명해진다.
        # (배경에 alpha를 또 주면 슬라이더가 100%여도 항상 일부 비쳐 보이는 문제가 생긴다.)
        painter.setBrush(QColor(30, 30, 30, 255))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

        # 1px 두께의 은은한 반투명 화이트 테두리 추가
        pen = QPen(QColor(255, 255, 255, 30), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 11, 11)

    def enterEvent(self, event):
        # 사용자가 슬라이더로 투명도를 조절 중이면 hover 페이드가 값을 덮어쓰지 않도록 양보한다.
        if not self._user_opacity_active:
            self._animate_opacity(self._effective_hover_opacity())
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._user_opacity_active:
            self._animate_opacity(self.normal_opacity)
        super().leaveEvent(event)

    def closeEvent(self, event):
        try:
            self.context.signals.meeting_started.disconnect(self._on_meeting_started)
            self.context.signals.meeting_ended.disconnect(self._on_meeting_ended)
            self.context.signals.meeting_paused.disconnect(self._on_meeting_paused)
        except Exception:
            pass
        super().closeEvent(event)

    def _on_pause_clicked(self):
        self.context.toggle_pause()

    def _on_stop_clicked(self):
        self.context.end_meeting()

    def _on_meeting_started(self, session_id: str):
        self.btn_pause.setVisible(True)
        self.btn_stop.setVisible(True)
        self.btn_pause.setText("\uE769") # Pause
        self.btn_pause.setToolTip("회의 일시중지")
        self._reposition_controls()

    def _on_meeting_ended(self, session_id: str):
        self.btn_pause.setVisible(False)
        self.btn_stop.setVisible(False)
        self._reposition_controls()

    def _on_meeting_paused(self, paused: bool):
        if paused:
            self.btn_pause.setText("\uE768") # Play
            self.btn_pause.setToolTip("회의 재개")
        else:
            self.btn_pause.setText("\uE769") # Pause
            self.btn_pause.setToolTip("회의 일시중지")

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
