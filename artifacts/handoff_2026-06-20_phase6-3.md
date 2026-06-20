# PrismFlow Handoff — Phase 6-3 착수 (2026-06-20)

## 0. 한 줄 요약
Phase 6(실 STT/화자분리 엔진) **완료·커밋**. 다음은 **Phase 6-3(배포 전 완성도 확보)** 를 **6-3-1 → 6-3-6 순서대로** 진행한다. (사용자 승인 완료, 자율 진행 허가)

## 1. 먼저 읽을 것 (순서 고정)
1. `agent.md` — 내비게이션/코딩 수칙 (Karpathy 4원칙, 수칙 6: docs/가 정본, artifacts/는 handoff 전용)
2. `docs/implementation_plan.md` §5 **"Phase 6-3"** 섹션 — 정식 상세 계획(정본)
3. `docs/task.md` **Phase 6-3** 체크리스트
4. `prismflow/agents/stt/stt_agent.py` — 실엔진(VAD 분절 루프 + Whisper + pyannote)
5. `prismflow/ui_common/settings_ui.py` — 6-3-1에서 손댈 설정 UI
6. `prismflow/core/config.py` — 6-3-1 config 측 배선 **이미 완료**(`_apply_db_settings`)

## 2. 현재 상태 (git)
- 브랜치 `master`, HEAD `0a251db`
- `99832f6` feat: Phase 6 실엔진 / `0a251db` docs: 6-3 계획 + 6-3-1 config 배선
- 작업 트리 클린. 모델 가중치(`prismflow/resources/models/`, 245MB)는 `.gitignore` 제외.
- 회귀: `pytest tests/` → **41 passed, 1 skipped**(`STT_LIVE` 옵트인)

## 3. 검증된 환경 사실 (재확인 불필요)
- HW: Intel Core Ultra 7 258V + **Arc 140V iGPU(16GB)** + NPU. OpenVINO devices = GPU/NPU/CPU. NVIDIA 없음.
- STT 스택 설치됨: `openvino 2026.2.1`, `openvino-genai 2026.2.1.0`, `pyaudio 0.2.14`, `pyannote.audio 4.0.4`, `torch 2.12.1+cpu`, `librosa`, `soundfile`. numpy 2.4.6 유지(충돌 없음).
- Whisper 모델: `prismflow/resources/models/whisper-small-int8-ov` (다운로드 완료). GPU 전사 검증(3s→0.5s).
- 화자분리: pyannote.audio 4.x. **`HF_TOKEN` 사용자 환경변수 등록됨(setx)**. 게이트 3종 동의 완료(segmentation-3.0 / speaker-diarization-3.1 / **speaker-diarization-community-1**). 토큰 없으면 단일화자 graceful.
- `claude` CLI v2.1.183. 모델: Flow/Chat=`claude-haiku-4-5`, Report=`claude-opus-4-8`.

## 4. 핵심 주의점 (지난 세션 시행착오 — history.md Phase 6 참조)
- **Windows 셸 인자 금물**: 다중줄 프롬프트는 STDIN 전달(`shell=False`). `cli_controller`가 이미 그렇게 구현됨.
- **CLI 세션ID는 UUID 강제** → `cli_controller._normalize_session_id`(uuid5)로 처리됨.
- **에이전트 CLI는 격리 실행**: `--strict-mcp-config`/`--setting-sources user`/중립 cwd/`--system-prompt`. 프로젝트 CLAUDE.md·메모리 미참조.
- **word_timestamps 미지원**(int8 OV) → segment 타임스탬프 사용.
- **무음 환각** → VAD 게이팅 필수. 현재 endpoint 1.0s, energy_gate=`0.01×vad_threshold`.
- pyannote 4.x 출력은 `DiarizeOutput.speaker_diarization`(Annotation).

## 5. Phase 6-3 남은 작업 (순서대로)
- **6-3-1 (진행 중)**: 설정↔실엔진 배선
  - ✅ config 측: `AppConfig._apply_db_settings`로 stt_mock_mode/whisper_model_size→model dir/hardware_acceleration→stt_device/vad_threshold/hf_token DB 오버라이드 완료.
  - ⏳ **남음**: `settings_ui.py`에 ① Mock 모드 토글(QCheckBox) ② HF 토큰 입력 필드 ③ 가속 옵션을 `AUTO/GPU/NPU/CPU`로 정합(현재 CPU/CUDA/OpenVINO) ④ 모델크기↔OV 디렉토리 존재 표시 ⑤ 저장 시 `stt_mock_mode`/`hf_token` DB 저장 + AppConfig 실시간 반영. + 설정 오버라이드 단위테스트(`tests/test_core.py` 패턴).
- **6-3-2**: `stt_mock_mode=False`로 `run.bat` 풀 구동 — 실음성→전사→Flow→Chat→종료→보고서 육안 검증 + 버그 수정.
- **6-3-3**: 멀티 화자 전역 일관성(발화 임베딩 점증 클러스터링/코사인 매칭).
- **6-3-4**: 첫 실행 UX·에러 하드닝(모델/토큰/장치 실패 가시화 + Mock 폴백).
- **6-3-5**: 사용자 실회의 검증 → 피드백 반영.
- **6-3-6**: 정리·회귀(테스트 확장, `stt_live_test.py` 정리, Pretendard 폰트 누락 처리).
- **완료 기준**: ①에이전트 앱 통합 실측 ②사용자 실회의 검증 ③버그/사용성 개선 반영. → 통과 후 Phase 7(배포).

## 6. 작업 규칙 리마인더
- 코드 한 단락마다 관련 `pytest` 즉시 실행. Phase 완료 선언 전 `docs/history.md` 선행 작성, `docs/task.md`는 진행 즉시 갱신. 복제본 금지(docs/가 정본).
- 라이브 STT 단독 확인: `.venv\Scripts\python.exe stt_live_test.py` (새 터미널, HF_TOKEN 적용).
- 보안: HF 토큰이 과거 채팅에 평문 노출됨 → 사용자에게 회전 권장(완료 시 setx 갱신).
