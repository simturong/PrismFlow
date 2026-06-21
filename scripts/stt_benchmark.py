"""STT 성능 벤치마크 하네스 (Phase 16-3).

동일 오디오에 대해 Whisper 모델 크기(small/medium/…) × 디바이스(GPU/CPU)를 바꿔가며
전사 속도(RTF)·소요시간을 측정하고, 정답 텍스트가 주어지면 정확도(CER/WER)를 산출한다.
medium+GPU 전환의 정확도/반응성 트레이드오프를 정량적으로 비교하기 위한 도구다.

지표 정의:
- RTF(Real-Time Factor) = 추론 소요초 / 오디오 길이초. 1보다 작을수록 실시간보다 빠르다.
- CER/WER = 정답 대비 문자/단어 오류율(레벤슈타인 편집거리 / 정답 길이). 낮을수록 정확.

사용 예:
    .venv\\Scripts\\python.exe scripts/stt_benchmark.py path\\to.wav --models small medium --devices GPU CPU
    .venv\\Scripts\\python.exe scripts/stt_benchmark.py a.wav --ref-file a_ref.txt
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


# ----------------------- 순수 지표 함수 (오디오/모델 비의존, 항상 테스트 가능) -----------------------

def _levenshtein(a, b) -> int:
    """두 시퀀스(문자열 또는 토큰 리스트) 간 편집거리(삽입/삭제/치환=1)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ai = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ai == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def _normalize(text: str) -> str:
    """공백 정규화(연속 공백→1칸, 양끝 트림). 대소문자는 보존(한국어 위주)."""
    return " ".join((text or "").split())


def cer(reference: str, hypothesis: str) -> float:
    """문자 오류율(Character Error Rate). 공백 제거 후 문자 단위 편집거리/정답 문자수."""
    ref = _normalize(reference).replace(" ", "")
    hyp = _normalize(hypothesis).replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str) -> float:
    """단어 오류율(Word Error Rate). 공백 토큰 단위 편집거리/정답 단어수."""
    ref = _normalize(reference).split()
    hyp = _normalize(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def rtf(audio_sec: float, infer_sec: float) -> float:
    """Real-Time Factor = 추론초/오디오초. 오디오 길이가 0이면 0.0."""
    if audio_sec <= 0:
        return 0.0
    return infer_sec / audio_sec


# ----------------------- 실모델 측정 (opt-in: 오디오/openvino 필요) -----------------------

def _load_audio(wav_path: str):
    """WAV를 16kHz mono float32로 로드하고 (samples, 길이초)를 반환."""
    import librosa
    audio, sr = librosa.load(wav_path, sr=16000, mono=True)
    return audio, len(audio) / float(sr)


def transcribe_once(wav_path: str, model_dir: str, device: str):
    """주어진 OpenVINO Whisper 모델/디바이스로 파일 전체를 1회 전사하고 측정치를 반환."""
    import openvino_genai as og
    audio, audio_sec = _load_audio(wav_path)

    t_load = time.time()
    pipe = og.WhisperPipeline(model_dir, device)
    load_sec = time.time() - t_load
    cfg = pipe.get_generation_config()
    cfg.language = "<|ko|>"
    cfg.task = "transcribe"

    t0 = time.time()
    text = str(pipe.generate(audio, cfg)).strip()
    infer_sec = time.time() - t0
    return {
        "audio_sec": audio_sec,
        "load_sec": load_sec,
        "infer_sec": infer_sec,
        "rtf": rtf(audio_sec, infer_sec),
        "text": text,
    }


def run_benchmark(wav_path: str, models, devices, reference: str | None, models_dir: str):
    rows = []
    for size in models:
        model_dir = os.path.join(models_dir, f"whisper-{size}-int8-ov")
        if not os.path.isdir(model_dir):
            print(f"[skip] 미설치: {model_dir}  (python scripts/setup_whisper_model.py {size})")
            continue
        for dev in devices:
            try:
                r = transcribe_once(wav_path, model_dir, dev)
            except Exception as e:
                print(f"[error] {size}/{dev}: {e}")
                continue
            r["model"], r["device"] = size, dev
            if reference:
                r["cer"], r["wer"] = cer(reference, r["text"]), wer(reference, r["text"])
            rows.append(r)
            acc = f" CER={r['cer']:.3f} WER={r['wer']:.3f}" if reference else ""
            print(f"[{size:7}/{dev:3}] audio={r['audio_sec']:.1f}s load={r['load_sec']:.1f}s "
                  f"infer={r['infer_sec']:.2f}s RTF={r['rtf']:.3f}{acc}")
            print(f"            → {r['text'][:90]}{'…' if len(r['text']) > 90 else ''}")
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="PrismFlow STT 벤치마크")
    p.add_argument("wav", help="측정할 16kHz WAV 경로")
    p.add_argument("--models", nargs="+", default=["small", "medium"], help="모델 크기 목록")
    p.add_argument("--devices", nargs="+", default=["GPU", "CPU"], help="디바이스 목록")
    p.add_argument("--ref-file", help="정답 텍스트 파일(있으면 CER/WER 산출)")
    args = p.parse_args(argv)

    if not os.path.isfile(args.wav):
        print(f"[error] WAV를 찾을 수 없습니다: {args.wav}", file=sys.stderr)
        return 1
    reference = None
    if args.ref_file and os.path.isfile(args.ref_file):
        reference = Path(args.ref_file).read_text(encoding="utf-8")

    models_dir = str(Path(__file__).resolve().parents[1] / "prismflow" / "resources" / "models")
    run_benchmark(args.wav, args.models, args.devices, reference, models_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
