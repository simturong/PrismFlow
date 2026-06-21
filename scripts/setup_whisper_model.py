"""Whisper OpenVINO int8 모델 셋업 유틸리티.

PrismFlow의 STT 엔진은 `prismflow/resources/models/whisper-{size}-int8-ov`
디렉토리에서 OpenVINO int8(IR) Whisper 가중치를 로컬 우선으로 로드한다.
기본 번들은 small(244MB)이며, 한국어 전사 정확도를 높이려면 medium/large-v3를
추가로 내려받아야 한다. 이 스크립트는 Intel/OpenVINO 공식 org가 HuggingFace에
사전 빌드해 둔 int8-ov 모델(`OpenVINO/whisper-{size}-int8-ov`)을 그대로 받아
배치한다. (optimum/nncf 로컬 변환 없이 small과 동일한 출처·레이아웃을 보장.)

사용 예:
    .venv\\Scripts\\python.exe scripts/setup_whisper_model.py medium
    .venv\\Scripts\\python.exe scripts/setup_whisper_model.py large-v3 --force
    .venv\\Scripts\\python.exe scripts/setup_whisper_model.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 지원 모델 크기 (설정 UI/`AppConfig.whisper_dir_name`과 동일 어휘)
SUPPORTED_SIZES = ("tiny", "base", "small", "medium", "large-v3")

# HuggingFace 사전 빌드 int8-ov org (small 번들과 동일 출처)
HF_ORG = "OpenVINO"


def repo_id_for(size: str) -> str:
    """모델 크기 → HuggingFace 사전 빌드 int8-ov repo id."""
    return f"{HF_ORG}/whisper-{size}-int8-ov"


def dir_name_for(size: str) -> str:
    """모델 크기 → 로컬 OpenVINO 디렉토리명 (`AppConfig.whisper_dir_name`과 동일 규칙)."""
    return f"whisper-{size}-int8-ov"


def models_dir() -> Path:
    """STT 엔진이 탐색하는 로컬 모델 루트(`prismflow/resources/models`)."""
    return Path(__file__).resolve().parents[1] / "prismflow" / "resources" / "models"


def target_dir_for(size: str) -> Path:
    return models_dir() / dir_name_for(size)


def is_installed(size: str) -> bool:
    """필수 OpenVINO 인코더 가중치 존재로 설치 완료 여부를 판정한다."""
    d = target_dir_for(size)
    return d.is_dir() and (d / "openvino_encoder_model.xml").is_file()


def download(size: str, force: bool = False) -> Path:
    """`OpenVINO/whisper-{size}-int8-ov`를 로컬 모델 디렉토리로 내려받는다."""
    if size not in SUPPORTED_SIZES:
        raise ValueError(
            f"지원하지 않는 모델 크기: {size!r} (지원: {', '.join(SUPPORTED_SIZES)})"
        )

    target = target_dir_for(size)
    if is_installed(size) and not force:
        print(f"[skip] 이미 설치됨: {target}  (--force로 재다운로드)")
        return target

    try:
        from huggingface_hub import snapshot_download
    except ImportError as e:  # pragma: no cover - 환경 의존
        raise ImportError(
            "huggingface_hub가 설치되어 있지 않습니다. `pip install huggingface_hub` 후 다시 실행하세요."
        ) from e

    repo_id = repo_id_for(size)
    print(f"[download] {repo_id} → {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo_id, local_dir=str(target))

    if not is_installed(size):  # pragma: no cover - 네트워크/원격 변경 방어
        raise RuntimeError(
            f"다운로드는 끝났지만 OpenVINO 가중치를 확인하지 못했습니다: {target}"
        )
    print(f"[ok] 설치 완료: {target}")
    return target


def _print_list() -> None:
    print("Whisper OpenVINO int8 모델 설치 상태:")
    for size in SUPPORTED_SIZES:
        mark = "✓ 설치됨" if is_installed(size) else "✗ 미설치"
        print(f"  {mark:8}  {size:10}  ({dir_name_for(size)})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="PrismFlow Whisper OpenVINO int8 모델 다운로드/설치"
    )
    parser.add_argument(
        "size", nargs="?", choices=SUPPORTED_SIZES,
        help="설치할 모델 크기 (예: medium, large-v3)",
    )
    parser.add_argument("--force", action="store_true", help="이미 설치돼 있어도 재다운로드")
    parser.add_argument("--list", action="store_true", help="설치 상태만 출력")
    args = parser.parse_args(argv)

    if args.list or not args.size:
        _print_list()
        if not args.size:
            print("\n사용법: python scripts/setup_whisper_model.py <size> [--force]")
        return 0

    try:
        download(args.size, force=args.force)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
