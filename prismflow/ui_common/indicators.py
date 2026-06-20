"""오버레이 공용 상태 인디케이터 위젯 (Phase 10)."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

_DOT_ON = "color: #ff3b30; font-size: 13px; background: transparent;"
_DOT_OFF = "color: rgba(255, 59, 48, 35); font-size: 13px; background: transparent;"


class RecordingIndicator(QWidget):
    """'● 녹음 중' 빨간 점 점멸 인디케이터.

    set_recording(True) 시 표시되며 600ms 주기로 점이 깜빡인다. set_recording(False)면 숨겨진다.
    오버레이 좌상단에 얹어 현재 녹음(회의 진행) 중임을 시각적으로 알린다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 드래그/리사이즈 방해 금지

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.dot = QLabel("●", self)  # ●
        self.dot.setStyleSheet(_DOT_ON)
        self.text = QLabel("녹음 중", self)
        self.text.setStyleSheet(
            "color: #ff6b6b; font-size: 11px; font-weight: bold; background: transparent;"
            " font-family: 'Pretendard', 'Malgun Gothic', sans-serif;"
        )
        layout.addWidget(self.dot)
        layout.addWidget(self.text)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._dot_on = True
        self._recording = False
        self.hide()

    def _toggle_blink(self):
        self._dot_on = not self._dot_on
        self.dot.setStyleSheet(_DOT_ON if self._dot_on else _DOT_OFF)

    def set_recording(self, recording: bool):
        """녹음 상태를 설정한다. True면 점멸 시작·표시, False면 정지·숨김."""
        self._recording = bool(recording)
        if self._recording:
            self._dot_on = True
            self.dot.setStyleSheet(_DOT_ON)
            self.adjustSize()
            self.show()
            self.raise_()
            self._blink_timer.start(600)
        else:
            self._blink_timer.stop()
            self.hide()

    def is_recording(self) -> bool:
        return self._recording
