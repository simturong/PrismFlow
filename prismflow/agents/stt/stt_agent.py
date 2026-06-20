import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig
from .audio import MOCK_DIALOGUES, AudioCapture

class RealTimeEngineWorker(QThread):
    status_changed = Signal(str) # "running", "idle", "error"
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.context = MeetingContext()
        self.config = AppConfig.load_default()
        self._running = False
        
        # 실제 추론 모델 홀더 (OpenVINO 관련)
        self.whisper_model = None
        self.diarization_model = None
        
        # Mock 전용 주기 설정 (테스트 시 짧게 조정 가능하도록 config 확인 및 기본 15.0초 지정)
        self.mock_interval = getattr(self.config, "stt_mock_interval", 15.0)

    def stop(self):
        """스레드를 안전하게 종료합니다."""
        self._running = False
        self.wait()

    def run(self):
        self._running = True
        self.status_changed.emit("running")
        
        if self.config.stt_mock_mode:
            self._run_mock_loop()
        else:
            self._run_real_loop()

    def _run_mock_loop(self):
        dialogue_idx = 0
        
        while self._running:
            if self.context.is_meeting_active:
                if dialogue_idx < len(MOCK_DIALOGUES):
                    speaker, text, start_time, end_time = MOCK_DIALOGUES[dialogue_idx]
                    
                    self.context.add_transcript(
                        speaker=speaker,
                        text=text,
                        start_time=start_time,
                        end_time=end_time
                    )
                    dialogue_idx += 1
                else:
                    # 루프 회독이 끝났으나 회의가 계속 진행 중일 때 대기
                    pass
                
                # mock_interval 초 동안 대기하되 스레드 중단 요청에 빠르게 반응하도록 0.1초씩 끊어서 확인
                sleep_steps = int(self.mock_interval / 0.1)
                for _ in range(sleep_steps):
                    if not self._running or not self.context.is_meeting_active:
                        break
                    time.sleep(0.1)
            else:
                # 회의가 종료되었거나 활성화 전이면 대기
                dialogue_idx = 0
                time.sleep(0.1)
                
        self.status_changed.emit("idle")

    def _run_real_loop(self):
        # 1. OpenVINO 런타임 및 가중치 확인 로드
        try:
            self._load_openvino_models()
        except Exception as e:
            self.error_occurred.emit(f"OpenVINO 모델 로드 실패: {str(e)}")
            self.status_changed.emit("error")
            self._running = False
            return

        # 2. 마이크 장치 준비
        audio_cap = AudioCapture(
            sample_rate=self.config.audio_sample_rate,
            channels=1
        )
        if not audio_cap.start():
            self.error_occurred.emit("PyAudio 마이크 입력을 초기화할 수 없습니다.")
            self.status_changed.emit("error")
            self._running = False
            return

        try:
            # diart 규격: 5.0초 윈도우, 0.5초 shift
            sample_rate = self.config.audio_sample_rate
            window_size = int(5.0 * sample_rate)
            step_size = int(0.5 * sample_rate)
            buffer = np.zeros(0, dtype=np.float32)
            
            # 상대 시작 시점 관리용
            relative_start_time = 0.0

            while self._running:
                # 미팅이 활성화된 상태에서만 수집 및 추론 수행
                if self.context.is_meeting_active:
                    chunk = audio_cap.get_audio_chunk()
                    if chunk is not None:
                        buffer = np.append(buffer, chunk)
                    
                    # 5초 오디오 데이터가 쌓이면 추론 실행
                    while len(buffer) >= window_size and self._running:
                        window_data = buffer[:window_size]
                        
                        # OpenVINO 추론 연동 (Whisper & pyannote-openvino)
                        speaker, text = self._process_inference(window_data)
                        
                        # 화자 분리 및 텍스트 캡처 완료 시 Context 적재
                        if text:
                            # 0.5초 간격으로 시프트하므로 상대 시각 기록
                            # 여기서는 5초 윈도우 크기에 맞춰 발화 시각 할당
                            self.context.add_transcript(
                                speaker=speaker,
                                text=text,
                                start_time=relative_start_time,
                                end_time=relative_start_time + 5.0
                            )
                        
                        # 0.5초 시프트
                        buffer = buffer[step_size:]
                        relative_start_time += 0.5
                else:
                    # 미팅 비활성화 상태에서는 버퍼와 타임라인 리셋
                    buffer = np.zeros(0, dtype=np.float32)
                    relative_start_time = 0.0
                    time.sleep(0.1)
                
                time.sleep(0.01)
        finally:
            audio_cap.stop()
            self.status_changed.emit("idle")

    def _load_openvino_models(self):
        """OpenVINO GenAI 및 pyannote-openvino ONNX 런타임 가중치 로드 로직"""
        try:
            import openvino.runtime as ov
        except ImportError:
            raise ImportError("openvino 라이브러리가 설치되어 있지 않습니다.")

        # Whisper 및 Pyannote 파라미터 강제 규격 제어 명시
        # condition_on_previous_text = False
        # language = "<|ko|>"
        # word_timestamps = True
        # duration = 5.0, step = 0.5, rho_update = 0.1
        
        # 실제 모델 경로 로드 시도
        # 예: model = ov.Core().read_model(...)
        # 가중치 파일이 없는 경우 FileNotFoundError 등을 발생시켜 예외 전파
        pass

    def _process_inference(self, audio_window) -> tuple:
        """OpenVINO Whisper 및 pyannote-openvino를 사용한 추론 처리 루틴"""
        # 실제 추론 로직 적용
        # 여기서는 placeholder이며, 모델 로드 완료 후 실행 가능
        return "Speaker_00", ""
