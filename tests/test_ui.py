import pytest
from PySide6.QtWidgets import QMessageBox

from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager
from prismflow.ui_common.settings_ui import SettingsDialog


def test_settings_dialog_roundtrip(q_app, tmp_path, monkeypatch):
    """설정 다이얼로그가 STT 실엔진 설정을 DB에 저장하고 다시 로드하는지(라운드트립) 검증.

    6-3-1 핵심: Mock 토글·모델 크기·가속·VAD·HF 토큰이 DB와 AppConfig에 정확히 반영되어야
    다음 회의 시작 시 STT 워커가 그 값으로 실엔진을 기동한다.
    """
    # QMessageBox가 테스트를 블로킹하지 않도록 no-op 처리
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))

    db = DatabaseManager(str(tmp_path / "ui_settings.db"))
    context = MeetingContext()
    original_db = context.db_manager
    context.db_manager = db
    try:
        dlg = SettingsDialog()
        dlg.mock_check.setChecked(False)
        dlg.model_combo.setCurrentText("medium")
        dlg.accel_combo.setCurrentText("GPU")
        dlg.vad_spin.setValue(0.7)
        dlg.hf_input.setText("hf_ui_token")
        dlg.path_input.setText("claude")
        dlg.save_settings()

        # 1. DB 영속화 확인
        assert db.get_setting("stt_mock_mode") == "false"
        assert db.get_setting("whisper_model_size") == "medium"
        assert db.get_setting("hardware_acceleration") == "GPU"
        assert db.get_setting("vad_threshold") == "0.7"
        assert db.get_setting("hf_token") == "hf_ui_token"

        # 2. in-memory AppConfig 실시간 반영 확인
        assert dlg.config.stt_mock_mode is False
        assert dlg.config.whisper_model_name == "whisper-medium-int8-ov"
        assert dlg.config.stt_device == "GPU"
        assert dlg.config.vad_threshold == 0.7
        assert dlg.config.hf_token == "hf_ui_token"

        # 3. 새 다이얼로그가 저장값을 그대로 다시 로드하는지(라운드트립) 확인
        dlg2 = SettingsDialog()
        assert dlg2.mock_check.isChecked() is False
        assert dlg2.model_combo.currentText() == "medium"
        assert dlg2.accel_combo.currentText() == "GPU"
        assert dlg2.vad_spin.value() == 0.7
        assert dlg2.hf_input.text() == "hf_ui_token"
    finally:
        context.db_manager = original_db


def test_settings_dialog_legacy_accel_fallback(q_app, tmp_path, monkeypatch):
    """구버전 UI가 남긴 비호환 가속값(예: OpenVINO)이 로드 시 AUTO로 폴백되는지 검증."""
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))

    db = DatabaseManager(str(tmp_path / "ui_legacy.db"))
    db.set_setting("hardware_acceleration", "OpenVINO")

    context = MeetingContext()
    original_db = context.db_manager
    context.db_manager = db
    try:
        dlg = SettingsDialog()
        assert dlg.accel_combo.currentText() == "AUTO"
    finally:
        context.db_manager = original_db
