import os
import pytest
import time
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.stt.audio import MOCK_DIALOGUES

@pytest.fixture
def mock_stt_config(temp_config):
    # 테스트 속도를 위해 mock interval을 0.05초로 지정
    temp_config.stt_mock_mode = True
    temp_config.stt_mock_interval = 0.05
    return temp_config

def test_stt_mock_mode_pipeline(q_app, mock_stt_config, monkeypatch):
    """STT 스레드가 Mock 모드일 때 대화 데이터가 정기적으로 context에 적재되는지 검증"""
    # AppConfig가 모킹된 설정을 가져가도록 패치
    monkeypatch.setattr(AppConfig, "load_default", lambda: mock_stt_config)
    
    context = MeetingContext()
    context.reset() # 초기화
    
    # 스레드 생성
    worker = RealTimeEngineWorker()
    
    # 스레드 기동 상태 모니터링 시그널 수집
    status_history = []
    worker.status_changed.connect(status_history.append)
    
    # 1. 회의 활성화 전 기동
    worker.start()
    
    # 스레드가 기동될 때까지 대기 (최대 0.5초)
    for _ in range(50):
        if worker.isRunning():
            break
        time.sleep(0.01)
        
    assert worker.isRunning() is True
    # 회의가 아직 시작되지 않았으므로 transcripts는 비어있어야 함
    assert len(context.transcripts) == 0
    
    # 2. 회의 시작
    session_id = "test_stt_sess_1"
    context.start_meeting(session_id, title="STT 테스트 미팅")
    
    # QThread가 돌아가면서 발화를 쌓도록 대기 및 이벤트 처리
    # mock_interval이 0.05초이므로 0.5초 대기하면 최소 3개 이상 쌓여야 함
    # 타이밍 마진을 고려해 루프 대기를 100회(최대 1.0초)로 넉넉하게 지정
    for _ in range(100):
        q_app.processEvents()
        time.sleep(0.01)
        if len(context.transcripts) >= 3:
            break
            
    assert len(context.transcripts) >= 3
    # 데이터가 MOCK_DIALOGUES와 부합하는지 검증
    for i, item in enumerate(context.transcripts[:3]):
        assert item["speaker"] == MOCK_DIALOGUES[i][0]
        assert item["text"] == MOCK_DIALOGUES[i][1]
        assert item["start_time"] == MOCK_DIALOGUES[i][2]
        assert item["end_time"] == MOCK_DIALOGUES[i][3]
        
    # 3. 회의 종료 후 스레드가 추가 데이터를 주입하지 않고 대기 상태로 가는지 검증
    context.end_meeting()
    current_count = len(context.transcripts)
    time.sleep(0.1)
    q_app.processEvents()
    assert len(context.transcripts) == current_count
    
    # 4. 스레드 정지 및 마무리
    worker.stop()
    q_app.processEvents()  # 시그널 배달 보장
    assert worker.isRunning() is False
    assert "running" in status_history
    assert "idle" in status_history

def test_stt_real_mode_error_fallback(q_app, mock_stt_config, monkeypatch):
    """실제 모드 구동 시 모델 로드 실패가 error 시그널로 전파되고 스레드가 안전 종료되는지 검증.

    무거운 실엔진(OpenVINO) 콜드 임포트나 마이크 하드웨어 유무에 따라 결과가 흔들리지 않도록,
    AudioCapture는 성공으로 가장하고 모델 로드만 결정적으로 실패하도록 주입하여
    "모델 로드 실패 → error 시그널 → 스레드 안전 종료" 경로만 결정적으로 검증한다.
    """
    import prismflow.agents.stt.stt_agent as stt_mod

    mock_stt_config.stt_mock_mode = False
    monkeypatch.setattr(AppConfig, "load_default", lambda: mock_stt_config)

    # 1. 오디오 캡처는 성공한 것으로 가장 (PyAudio/마이크 의존성 제거 → 결정성 확보)
    class _FakeCap:
        def __init__(self, *args, **kwargs):
            pass
        def start(self):
            return True
        def stop(self):
            pass
        def get_audio_chunk(self):
            return None
    monkeypatch.setattr(stt_mod, "AudioCapture", _FakeCap)

    worker = RealTimeEngineWorker()

    # 2. 무거운 실엔진 로드를 제거하고 결정적으로 모델 로드 실패를 주입
    def _raise_load():
        raise RuntimeError("강제 모델 로드 실패 (테스트)")
    monkeypatch.setattr(worker, "_load_openvino_models", _raise_load)

    error_msgs = []
    worker.error_occurred.connect(error_msgs.append)

    worker.start()

    # 모델 로드 실패 후 error_occurred 방출 및 스레드 안전 종료를 대기 (최대 2.0초면 충분)
    for _ in range(200):
        q_app.processEvents()
        time.sleep(0.01)
        if not worker.isRunning():
            break

    assert worker.isRunning() is False
    q_app.processEvents()  # 시그널 배달 보장
    assert len(error_msgs) > 0
    assert any("실패" in msg or "없습니다" in msg or "오류" in msg for msg in error_msgs)


def test_detect_device_respects_override(temp_config, monkeypatch):
    """stt_device 강제 설정은 우선 적용되고, AUTO는 문자열 디바이스를 반환한다."""
    monkeypatch.setattr(AppConfig, "load_default", lambda: temp_config)
    worker = RealTimeEngineWorker()

    temp_config.stt_device = "CPU"
    assert worker._detect_device() == "CPU"

    temp_config.stt_device = "AUTO"
    dev = worker._detect_device()
    assert isinstance(dev, str) and dev in ("GPU", "NPU", "CPU")


def test_vad_segmentation_emits_single_utterance(q_app, temp_config, monkeypatch):
    """에너지 VAD 루프: 발화(speech)+무음(endpoint)을 1개의 발화로 분절해 전사 적재하는지 검증.

    실제 모델 없이 _process_inference를 모킹하여 VAD 분절/타임라인/적재 로직만 단위 검증한다.
    """
    import numpy as np
    monkeypatch.setattr(AppConfig, "load_default", lambda: temp_config)

    context = MeetingContext()
    context.reset()
    context.start_meeting("vad_sess", title="VAD 테스트")

    worker = RealTimeEngineWorker()
    # 전사 추론은 모킹 (화자/텍스트 고정)
    worker._process_inference = lambda audio: ("Speaker_01", "테스트 발화입니다")

    sr = temp_config.audio_sample_rate
    frame = sr // 10  # 0.1초 프레임
    loud = (np.ones(frame, dtype=np.float32) * 0.1)   # rms=0.1 > gate(0.005) → speech
    quiet = np.zeros(frame, dtype=np.float32)          # rms=0 → silence
    # 1.0초 발화 + 0.8초 무음(endpoint 0.6s 초과) → finalize 1회
    script = [loud] * 10 + [quiet] * 8

    class FakeCap:
        def __init__(self, chunks):
            self._chunks = list(chunks)
        def get_audio_chunk(self):
            if self._chunks:
                return self._chunks.pop(0)
            worker._running = False  # 스크립트 소진 시 루프 종료
            return None
        def stop(self):
            pass

    worker._running = True
    worker._run_vad_segmented_loop(FakeCap(script))

    assert len(context.transcripts) == 1
    tr = context.transcripts[0]
    assert tr["speaker"] == "Speaker_01"
    assert tr["text"] == "테스트 발화입니다"
    assert tr["start_time"] == 0.0
    assert 1.0 <= tr["end_time"] <= 2.0  # 발화1.0s + 무음 endpoint(~0.6s) 구간

    context.end_meeting()
    context.reset()


@pytest.mark.skipif(
    not os.environ.get("STT_LIVE"),
    reason="실엔진(OpenVINO Whisper) 옵트인 테스트 — STT_LIVE=1 환경에서만 실행",
)
def test_live_whisper_load_and_infer(temp_config, monkeypatch):
    """[옵트인] 실제 OpenVINO Whisper 로드 + 추론 경로가 (speaker, text)를 반환하는지 검증."""
    import numpy as np
    monkeypatch.setattr(AppConfig, "load_default", lambda: temp_config)
    worker = RealTimeEngineWorker()
    worker._load_openvino_models()
    assert worker.whisper_model is not None
    spk, txt = worker._process_inference(np.zeros(int(3.0 * temp_config.audio_sample_rate), dtype=np.float32))
    assert spk == "Speaker_00"
    assert isinstance(txt, str)


def test_global_speaker_matching(temp_config, monkeypatch):
    """임베딩 코사인 유사도 전역 매칭 알고리즘 검증"""
    import numpy as np
    monkeypatch.setattr(AppConfig, "load_default", lambda: temp_config)
    worker = RealTimeEngineWorker()
    
    # 임베딩 추출기 모크: 입력 오디오의 첫 번째 원소를 보고 시뮬레이션된 임베딩 반환
    def mock_extractor(data):
        waveform = data["waveform"]
        first_val = float(waveform[0, 0])
        if abs(first_val - 1.0) < 0.01:
            # 화자 A 임베딩
            return np.array([[1.0, 0.0]], dtype=np.float32)
        elif abs(first_val - 1.1) < 0.01:
            # 화자 A와 유사한 임베딩 (코사인 유사도 0.99)
            return np.array([[0.995, 0.099]], dtype=np.float32)
        else:
            # 화자 B 임베딩 (화자 A와 수직, 코사인 유사도 0.0)
            return np.array([[0.0, 1.0]], dtype=np.float32)
            
    worker.embedding_extractor = mock_extractor
    
    audio_a1 = np.ones(100, dtype=np.float32) * 1.0
    audio_a2 = np.ones(100, dtype=np.float32) * 1.1
    audio_b = np.ones(100, dtype=np.float32) * 2.0
    
    # 1. 화자 A 매칭 (첫 화자이므로 신규 추가)
    spk1 = worker._match_global_speaker(audio_a1, "Speaker_00")
    assert spk1 == "Speaker_01"
    assert "Speaker_01" in worker.speaker_embeddings
    
    # 2. 유사 화자 매칭 (유사도가 0.55 이상이므로 Speaker_01로 통합)
    spk2 = worker._match_global_speaker(audio_a2, "Speaker_00")
    assert spk2 == "Speaker_01"
    
    # 3. 다른 화자 매칭 (유사도가 0.0이므로 임계값 미만 -> Speaker_02로 추가)
    spk3 = worker._match_global_speaker(audio_b, "Speaker_01")
    assert spk3 == "Speaker_02"
    assert "Speaker_02" in worker.speaker_embeddings

