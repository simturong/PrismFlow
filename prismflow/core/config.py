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

    @classmethod
    def load_default(cls):
        """기본 설정을 로드합니다."""
        return cls()
