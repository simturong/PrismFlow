"""화면(PPT) 용어집 기반 STT 오인식 보정 검증 (i2t 교정 DB 연동)."""
from prismflow.core.glossary import extract_glossary_terms, apply_glossary_correction
from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager


# ----------------------- 용어 추출 -----------------------

def test_extract_keeps_distinctive_terms():
    text = "PrismFlow 아키텍처: Kubernetes 와 데이터베이스 연동. 회의 오늘 12 3개"
    terms = extract_glossary_terms(text)
    assert "PrismFlow" in terms
    assert "Kubernetes" in terms
    assert "데이터베이스" in terms
    # 흔한 한글 낱말/짧은 토큰/숫자는 제외
    assert "회의" not in terms      # 스톱워드
    assert "오늘" not in terms      # 스톱워드
    assert "12" not in terms        # 숫자만
    # 중복 제거
    assert len(terms) == len(set(terms))


def test_extract_empty():
    assert extract_glossary_terms("") == []
    assert extract_glossary_terms("a 1 의 !!!") == []  # 모두 너무 짧거나 숫자/기호


# ----------------------- 근접 보정 -----------------------

def test_correction_fixes_near_miss_same_script():
    glossary = {"Kubernetes", "프리즘플로우"}
    # 영문 1자 오인식 → 보정
    assert apply_glossary_correction("We deployed Kubernetis today", glossary) == "We deployed Kubernetes today"
    # 한글 1자 오인식(6자) → 보정
    assert apply_glossary_correction("프리즘플로워 회의입니다", glossary) == "프리즘플로우 회의입니다"


def test_correction_leaves_exact_and_dissimilar():
    glossary = {"Kubernetes"}
    # 정확히 일치 → 그대로
    assert apply_glossary_correction("Kubernetes is up", glossary) == "Kubernetes is up"
    # 전혀 다른 단어 → 그대로 (과교정 방지)
    assert apply_glossary_correction("I like apples", glossary) == "I like apples"


def test_correction_does_not_cross_script():
    # 전사(transliteration)는 다루지 않는다: 한글 토큰을 영문 용어로 바꾸지 않음
    glossary = {"PrismFlow"}
    assert apply_glossary_correction("프리즘플로우 좋아요", glossary) == "프리즘플로우 좋아요"


def test_correction_noop_without_glossary():
    assert apply_glossary_correction("아무 텍스트", set()) == "아무 텍스트"


# ----------------------- DB 저장/조회 -----------------------

def test_db_glossary_roundtrip_and_dedup(tmp_path):
    db = DatabaseManager(str(tmp_path / "g.db"))
    db.add_glossary_terms(["PrismFlow", "Kubernetes", "PrismFlow"])  # 중복 포함
    db.add_glossary_terms([])  # 빈 입력은 무시
    terms = db.get_glossary_terms()
    assert terms == {"PrismFlow", "Kubernetes"}


# ----------------------- add_transcript 통합 -----------------------

def test_add_transcript_applies_glossary_correction(tmp_path):
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(str(tmp_path / "ctx.db"))
    context.db_manager.add_glossary_terms(["Kubernetes"])
    context.start_meeting("s_glossary", "용어집 테스트")

    context.add_transcript("Speaker_00", "We use Kubernetis in production")
    # 화면 용어집의 정확한 표기로 보정되어 저장됨
    assert context.transcripts[-1]["text"] == "We use Kubernetes in production"

    context.end_meeting()
    context.reset()
