"""scripts/setup_whisper_model.py 순수 헬퍼 검증 (네트워크 미사용)."""
import importlib.util
from pathlib import Path

import pytest

from prismflow.core.config import AppConfig

# scripts/는 패키지가 아니므로 파일 경로로 직접 로드
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_whisper_model.py"
_spec = importlib.util.spec_from_file_location("setup_whisper_model", _SCRIPT)
setup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup)


def test_dir_name_matches_appconfig():
    """셋업 스크립트의 디렉토리 매핑이 AppConfig 단일 정본과 일치해야 한다."""
    for size in setup.SUPPORTED_SIZES:
        assert setup.dir_name_for(size) == AppConfig.whisper_dir_name(size)


def test_repo_id_format():
    assert setup.repo_id_for("medium") == "OpenVINO/whisper-medium-int8-ov"
    assert setup.repo_id_for("large-v3") == "OpenVINO/whisper-large-v3-int8-ov"


def test_target_dir_under_models_dir():
    target = setup.target_dir_for("medium")
    assert target.name == "whisper-medium-int8-ov"
    assert target.parent.name == "models"


def test_supported_sizes_cover_ui_choices():
    """설정 UI 콤보 항목(tiny..large-v3)을 모두 지원해야 한다."""
    for size in ("tiny", "base", "small", "medium", "large-v3"):
        assert size in setup.SUPPORTED_SIZES


def test_download_rejects_unknown_size():
    with pytest.raises(ValueError):
        setup.download("huge")


def test_is_installed_false_for_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "models_dir", lambda: tmp_path)
    assert setup.is_installed("medium") is False
