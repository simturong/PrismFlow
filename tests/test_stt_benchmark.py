"""scripts/stt_benchmark.py 순수 지표 함수 검증 (오디오/모델 비의존, 항상 실행).

실모델 측정(transcribe_once)은 GPU·대용량 모델·오디오가 필요하므로 여기서 다루지 않는다
(라이브 측정은 scripts/stt_benchmark.py를 직접 실행).
"""
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stt_benchmark.py"
_spec = importlib.util.spec_from_file_location("stt_benchmark", _SCRIPT)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)


def test_levenshtein_basics():
    assert bench._levenshtein("abc", "abc") == 0
    assert bench._levenshtein("abc", "abd") == 1      # 치환 1
    assert bench._levenshtein("abc", "ab") == 1       # 삭제 1
    assert bench._levenshtein("", "abc") == 3
    assert bench._levenshtein("abc", "") == 3


def test_cer_perfect_and_errors():
    assert bench.cer("안녕하세요 회의 시작합니다", "안녕하세요 회의 시작합니다") == 0.0
    # 공백은 무시: 정답 "회의시작"(4자), 1자 오인식 → 0.25
    assert bench.cer("회의 시작", "회의 시자") == pytest.approx(0.25)
    # 빈 정답 처리
    assert bench.cer("", "") == 0.0
    assert bench.cer("", "x") == 1.0


def test_wer_word_level():
    assert bench.wer("회의 자료 검토", "회의 자료 검토") == 0.0
    # 3단어 중 1단어 오류 → 1/3
    assert bench.wer("회의 자료 검토", "회의 문서 검토") == pytest.approx(1 / 3)


def test_rtf():
    assert bench.rtf(10.0, 5.0) == 0.5     # 실시간의 2배 빠름
    assert bench.rtf(10.0, 20.0) == 2.0    # 실시간보다 느림
    assert bench.rtf(0.0, 1.0) == 0.0      # 길이 0 방어


def test_normalize_collapses_whitespace():
    assert bench._normalize("  회의   시작  ") == "회의 시작"
