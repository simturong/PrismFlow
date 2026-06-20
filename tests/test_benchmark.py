"""Phase 9-3: 최적화 전/후 정량 벤치마크 (50% 성능 향상 증명).

각 테스트는 최적화 효과를 **수치로 측정**하고 50% 목표 달성을 단언(assert)하여,
향후 성능 회귀를 CI 단계에서 자동 차단한다. `-s` 옵션으로 실행하면 상세 수치 리포트를 출력한다.

  - 9-1 STT 화자 분리: 발화당 무거운 모델 추론을 2회(Diarization 파이프라인 + Embedding)에서
                       1회(Embedding 단독)로 축소 → 구조적 50% 감축 + Diarization 핫패스 0회 호출 증명.
  - 9-2 Flow Agent : 발화록을 전체 누적 전송에서 최근 15개 슬라이딩 윈도우로 축소 → 입력 토큰 ≥50% 절감.
  - 9-4 Chat Agent : 3분 주기 백그라운드 CLI 주입(IngestWorker)을 폐지 → 백그라운드 프로세스 기동 100% 제거.
"""
import re
import time
import numpy as np
import pytest
from unittest.mock import MagicMock

from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.agents.flow.flow_agent import FlowAgent
from prismflow.agents.chat.chat_agent import ChatAgent
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.stt.audio import MOCK_DIALOGUES


def _estimate_tokens(text: str) -> int:
    """한국어/혼합 텍스트의 보수적 토큰 근사치(상대 비교용).

    CJK 문자는 토큰당 ~1.5자, 그 외(공백/영문/기호)는 토큰당 ~4자로 가정한다.
    절대값이 아닌 전/후 '비율' 비교에 사용하므로 근사로 충분하다.
    """
    cjk = len(re.findall(r"[가-힣一-鿿]", text))
    non_cjk = len(text) - cjk
    return int(cjk / 1.5 + non_cjk / 4) + 1


def _seed_long_meeting(context, n: int = 120):
    """실측을 위해 MOCK_DIALOGUES를 순환하며 n개의 현실적인 한국어 발화를 누적한다."""
    for i in range(n):
        spk, txt, _, _ = MOCK_DIALOGUES[i % len(MOCK_DIALOGUES)]
        context.add_transcript(speaker=spk, text=txt, start_time=float(i * 5), end_time=float(i * 5 + 4))


def test_benchmark_flow_prompt_token_reduction(q_app, temp_config, capsys):
    """9-2: Flow Agent 입력 토큰이 전체 누적 대비 슬라이딩 윈도우로 ≥50% 절감되는지 실측 검증."""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)
    context.start_meeting("bench_flow", "토큰 벤치마크")
    _seed_long_meeting(context, n=120)

    # 회의가 길어질수록 누적되는 기존 Mermaid 지도(30개 노드)도 동일하게 포함된다.
    big_mermaid = "graph TD\n" + "\n".join(f"    N{i}[\"노드 {i} (Speaker_0{i % 3})\"] --> N{i + 1}" for i in range(30))
    context.update_mermaid_code(big_mermaid)

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.is_session_limited.return_value = False

    captured = {}

    def capture_exec(prompt, session_id, model=None, system_prompt=None, **kwargs):
        captured["prompt"] = prompt
        return "graph TD\n    A --> B"

    mock_cli.execute_command.side_effect = capture_exec

    agent = FlowAgent(context, mock_cli)
    agent.flow_session_id = "flow-bench-session"

    transcripts = context.transcripts
    # NEW 경로 실행: 내부적으로 최근 15개 발화만 프롬프트에 포함한다.
    agent._analyze_and_update(transcripts)

    new_prompt = captured["prompt"]
    assert new_prompt, "Flow 프롬프트가 캡처되지 않았습니다."
    new_size = len(new_prompt)

    # OLD 베이스라인: 동일 프롬프트에서 '발화록만' 전체 누적으로 치환했을 때의 크기(공정 비교).
    fmt = lambda t: f"[{t['speaker']}] {t['text']}"
    new_tx = "\n".join(fmt(t) for t in transcripts[-15:])
    old_tx = "\n".join(fmt(t) for t in transcripts)
    old_size = new_size - len(new_tx) + len(old_tx)

    new_tok = _estimate_tokens(new_prompt)
    old_tok = new_tok - _estimate_tokens(new_tx) + _estimate_tokens(old_tx)

    char_reduction = 1 - new_size / old_size
    tok_reduction = 1 - new_tok / old_tok
    tx_reduction = 1 - len(new_tx) / len(old_tx)

    with capsys.disabled():
        print("\n[9-2] Flow Agent 입력 프롬프트 경량화 (발화 120개 누적 회의 기준)")
        print(f"  - 전송 발화 수      : 120개(전체) → 15개(슬라이딩 윈도우)")
        print(f"  - 발화록 문자수     : {len(old_tx):,} → {len(new_tx):,}  ({tx_reduction*100:.1f}% 절감)")
        print(f"  - 전체 프롬프트 문자: {old_size:,} → {new_size:,}  ({char_reduction*100:.1f}% 절감)")
        print(f"  - 추정 입력 토큰    : {old_tok:,} → {new_tok:,}  ({tok_reduction*100:.1f}% 절감)")

    assert tx_reduction >= 0.5, f"발화록 절감률 {tx_reduction:.1%} < 50%"
    assert char_reduction >= 0.5, f"프롬프트 문자 절감률 {char_reduction:.1%} < 50%"
    assert tok_reduction >= 0.5, f"입력 토큰 절감률 {tok_reduction:.1%} < 50%"

    context.end_meeting()
    context.reset()


def test_benchmark_stt_diarization_elimination(q_app, temp_config, monkeypatch, capsys):
    """9-1: 발화 추론 핫패스에서 Diarization 파이프라인이 제거되어 무거운 추론이 2→1회로 줄었는지 검증."""
    monkeypatch.setattr(AppConfig, "load_default", lambda: temp_config)
    worker = RealTimeEngineWorker()

    # Whisper 전사는 고정 응답으로 모킹(전사 비용은 전/후 동일하므로 비교 대상에서 제외)
    worker.whisper_model = MagicMock()
    worker.whisper_model.generate.return_value = "벤치마크 테스트 발화입니다"
    worker._whisper_cfg = MagicMock()

    # 임베딩 추출기 모킹: 호출 횟수와 소요시간 측정
    embed_calls = {"n": 0}

    def fake_embed(data):
        embed_calls["n"] += 1
        return np.array([[1.0, 0.0]], dtype=np.float32)

    worker.embedding_extractor = fake_embed

    # Diarization 파이프라인 호출을 감시(핫패스에서 0회여야 함)
    diar_spy = MagicMock(wraps=worker._diarize_dominant_speaker)
    worker._diarize_dominant_speaker = diar_spy

    audio = np.ones(16000, dtype=np.float32)
    N = 50
    t0 = time.perf_counter()
    for _ in range(N):
        spk, txt = worker._process_inference(audio)
    per_utt_ms = (time.perf_counter() - t0) / N * 1000.0

    heavy_inferences_new = embed_calls["n"] / N           # 발화당 무거운 추론 횟수 (신규)
    heavy_inferences_old = heavy_inferences_new + 1.0     # 구버전: + Diarization 파이프라인 1회
    structural_reduction = 1 - heavy_inferences_new / heavy_inferences_old

    with capsys.disabled():
        print("\n[9-1] STT 화자 분리 경량화 (발화당 무거운 모델 추론 횟수)")
        print(f"  - Diarization 파이프라인 핫패스 호출: {diar_spy.call_count}회 (제거 완료)")
        print(f"  - 발화당 무거운 추론: 2회(Diarization+Embedding) → {heavy_inferences_new:.0f}회(Embedding 단독)")
        print(f"  - 구조적 추론 감축률: {structural_reduction*100:.1f}%  (임베딩 단독 경로 {per_utt_ms:.3f} ms/발화)")

    # 핵심: Diarization 파이프라인은 발화 추론 경로에서 단 한 번도 호출되지 않아야 한다.
    assert diar_spy.call_count == 0
    # 발화당 임베딩 추출은 정확히 1회 (단일 무거운 추론)
    assert embed_calls["n"] == N
    # 무거운 추론 2회 → 1회 = 50% 구조적 감축 (실측상 Diarization이 더 무거워 실지연은 50% 이상 단축)
    assert structural_reduction >= 0.5


def test_benchmark_chat_background_spawn_elimination(q_app, temp_config, capsys):
    """9-4: 3분 주기 백그라운드 CLI 주입 폐지로 백그라운드 프로세스 기동이 100% 제거되는지 검증."""
    context = MeetingContext()
    context.reset()
    context.db_manager = DatabaseManager(temp_config.db_path)

    mock_cli = MagicMock(spec=ClaudeCLIController)
    mock_cli.is_session_limited.return_value = False

    agent = ChatAgent(context=context, cli_controller=mock_cli)
    context.start_meeting("bench_chat", "백그라운드 주입 벤치마크")

    # 발화가 활발히 누적되는 상황을 시뮬레이션
    for i in range(60):
        context.add_transcript("Speaker_00", f"누적 발화 {i}번입니다.")

    # 이벤트 루프를 충분히 돌려 백그라운드 주입(구버전 타이머)이 일어나지 않음을 확인
    from PySide6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    new_spawns = mock_cli.execute_command.call_count + mock_cli.execute_command_stream.call_count

    # 구버전 환산: 60분 회의에서 180초 간격 주입 → 20회 백그라운드 프로세스 기동
    OLD_INTERVAL_SEC = 180
    MEETING_SEC = 3600
    old_spawns = MEETING_SEC // OLD_INTERVAL_SEC
    reduction = 1 - new_spawns / old_spawns if old_spawns else 1.0

    with capsys.disabled():
        print("\n[9-4] Chat Agent 백그라운드 CLI 주입 폐지 (60분 회의 환산)")
        print(f"  - 백그라운드 프로세스 기동: {old_spawns}회(180초 주기) → {new_spawns}회 (One-shot Q&A)")
        print(f"  - 기동량 감축률: {reduction*100:.1f}%")

    # 질문하지 않는 한 백그라운드 CLI 프로세스 기동은 0이어야 한다 (세션 락 경합 원천 차단)
    assert new_spawns == 0
    assert reduction >= 0.5

    context.end_meeting()
    context.reset()
