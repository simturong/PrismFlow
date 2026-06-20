import pytest
import sys
from PySide6.QtWidgets import QApplication
from prismflow.core.config import AppConfig

@pytest.fixture(scope="session")
def q_app():
    """
    PySide6 GUI 객체를 인스턴스화하기 위해 전체 PyTest 세션 동안
    단 하나의 QApplication 인스턴스를 유지 및 제공합니다.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # PySide6 리소스 해제
    app.processEvents()

@pytest.fixture
def temp_config(tmp_path):
    """
    테스트 격리를 위해 임시 디렉토리 구조를 생성하여 적용한 AppConfig 피스처입니다.
    """
    db_file = tmp_path / "test_prismflow.db"
    docs_dir = tmp_path / "test_reports"
    
    config = AppConfig(
        db_path=str(db_file),
        claude_cli_cmd="mock_claude",
        stt_mock_mode=True,
        vad_threshold=0.6,
        audio_sample_rate=16000,
        docs_save_dir=str(docs_dir)
    )
    return config
