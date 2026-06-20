import pytest
import sys
from PySide6.QtWidgets import QApplication
from prismflow.core.config import AppConfig


@pytest.fixture(autouse=True)
def isolate_meeting_context(tmp_path):
    """[전역 격리] 모든 테스트가 실제 사용자 DB/문서 디렉토리가 아닌 임시 격리 환경만 쓰도록 강제합니다.

    MeetingContext는 싱글톤이라 `_db_manager`가 테스트 간 누수됩니다. 특히 한 테스트가
    `context.db_manager`를 자신의 임시 DB로 바꾸고 복원하지 않으면(예: 화자 프로필을 심은 DB),
    이후 테스트가 그 DB를 그대로 물려받아 발화 화자/텍스트가 오염되는 **순서 의존 플래키**가 발생합니다.
    또한 기본 `_db_manager`/`_config`는 실제 사용자 DB·문서 경로를 가리키므로, 격리하지 않으면
    테스트가 사용자의 실제 데이터를 읽고/쓰는 심각한 오염이 발생합니다.

    이 autouse 픽스처는 매 테스트 전에 싱글톤 컨텍스트를 초기화하고 임시 DB/설정으로 교체하여,
    개별 테스트가 명시적으로 db_manager를 다시 지정하더라도 항상 깨끗한 시작점을 보장합니다.
    (load_default 자체는 패치하지 않아, 실제 기본값을 검증하는 단위 테스트는 영향을 받지 않습니다.)
    """
    from prismflow.core.context import MeetingContext
    from prismflow.core.db import DatabaseManager

    iso_config = AppConfig(
        db_path=str(tmp_path / "isolated_ctx.db"),
        docs_save_dir=str(tmp_path / "isolated_docs"),
        claude_cli_cmd="mock_claude",
        stt_mock_mode=True,
    )

    ctx = MeetingContext()
    ctx.reset()

    # 이전 테스트에서 컨텍스트 싱글톤 시그널에 남은 슬롯(좀비 코디네이터/에이전트) 누수를 차단한다.
    # 비우지 않으면 다른 테스트가 start/end_meeting 할 때 좀비 객체가 반응해 STT(PyAudio)/Flow
    # 스레드를 중복 생성하고 네이티브 접근 위반(segfault)을 유발한다.
    # (연결된 슬롯이 없을 때 PySide가 내는 RuntimeWarning은 정상 경로이므로 억제한다.)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for _sig in (ctx.signals.meeting_started, ctx.signals.meeting_ended,
                     ctx.signals.transcript_updated, ctx.signals.flow_updated):
            try:
                _sig.disconnect()
            except (RuntimeError, TypeError):
                pass

    ctx._config = iso_config
    ctx.db_manager = DatabaseManager(iso_config.db_path)

    yield

    ctx.reset()


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
