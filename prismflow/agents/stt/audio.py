import queue
import numpy as np
import threading

# Mock 대화 시나리오 정의 (15~20초 주기로 진행되도록 상대 타임라인 구성)
MOCK_DIALOGUES = [
    ("Speaker_00", "안녕하세요. 오늘 PrismFlow 프로젝트 Phase 2 회의를 시작하겠습니다.", 0.0, 4.5),
    ("Speaker_01", "반갑습니다. 저는 오늘 STT 엔진 개발과 SQLite 데이터베이스 연동 부분을 검토하려고 합니다.", 6.0, 11.2),
    ("Speaker_02", "네, 안녕하세요. 저는 Claude CLI 비차단 파이프라인 연동 상황을 말씀드릴게요.", 13.0, 18.5),
    ("Speaker_00", "좋습니다. DB 스키마는 정밀 타임라인 저장을 위해 start_time과 end_time을 개별 저장하기로 확정했었죠?", 20.0, 26.8),
    ("Speaker_01", "맞습니다. transcripts 테이블에 REAL 타입으로 저장해서 정밀하게 동기화하도록 구현이 완료되었습니다.", 28.0, 34.2),
    ("Speaker_02", "그렇군요. 그럼 다음 단계인 STT 에뮬레이터 개발도 순조롭게 진행되겠네요.", 36.0, 41.5),
    ("Speaker_00", "네, 다음으로 각자 담당한 모듈의 에러와 엣지 케이스 테스트를 강화해 주시길 바랍니다.", 44.0, 50.0),
    ("Speaker_01", "알겠습니다. 테스트 코드를 꼼꼼히 작성하겠습니다.", 52.0, 55.5),
    ("Speaker_02", "저도 비차단 IO 타임아웃 처리를 철저하게 테스트해 두겠습니다.", 57.0, 62.0),
    ("Speaker_00", "그럼 오늘 회의는 이것으로 마치고 다음 세션에서 뵙겠습니다. 감사합니다.", 64.0, 69.5)
]

class AudioCapture:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.queue = queue.Queue()
        self.stream = None
        self._is_recording = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """PyAudio 마이크 캡처 스트림을 시작합니다."""
        with self._lock:
            if self._is_recording:
                return True
            try:
                import pyaudio
                self.p = pyaudio.PyAudio()
                self.stream = self.p.open(
                    format=pyaudio.paFloat32,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    stream_callback=self._callback
                )
                self._is_recording = True
                self.stream.start_stream()
                return True
            except (ImportError, Exception) as e:
                # 마이크 하드웨어가 없거나 PyAudio 라이브러리가 없을 때의 우회 처리
                print(f"[AudioCapture] Failed to start real audio capture: {e}")
                self._is_recording = False
                return False

    def _callback(self, in_data, frame_count, time_info, status):
        # PyAudio 버퍼 데이터를 numpy float32 배열로 캐스팅해 큐에 삽입
        import pyaudio
        data = np.frombuffer(in_data, dtype=np.float32)
        self.queue.put(data)
        return (None, pyaudio.paContinue)

    def stop(self):
        """오디오 스트림을 중지합니다."""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            if hasattr(self, 'p'):
                try:
                    self.p.terminate()
                except Exception:
                    pass

    def get_audio_chunk(self):
        """큐에서 캡처된 오디오 청크를 꺼냅니다."""
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None
