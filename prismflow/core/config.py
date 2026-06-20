import os
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class AppConfig:
    # 데이터베이스 경로
    db_path: str = field(default_factory=lambda: str(Path.home() / "Documents" / "PrismFlow" / "prismflow.db"))
    
    # Claude CLI 실행 명령어
    claude_cli_cmd: str = "claude"
    
    # STT 설정
    stt_mock_mode: bool = True
    vad_threshold: float = 0.5
    audio_sample_rate: int = 16000

    # STT 실엔진(OpenVINO Whisper + pyannote) 설정
    # 로컬 가중치 우선 탐색 경로 (오프라인 배포 전제)
    models_dir: str = field(default_factory=lambda: str(Path(__file__).resolve().parents[1] / "resources" / "models"))
    # OpenVINO Whisper 모델 디렉토리명 (models_dir 하위)
    whisper_model_name: str = "whisper-small-int8-ov"
    # 추론 디바이스 선호: "AUTO"면 자동 감지(GPU→NPU→CPU), 또는 "GPU"/"NPU"/"CPU" 강제
    stt_device: str = "AUTO"
    # pyannote 화자분리 게이트 모델 다운로드용 Hugging Face 토큰 (없으면 환경변수 HF_TOKEN 사용)
    hf_token: str = field(default_factory=lambda: os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "")
    
    # 보고서 저장 경로
    docs_save_dir: str = field(default_factory=lambda: str(Path.home() / "Documents" / "PrismFlow" / "Reports"))

    def __post_init__(self):
        # 필요한 폴더 생성
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            Path(self.docs_save_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            # 권한 등의 문제로 폴더 생성 실패 시 예외 처리
            pass
            
        # DB의 settings에서 claude_cli_cmd 값을 조회하여 오버라이드 시도
        try:
            db_file = Path(self.db_path)
            if db_file.exists():
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                cur = conn.cursor()
                # settings 테이블 존재 확인
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
                if cur.fetchone():
                    cur.execute("SELECT value FROM settings WHERE key='claude_cli_cmd'")
                    row = cur.fetchone()
                    if row:
                        self.claude_cli_cmd = row[0]
                conn.close()
        except Exception:
            pass

    @classmethod
    def load_default(cls):
        """기본 설정을 로드합니다."""
        return cls()
