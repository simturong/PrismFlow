"""STT 실엔진 라이브 검증 스크립트 (Phase 6-2 정확도/VAD 튜닝용 개발 도구).

실제 마이크로 한국어를 말하면 OpenVINO Whisper가 발화 단위로 전사해 출력한다.
앱 전체를 띄우지 않고 STT 엔진만 빠르게 확인할 때 사용한다. (검증 후 삭제 가능)

실행:  .venv\\Scripts\\python.exe stt_live_test.py
"""
import time
import warnings
import numpy as np

warnings.filterwarnings("ignore")  # pyannote/torch 초단발화 경고 억제

from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.stt.audio import AudioCapture

DURATION_SEC = 25  # 테스트 시간

def main():
    worker = RealTimeEngineWorker()
    print("[1/3] OpenVINO Whisper 모델 로딩 중...")
    worker._load_openvino_models()
    print(f"      로드 완료 (device={worker._device}, "
          f"화자분리={'ON' if worker.diarization_model else 'OFF(단일화자)'})")

    cap = AudioCapture(sample_rate=worker.config.audio_sample_rate, channels=1)
    if not cap.start():
        print("[ERROR] 마이크를 열 수 없습니다.")
        return

    sr = worker.config.audio_sample_rate
    gate = 0.01 * float(worker.config.vad_threshold)
    endpoint = int(1.0 * sr)
    min_utt = int(0.6 * sr)

    print(f"[2/3] 마이크 준비 완료 (vad_gate={gate:.4f}). "
          f"지금부터 {DURATION_SEC}초간 한국어로 말해보세요!\n")

    utt, in_speech, silence, speech_seen = [], False, 0, False
    t0 = time.time()
    while time.time() - t0 < DURATION_SEC:
        chunk = cap.get_audio_chunk()
        if chunk is None:
            time.sleep(0.01)
            continue
        rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) else 0.0
        if rms >= gate:
            if not in_speech:
                in_speech = True
                utt = []
            utt.append(chunk)
            silence = 0
            speech_seen = True
        elif in_speech:
            utt.append(chunk)
            silence += len(chunk)
            if silence >= endpoint:
                audio = np.concatenate(utt).astype(np.float32)
                if len(audio) >= min_utt and speech_seen:
                    speaker, text = worker._process_inference(audio)
                    if text:
                        print(f"  [{speaker}] {text}")
                utt, in_speech, silence, speech_seen = [], False, 0, False

    cap.stop()
    print("\n[3/3] 종료. 전사가 정확하면 STT 엔진 검증 완료입니다.")

if __name__ == "__main__":
    main()
