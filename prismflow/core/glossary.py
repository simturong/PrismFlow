"""화면(PPT) 용어집 기반 STT 오인식 보정 (i2t 교정 DB 연동).

발표 화면에서 읽은 정확한 표기(용어집)를 이용해, 음성인식이 같은 단어를 살짝 다르게 받아쓴
경우(같은 문자 체계 내 근접 오인식)를 그 정확한 표기로 되돌린다.

설계 원칙 — 과교정(false positive) 방지:
- 토큰은 영문/숫자 3자 이상, 한글 3자 이상만 다룬다(흔한 2자어 오교정 차단).
- 같은 문자 체계(영문↔영문, 한글↔한글)끼리만 비교한다(전사 표기 차이는 별도 문제라 다루지 않음).
- 길이 차가 크면 후보에서 제외하고, 유사도 임계값(기본 0.85)을 높게 둬 확실할 때만 치환한다.
"""
import re
from difflib import SequenceMatcher

# 영문/숫자 3자 이상 또는 한글 3자 이상 토큰
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[가-힣]{3,}")

# 도메인 용어로 보기 어려운 흔한 한글 낱말(용어집에 넣지 않아 오교정을 줄인다)
_STOPWORDS = {
    "회의", "오늘", "내용", "그리고", "그러면", "우리", "여기", "저기", "이것", "그것", "저것",
    "합니다", "입니다", "때문", "경우", "사용", "가능", "진행", "관련", "대해", "위해", "통해",
    "하지만", "그래서", "이번", "다음", "정도", "부분", "생각", "이야기", "말씀", "여러분",
}

# 용어집 보관 상한(메모리/보정 비용 상한)
MAX_GLOSSARY_TERMS = 200


def extract_glossary_terms(text: str) -> list:
    """슬라이드 텍스트에서 도메인 용어 후보(고유명사·기술용어 등)를 중복 없이 추출한다."""
    if not text:
        return []
    out = []
    seen = set()
    for tok in _TOKEN_RE.findall(text):
        if tok in seen:
            continue
        is_ascii = tok[0].isascii()
        if is_ascii:
            keep = len(tok) >= 3              # 영문/혼합: 3자 이상(PrismFlow, Kubernetes 등)
        else:
            keep = len(tok) >= 3 and tok not in _STOPWORDS  # 한글: 3자 이상 + 흔한 낱말 제외
        if keep:
            seen.add(tok)
            out.append(tok)
    return out


def _same_script(a: str, b: str) -> bool:
    return a[0].isascii() == b[0].isascii()


def apply_glossary_correction(text: str, glossary, threshold: float = 0.8) -> str:
    """전사 텍스트의 토큰을 용어집의 정확한 표기로 근접 보정한다(확실할 때만).

    이미 용어집과 정확히 일치하는 토큰은 그대로 두고, 같은 문자 체계의 후보 중 유사도가 임계값
    이상이면서 길이 차가 작은 경우에만 치환한다.
    """
    if not text or not glossary:
        return text
    terms = [t for t in glossary if len(t) >= 3]
    if not terms:
        return text
    gset = set(glossary)

    def repl(m):
        tok = m.group(0)
        if tok in gset:
            return tok  # 이미 정확한 표기
        best, best_r = None, 0.0
        low = tok.lower()
        for term in terms:
            if not _same_script(tok, term):
                continue
            if abs(len(tok) - len(term)) > 2:
                continue
            r = SequenceMatcher(None, low, term.lower()).ratio()
            if r > best_r:
                best_r, best = r, term
        if best is not None and best_r >= threshold and best != tok:
            return best
        return tok

    return _TOKEN_RE.sub(repl, text)
