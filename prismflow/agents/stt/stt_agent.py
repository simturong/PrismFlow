import time
import logging
import numpy as np
from PySide6.QtCore import QThread, Signal
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig
from .audio import MOCK_DIALOGUES, AudioCapture

logger = logging.getLogger(__name__)

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
        self.embedding_extractor = None
        self._device = None
        self._whisper_cfg = None
        
        # 화자 매칭 정보
        self.speaker_embeddings = {}
        self.speaker_count = 0
        
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
        # 화자 매칭 데이터 초기화
        self.speaker_embeddings = {}
        self.speaker_count = 0

        # 1. 마이크 장치 준비 선행
        audio_cap = AudioCapture(
            sample_rate=self.config.audio_sample_rate,
            channels=1
        )
        # 로딩 상태 진입 알림
        self.status_changed.emit("loading")
        
        if not audio_cap.start():
            self.error_occurred.emit("PyAudio 마이크 입력을 초기화할 수 없습니다.")
            self.status_changed.emit("error")
            self._running = False
            return

        # 2. OpenVINO 런타임 및 가중치 확인 로드 (오디오는 이미 큐에 버퍼링 중)
        try:
            self._load_openvino_models()
        except Exception as e:
            audio_cap.stop()
            self.error_occurred.emit(f"OpenVINO 모델 로드 실패: {str(e)}")
            self.status_changed.emit("error")
            self._running = False
            return

        # 준비 완료
        self.status_changed.emit("running")

        try:
            self._run_vad_segmented_loop(audio_cap)
        finally:
            audio_cap.stop()
            self.status_changed.emit("idle")

    def _run_vad_segmented_loop(self, audio_cap):
        """에너지 VAD 엔드포인팅으로 발화 단위를 분절하여 추론한다.

        고정 5초 윈도우를 0.5초마다 재전사하는 방식은 동일 오디오를 10회 중복 전사하고
        무음 구간까지 환각 전사하는 문제가 있다. 대신 발화(speech)가 끝나고 일정 시간
        무음(endpoint)이 지속되면 그 발화 버퍼만 1회 전사하여 중복·환각·드리프트를 차단한다.
        (6-2 안정화 항목인 vad_threshold 연동·버퍼/백프레셔 제어를 본 루프에 내장)
        """
        sr = self.config.audio_sample_rate

        # config.vad_threshold(0~1)를 에너지(RMS) 게이트로 매핑. 0.5 → 0.005 (일반 발화/무음 분리 수준)
        energy_gate = 0.01 * float(getattr(self.config, "vad_threshold", 0.5))
        endpoint_samples = int(1.0 * sr)   # 발화 후 1.0초 무음이면 종료(문장 중간 pause 파편화 방지)
        min_utt_samples = int(0.6 * sr)    # 0.6초 미만 발화는 잡음/초단 파편으로 간주해 폐기
        max_utt_samples = int(20.0 * sr)   # 백프레셔: 20초 초과 발화는 강제 분절

        utt = []                  # 현재 발화 버퍼(청크 리스트)
        in_speech = False
        silence_run = 0
        speech_seen = False
        abs_samples = 0           # 전체 타임라인 클럭(샘플 단위)
        utt_start_sample = 0

        def finalize():
            nonlocal utt, in_speech, silence_run, speech_seen, utt_start_sample
            if speech_seen and utt:
                audio = np.concatenate(utt).astype(np.float32)
                if len(audio) >= min_utt_samples:
                    speaker, text = self._process_inference(audio)
                    if text:
                        self.context.add_transcript(
                            speaker=speaker,
                            text=text,
                            start_time=round(utt_start_sample / sr, 2),
                            end_time=round(abs_samples / sr, 2),
                        )
            utt = []
            in_speech = False
            silence_run = 0
            speech_seen = False

        while self._running:
            if not self.context.is_meeting_active:
                # 미팅 비활성화 시 버퍼/타임라인 리셋
                utt = []
                in_speech = False
                silence_run = 0
                speech_seen = False
                abs_samples = 0
                time.sleep(0.1)
                continue

            chunk = audio_cap.get_audio_chunk()
            if chunk is None:
                time.sleep(0.01)
                continue

            abs_samples += len(chunk)
            rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) else 0.0
            is_speech = rms >= energy_gate

            if is_speech:
                if not in_speech:
                    in_speech = True
                    utt_start_sample = abs_samples - len(chunk)
                    utt = []
                utt.append(chunk)
                silence_run = 0
                speech_seen = True
                # 백프레셔: 발화가 과도하게 길어지면 강제 종료
                if sum(len(c) for c in utt) >= max_utt_samples:
                    finalize()
            elif in_speech:
                # 발화 중 무음: 트레일링 무음으로 포함하되 endpoint 판정
                utt.append(chunk)
                silence_run += len(chunk)
                if silence_run >= endpoint_samples:
                    finalize()

        # 종료 시 미완료 발화 마무리
        finalize()

    def _detect_device(self) -> str:
        """추론 디바이스 자동 감지: 설정 강제값 우선, 없으면 OpenVINO 가용 디바이스에서 GPU→CPU 선택.

        (NVIDIA CUDA 경로는 별도 백엔드가 필요하며 본 환경/openvino-genai에서는 미지원이므로
        Intel GPU(iGPU/Arc)→CPU 순으로 폴백한다. NPU는 Whisper 호환성 이슈로 기본 제외.)
        """
        forced = str(getattr(self.config, "stt_device", "AUTO") or "AUTO").upper()
        try:
            import openvino as ov
            available = ov.Core().available_devices
        except Exception:
            available = []

        if forced != "AUTO":
            return forced if forced in available else "CPU"
        if "GPU" in available:
            return "GPU"
        return "CPU"

    def _load_openvino_models(self):
        """OpenVINO Whisper(전사) + pyannote(화자분리) 가중치를 로컬 우선으로 로드한다.

        - Whisper: `openvino_genai.WhisperPipeline`을 감지된 디바이스로 로드(실패 시 CPU 폴백).
          추론 규격: language="<|ko|>", task="transcribe", return_timestamps=True.
          (word_timestamps는 int8 OV 모델이 cross-attention 분해를 미지원하므로 segment
          타임스탬프로 대체. 발화별 독립 전사이므로 condition_on_previous_text=False와 동치.)
        - pyannote: HF 토큰이 있을 때만 로드하며, 없으면 단일 화자(Speaker_00)로 graceful 동작.
        """
        import os
        try:
            import openvino_genai as og
        except ImportError:
            raise ImportError("openvino-genai 라이브러리가 설치되어 있지 않습니다. requirements.txt를 확인하세요.")

        model_dir = os.path.join(self.config.models_dir, self.config.whisper_model_name)
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(
                f"Whisper 모델 디렉토리를 찾을 수 없습니다: {model_dir}\n"
                f"OpenVINO 변환 모델을 해당 경로에 배치하세요."
            )

        device = self._detect_device()
        try:
            self.whisper_model = og.WhisperPipeline(model_dir, device)
        except Exception as e:
            if device != "CPU":
                # HW 가속 실패 시 CPU로 안전 폴백
                self.whisper_model = og.WhisperPipeline(model_dir, "CPU")
                device = "CPU"
            else:
                raise
        self._device = device

        cfg = self.whisper_model.get_generation_config()
        cfg.language = "<|ko|>"
        cfg.task = "transcribe"
        cfg.return_timestamps = True
        self._whisper_cfg = cfg

        # pyannote 화자분리: 토큰이 있을 때만 시도(게이트 모델). 없으면 단일 화자로 동작.
        self.diarization_model = None
        self._load_diarization_if_available()

    def _load_diarization_if_available(self):
        """HF 토큰이 있고 pyannote가 설치된 경우에만 화자분리 파이프라인과 임베딩 모델을 로드한다."""
        token = getattr(self.config, "hf_token", "") or ""
        if not token:
            return
        # waveform 텐서를 직접 입력하므로 torchcodec(FFmpeg) DLL 미로드 경고는 무해 → 억제
        import warnings
        warnings.filterwarnings("ignore", message=".*torchcodec.*")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from pyannote.audio import Pipeline, Model, Inference
        except ImportError:
            return
        try:
            # pyannote.audio 4.x는 token= 인자를 사용(구버전은 use_auth_token=)
            try:
                self.diarization_model = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1", token=token
                )
            except TypeError:
                self.diarization_model = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1", use_auth_token=token
                )
        except Exception as e:
            # 토큰 무효/약관 미동의/네트워크 오류 등은 단일 화자 폴백으로 흡수
            self.diarization_model = None

        try:
            # Speaker Embedding Model 로드 (wespeaker voxceleb)
            emb_model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM", token=token
            )
            self.embedding_extractor = Inference(emb_model, window="whole")
        except Exception as e:
            self.embedding_extractor = None

    def _process_inference(self, audio_window) -> tuple:
        """발화 오디오(float32, 16kHz, mono)를 전사하고 화자를 식별해 (speaker, text)를 반환한다."""
        text = ""
        if self.whisper_model is not None:
            try:
                res = self.whisper_model.generate(audio_window, self._whisper_cfg)
                text = str(res).strip()
            except Exception as e:
                self.error_occurred.emit(f"Whisper 추론 오류: {str(e)}")
                return "Speaker_00", ""

        speaker = "Speaker_00"
        if text and self.diarization_model is not None:
            local_speaker = self._diarize_dominant_speaker(audio_window)
            if self.embedding_extractor is not None:
                speaker = self._match_global_speaker(audio_window, local_speaker)
            else:
                speaker = local_speaker
        return speaker, text

    def _diarize_dominant_speaker(self, audio_window) -> str:
        """발화 윈도우에서 가장 길게 말한 화자 라벨을 반환한다(없으면 Speaker_00)."""
        try:
            import torch, warnings
            waveform = torch.from_numpy(np.ascontiguousarray(audio_window)).unsqueeze(0)
            # 초단 발화에서 pyannote 내부 std/mean이 NaN 경고를 내는 경우가 있어 억제(결과엔 영향 없음)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                diarization = self.diarization_model(
                    {"waveform": waveform, "sample_rate": self.config.audio_sample_rate}
                )
            # pyannote.audio 4.x는 DiarizeOutput.speaker_diarization(Annotation)을 반환,
            # 구버전은 Annotation을 직접 반환하므로 모두 호환되게 처리한다.
            annotation = getattr(diarization, "speaker_diarization", diarization)
            durations = {}
            for segment, _, label in annotation.itertracks(yield_label=True):
                durations[label] = durations.get(label, 0.0) + segment.duration
            if durations:
                top = max(durations, key=durations.get)
                # pyannote 라벨(SPEAKER_00)을 프로젝트 규격(Speaker_00)으로 정규화
                return "Speaker_" + top.split("_")[-1]
        except Exception:
            pass
        return "Speaker_00"

    def _match_global_speaker(self, audio_window, local_speaker: str) -> str:
        """발화 오디오의 임베딩을 추출하여 기존 전역 화자 임베딩 데이터베이스와 비교 매칭한다.
        
        임계값(기본 0.55)을 넘는 가장 유사한 전역 화자를 찾고,
        매칭되면 해당 화자의 임베딩을 갱신(rho_update=0.1 블렌딩)한다.
        매칭되지 않으면 새로운 전역 화자로 추가한다.
        """
        import torch
        try:
            # numpy array (float32) -> torch tensor (shape: 1 x num_samples)
            waveform = torch.from_numpy(np.ascontiguousarray(audio_window)).unsqueeze(0)
            
            # 임베딩 추출 (2D array, shape: 1 x embedding_dim)
            emb_res = self.embedding_extractor({"waveform": waveform, "sample_rate": self.config.audio_sample_rate})
            new_emb = np.array(emb_res).flatten()
            
            # 정규화
            new_emb_norm = np.linalg.norm(new_emb)
            if new_emb_norm < 1e-6:
                return "Speaker_00"
            new_emb = new_emb / new_emb_norm
            
            best_speaker = None
            best_sim = -1.0
            
            # 기존 전역 화자들과 코사인 유사도 비교
            for spk_id, ref_emb in self.speaker_embeddings.items():
                sim = float(np.dot(new_emb, ref_emb))
                if sim > best_sim:
                    best_sim = sim
                    best_speaker = spk_id
            
            # 임계값: 0.55 이상이면 동일 화자로 판정
            similarity_threshold = 0.55
            
            if best_speaker is not None and best_sim >= similarity_threshold:
                # 기존 화자에 매칭: 임베딩 점진적 업데이트 (rho_update=0.1)
                rho = 0.1
                updated_emb = (1 - rho) * self.speaker_embeddings[best_speaker] + rho * new_emb
                updated_emb_norm = np.linalg.norm(updated_emb)
                if updated_emb_norm > 1e-6:
                    self.speaker_embeddings[best_speaker] = updated_emb / updated_emb_norm
                
                logger.info(f"Speaker matched globally: Local {local_speaker} -> Global {best_speaker} (Similarity: {best_sim:.3f})")
                return best_speaker
            else:
                # 새로운 화자 추가
                self.speaker_count += 1
                new_spk_id = f"Speaker_{self.speaker_count:02d}"
                self.speaker_embeddings[new_spk_id] = new_emb
                logger.info(f"New global speaker detected: {new_spk_id} (Similarity: {best_sim:.3f})")
                return new_spk_id
                
        except Exception as e:
            logger.warning(f"Global speaker matching error, fallback to local speaker: {e}")
            return local_speaker
