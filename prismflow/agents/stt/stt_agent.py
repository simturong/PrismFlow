import time
import logging
import numpy as np
from PySide6.QtCore import QThread, Signal
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig
from .audio import MOCK_DIALOGUES, AudioCapture

logger = logging.getLogger(__name__)

import re as _re

_REPEAT_PUNCT = _re.compile(r"[\s,\.!?~\-…]+$")


def collapse_repetitions(text: str, max_run: int = 2) -> str:
    """연속으로 동일하게 반복되는 토큰을 최대 max_run개로 줄여 반복 환각을 제거한다.

    Whisper(특히 int8 양자화 medium)는 필러/무음에서 "아, 아, 아, …"처럼 같은 토큰을
    수십 번 되풀이하는 디코딩 루프에 빠지곤 한다. 자연스러운 2회 반복("네 네")은 보존하고
    3회 이상 연속 동일 토큰만 잘라낸다(구두점 차이는 무시하고 비교).
    """
    if not text:
        return text
    tokens = text.split()
    if len(tokens) < max_run + 1:
        return text
    out = []
    run_key = None
    run_len = 0
    for tok in tokens:
        key = _REPEAT_PUNCT.sub("", tok)
        if key and key == run_key:
            run_len += 1
            if run_len > max_run:
                continue  # 초과 반복은 버림
        else:
            run_key = key
            run_len = 1
        out.append(tok)
    return " ".join(out)


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
        self._wav_file = None

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
        wav_initialized = False
        
        while self._running:
            if self.context.is_meeting_active:
                if self.context.is_meeting_paused:
                    time.sleep(0.1)
                    continue

                if not wav_initialized:
                    self._init_wav_file(self.context.current_session_id)
                    wav_initialized = True
                    
                if dialogue_idx < len(MOCK_DIALOGUES):
                    speaker, text, start_time, end_time = MOCK_DIALOGUES[dialogue_idx]
                    
                    self.context.add_transcript(
                        speaker=speaker,
                        text=text,
                        start_time=start_time,
                        end_time=end_time
                    )
                    # 모크 쓰기: 파일 생성 보증을 위한 1초 분량 가짜 무음 기록
                    self._write_audio_to_wav(np.zeros(16000))
                    dialogue_idx += 1
                else:
                    # 루프 회독이 끝났으나 회의가 계속 진행 중일 때 대기
                    pass
                
                # mock_interval 초 동안 대기하되 스레드 중단 요청에 빠르게 반응하도록 0.1초씩 끊어서 확인
                sleep_steps = int(self.mock_interval / 0.1)
                for _ in range(sleep_steps):
                    if not self._running or not self.context.is_meeting_active or self.context.is_meeting_paused:
                        break
                    time.sleep(0.1)
            else:
                # 회의가 종료되었거나 활성화 전이면 대기
                if wav_initialized:
                    self._close_wav_file()
                    wav_initialized = False
                dialogue_idx = 0
                time.sleep(0.1)
                
        if wav_initialized:
            self._close_wav_file()
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
        
        # 실시간 녹음 파일 생성
        self._init_wav_file(self.context.current_session_id)

        try:
            self._run_vad_segmented_loop(audio_cap)
        finally:
            audio_cap.stop()
            self._close_wav_file()
            self.status_changed.emit("idle")

    def _process_interim_inference(self, audio_window) -> str:
        """임시 오디오 윈도우를 가볍게 전사하여 텍스트만 반환합니다."""
        if self.whisper_model is not None:
            try:
                res = self.whisper_model.generate(audio_window, self._whisper_cfg)
                return collapse_repetitions(str(res).strip())
            except Exception as e:
                logger.debug(f"Interim Whisper inference error: {e}")
        return ""

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
        # Phase 17-3: 확정 지연 단축 — 0.7초 무음이면 문장 단위로 빨리 확정해 "확정 문장 누적"을 촉진.
        # (확정이 빨라지면 라이브 자막이 확정 기록으로 자주 넘어가, interim이 앞 문장을 잃는 체감이 줄어든다.)
        endpoint_samples = int(0.7 * sr)   # 발화 후 0.7초 무음이면 종료(문장 경계에서 신속 확정)
        min_utt_samples = int(0.5 * sr)    # 0.5초 미만 발화는 잡음/초단 파편으로 간주해 폐기
        max_utt_samples = int(7.0 * sr)    # 백프레셔: 7초 초과 발화는 강제 분절 (앞문장 짤림 및 왜곡 방지)
        # interim(라이브 자막)은 진행 중 발화의 '전체'를 보여 앞부분을 잃지 않게 한다.
        # endpoint가 0.7초로 짧아 발화(=문장)가 대체로 짧으므로 전체 전사도 가볍다.
        # 다만 사용자가 쉬지 않고 매우 길게 말하는 폭주 발화를 대비해 상한(7초)만 둔다. (강제 분절 단위와 동기화)
        interim_window_samples = int(7.0 * sr)

        utt = []                  # 현재 발화 버퍼(청크 리스트)
        in_speech = False
        silence_run = 0
        speech_seen = False
        abs_samples = 0           # 전체 타임라인 클럭(샘플 단위)
        utt_start_sample = 0
        interim_sample_count = 0  # 실시간 임시 전사용 샘플 카운터

        def finalize():
            nonlocal utt, in_speech, silence_run, speech_seen, utt_start_sample, interim_sample_count
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
            interim_sample_count = 0

        while self._running:
            if not self.context.is_meeting_active:
                # 미팅 비활성화 시 버퍼/타임라인 리셋
                utt = []
                in_speech = False
                silence_run = 0
                speech_seen = False
                abs_samples = 0
                interim_sample_count = 0
                time.sleep(0.1)
                continue

            if self.context.is_meeting_paused:
                # 일시중지 상태인 경우 오디오 청크를 읽어버리되(버퍼 방지), VAD 추론 및 WAV 저장은 건너뛰고 대기
                chunk = audio_cap.get_audio_chunk()
                self.context.signals.partial_transcript_updated.emit("임시", "")
                time.sleep(0.01)
                continue

            chunk = audio_cap.get_audio_chunk()
            if chunk is None:
                time.sleep(0.01)
                continue

            # 실시간 오디오 파일에 프레임 기록
            self._write_audio_to_wav(chunk)

            abs_samples += len(chunk)
            rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) else 0.0
            is_speech = rms >= energy_gate

            if is_speech:
                if not in_speech:
                    in_speech = True
                    utt_start_sample = abs_samples - len(chunk)
                    utt = []
                    interim_sample_count = 0
                utt.append(chunk)
                silence_run = 0
                speech_seen = True
                
                # 실시간 임시(Interim) 전사 피드
                interim_sample_count += len(chunk)
                if interim_sample_count >= int(0.5 * sr):
                    interim_sample_count = 0
                    audio_so_far = np.concatenate(utt).astype(np.float32)[-interim_window_samples:]
                    if len(audio_so_far) >= min_utt_samples:
                        interim_text = self._process_interim_inference(audio_so_far)
                        if interim_text:
                            self.context.signals.partial_transcript_updated.emit("임시", interim_text)
                
                # 백프레셔: 발화가 과도하게 길어지면 강제 종료
                if sum(len(c) for c in utt) >= max_utt_samples:
                    finalize()
            elif in_speech:
                # 발화 중 무음: 트레일링 무음으로 포함하되 endpoint 판정
                utt.append(chunk)
                silence_run += len(chunk)
                
                # 무음 구간에서도 임시 전사를 갱신해줌 (예: 말하는 도중 잠시 쉴 때)
                interim_sample_count += len(chunk)
                if interim_sample_count >= int(0.5 * sr):
                    interim_sample_count = 0
                    audio_so_far = np.concatenate(utt).astype(np.float32)[-interim_window_samples:]
                    if len(audio_so_far) >= min_utt_samples:
                        interim_text = self._process_interim_inference(audio_so_far)
                        if interim_text:
                            self.context.signals.partial_transcript_updated.emit("임시", interim_text)
                            
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
            # 디렉토리명(whisper-{size}-int8-ov)에서 크기를 역산해 설치 명령을 안내한다.
            name = self.config.whisper_model_name
            size = name[len("whisper-"):-len("-int8-ov")] if name.startswith("whisper-") and name.endswith("-int8-ov") else name
            raise FileNotFoundError(
                f"Whisper '{size}' 모델이 설치되어 있지 않습니다: {model_dir}\n"
                f"설치: python scripts/setup_whisper_model.py {size}\n"
                f"(또는 설정에서 small 모델 선택)"
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
        """로컬 오프라인 캐시 우선으로 로드하며, 실패 시 HF 토큰 온라인 방식으로 폴백한다."""
        import os
        import warnings
        warnings.filterwarnings("ignore", message=".*torchcodec.*")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from pyannote.audio import Model, Inference
        except ImportError:
            return

        # 1단계: 로컬 오프라인(토큰리스) 로드 시도
        local_config_yaml = os.path.join(self.config.models_dir, "diarization", "config.yaml")
        local_hf_cache = os.path.join(self.config.models_dir, "hf_cache")
        
        if os.path.isfile(local_config_yaml) and os.path.isdir(local_hf_cache):
            logger.info("Local offline pyannote models detected. Attempting offline tokenless load...")
            # 허깅페이스 오프라인 모드 강제 및 캐시 디렉토리 오버라이드
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["HF_HOME"] = local_hf_cache
            try:
                # 임베딩 오프라인 로드 (HF_HOME이 로컬 캐시로 고정되어 있으므로 캐시 폴더에서 불러옴)
                emb_model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM")
                self.embedding_extractor = Inference(emb_model, window="whole")
                logger.info("Successfully loaded pyannote offline embedding model (Diarization pipeline skipped).")
                return
            except Exception as e:
                logger.warning(f"Failed to load pyannote offline: {e}. Falling back to online mode.")
                # 실패 시 환경변수 롤백 및 온라인 폴백 진행
                os.environ.pop("HF_HUB_OFFLINE", None)
                os.environ.pop("HF_HOME", None)
                self.embedding_extractor = None

        # 2단계: 기존 HF 토큰 온라인 폴백 로드
        token = getattr(self.config, "hf_token", "") or ""
        if not token:
            return

        try:
            # Speaker Embedding Model 로드 (wespeaker voxceleb)
            emb_model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM", token=token
            )
            self.embedding_extractor = Inference(emb_model, window="whole")
            logger.info("Successfully loaded pyannote online embedding model.")
        except Exception as e:
            logger.warning(f"Failed to load pyannote online embedding model: {e}")
            self.embedding_extractor = None

    def _process_inference(self, audio_window) -> tuple:
        """발화 오디오(float32, 16kHz, mono)를 전사하고 화자를 식별해 (speaker, text)를 반환한다."""
        text = ""
        if self.whisper_model is not None:
            try:
                res = self.whisper_model.generate(audio_window, self._whisper_cfg)
                text = str(res).strip()
                # 반복 디코딩 루프(예: "아, 아, 아, …") 환각 제거
                text = collapse_repetitions(text)
            except Exception as e:
                self.error_occurred.emit(f"Whisper 추론 오류: {str(e)}")
                return "Speaker_00", ""

            # ── 무음 환각 블랙리스트 필터 ──────────────────────────────────────────
            # Whisper는 무음·저에너지 구간에서 학습 데이터에 자주 등장하는 문구를
            # 그럴싸하게 만들어내는 경향이 있다(특히 뉴스 앵커 오프닝, 자막 문구 등).
            # 아래 키워드가 포함된 전사 결과는 환각으로 간주하고 빈 문자열로 무효화한다.
            _HALLUCINATION_BLACKLIST = [
                "MBC 뉴스",
                "KBS 뉴스",
                "SBS 뉴스",
                "뉴스데스크",
                "김성현입니다",
                "김지경입니다",
                "앵커입니다",
                "기자입니다",
                "자막",
                "Copyright",
                "Subtitles by",
                "ご視聴ありがとう",         # 일본어 환각 패턴
                "字幕",                      # 중국어 자막 환각
            ]
            text_lower = text.lower()
            if any(kw.lower() in text_lower for kw in _HALLUCINATION_BLACKLIST):
                logger.debug(f"[VAD] 환각 텍스트 차단: {text!r}")
                text = ""
            # ──────────────────────────────────────────────────────────────────────

        speaker = "Speaker_00"
        if text and self.embedding_extractor is not None:
            # Diarization Pipeline 호출을 완전히 스킵하고, 단독 Embedding Extractor로 글로벌 코사인 매칭을 수행합니다.
            # Local dominant speaker 추정 과정을 생략하여 획기적인 속도 향상을 얻습니다.
            speaker = self._match_global_speaker(audio_window, "Speaker_00")
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

    def _init_wav_file(self, session_id: str):
        """회의 세션 시작 시 실시간 녹음용 WAV 파일을 열고 초기 헤더를 생성합니다."""
        import datetime
        import wave
        from pathlib import Path
        try:
            if hasattr(self.context, "current_session_dir") and self.context.current_session_dir:
                wav_filepath = Path(self.context.current_session_dir) / f"meeting_{session_id}.wav"
            else:
                today = datetime.date.today().strftime("%Y-%m-%d")
                recordings_dir = Path(self.config.docs_save_dir).parent / "Recordings" / today
                recordings_dir.mkdir(parents=True, exist_ok=True)
                wav_filepath = recordings_dir / f"meeting_{session_id}.wav"
            
            self._wav_file = wave.open(str(wav_filepath), 'wb')
            self._wav_file.setnchannels(1)
            self._wav_file.setsampwidth(2) # 16-bit
            self._wav_file.setframerate(self.config.audio_sample_rate)
            logger.info(f"Initialized real-time audio WAV recording: {wav_filepath}")
        except Exception as e:
            logger.error(f"Failed to initialize audio WAV file: {e}")
            self._wav_file = None

    def _write_audio_to_wav(self, chunk):
        """Float32 오디오 numpy 배열을 Int16으로 변환하여 WAV에 실시간 기록합니다."""
        if self._wav_file and chunk is not None and len(chunk) > 0:
            try:
                # Float32 (-1.0 ~ 1.0) -> Int16 (-32768 ~ 32767)
                int_data = (chunk * 32767.0).astype(np.int16)
                self._wav_file.writeframes(int_data.tobytes())
            except Exception as e:
                logger.error(f"Failed to write audio frame to WAV file: {e}")

    def _close_wav_file(self):
        """기동 중인 WAV 파일을 안전하게 닫아 플러시를 마칩니다."""
        if self._wav_file:
            try:
                self._wav_file.close()
                logger.info("Closed real-time audio WAV recording file.")
            except Exception as e:
                logger.error(f"Failed to close WAV file: {e}")
            finally:
                self._wav_file = None
