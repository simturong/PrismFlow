# PrismFlow Handoff — Phase 6-3-1 완료 / 6-3-2 라이브 1차 실측 (2026-06-20, 세션 2)

## 0. 한 줄 요약
**6-3-1(설정 UI↔실엔진 배선) 완료**. **6-3-2 라이브 E2E 1차 실측 성공**(실엔진 풀 구동: 전사→Flow→Chat→보고서 전 구간 동작). 실측에서 도출된 이슈를 6-3-3/6-3-4/6-3-6/Phase7로 분배 기록함. 다음 세션은 **6-3-4 하드닝(콜드스타트/가시성)** 또는 **6-3-3 멀티화자**부터.

## 1. 먼저 읽을 것 (순서 고정)
1. `agent.md` — 코딩 수칙 (Karpathy 4원칙, 수칙 6: docs/가 정본, artifacts/는 handoff 전용)
2. `docs/implementation_plan.md` §5 "Phase 6-3" + Phase 7 (정본 계획; 6-3-4/Phase7에 6-3-2 실측 도출 항목 반영됨)
3. `docs/task.md` "Phase 6-3" 체크리스트 (6-3-1 [x], 6-3-2 E2E [x] + 발견 이슈 5건 미체크)
4. 본 핸드오프

## 2. 이번 세션에 한 일
### 6-3-1 설정 UI ↔ 실엔진 배선 — 완료
- `prismflow/core/config.py`: 모델크기→OV 디렉토리 매핑을 단일 정본 `AppConfig.whisper_dir_name()`로 추출, `_apply_db_settings`가 사용.
- `prismflow/ui_common/settings_ui.py`:
  - ① Mock 모드 `QCheckBox` ② HF 토큰 Password 필드(저장 시 DB + `os.environ["HF_TOKEN"]`) ③ 가속 콤보 `AUTO/GPU/NPU/CPU` 정합(레거시 `CPU/CUDA/OpenVINO`는 로드 시 AUTO 폴백) ④ 모델크기↔로컬 OV 디렉토리 **존재 표시 라벨**(`_update_model_status`) ⑤ 저장 시 `stt_mock_mode/whisper_model_name/stt_device/vad_threshold/hf_token` AppConfig 실시간 반영.
- 테스트: `tests/test_core.py`(+3: STT DB 오버라이드/가속 폴백/매핑 헬퍼), 신설 `tests/test_ui.py`(+2: SettingsDialog 저장/로드 라운드트립·레거시 폴백). → **`pytest tests/` = 46 passed, 1 skipped**.
- 배선 원리(중요): STT 워커는 회의 시작마다 `RealTimeEngineWorker()`가 `AppConfig.load_default()`로 **DB값을 재로드** → 실제 바인딩 경로는 **DB 영속화**. 설정 변경은 반드시 **회의 시작 전**에 해야 적용됨(진행 중 변경은 실행 중 워커에 미반영).
- 도달성: 트레이 **설정** → `SettingsDialog` 정상 연결됨(`tray.py:show_settings`).

### 6-3-2 라이브 E2E — 1차 성공 (사용자 실측, 캡처/로그 보관)
- 회의 1건(20260620_214414, 21:44~21:46) 실엔진 풀 구동. **실Whisper 한국어 전사 9건 → context → Flow 다이어그램 → Chat(전사맥락 반영 답변) → 종료 → 보고서 자동생성·열림**(`~/Documents/PrismFlow/Reports/2026-06-20/report_20260620_214414.md`). 전 구간 동작 확인.
- "전사 안 됨"은 오인이었음 — 화면에 찍힌 한국어는 사용자가 문제를 묘사한 발화가 정확히 전사된 결과.

## 3. 6-3-2에서 도출된 이슈 (후속 단계로 분배 — task.md에 미체크로 등록)
| 심각도 | 이슈 | 근거 | 후속 |
|:--|:--|:--|:--|
| 높음 | **콜드스타트 블라인드 윈도우**: `_run_real_loop`이 모델 로드 완료 후 AudioCapture 시작 → 로드 구간(~10-30s) 초기 발화 유실 | 21:44:14 시작, 모델 HF 체크 21:44:23까지, 캡처는 그 후 | 6-3-4: 캡처를 로드와 병행/선행 + 버퍼링 + "준비 중" 표시 |
| 높음 | **실시간 전사 가시성 부재**: 라이브 자막 없음 → 30초 Flow/보고서로만 드러나 "미작동" 오인 | Flow 첫 갱신 21:45:16 | 6-3-4/6-3-5: 경량 실시간 전사 표시 |
| 중 | **화자분리 온라인 의존**(오프라인 위배): 기동 시 pyannote가 huggingface.co HEAD 요청 | 21:44:21~23 httpx HF 로그 4건 | Phase 7: 토큰리스 오프라인 로컬 로드 |
| 중 | 단일화자만 테스트 → 전역 일관성(6-3-3) 미평가 | 전 노드 Speaker_00 | 6-3-5 다인 재검 |
| 낮음 | `QFont::setPointSize: Point size <= 0 (-1)` 폰트 폴백 경고 | 기동 첫 줄 | 6-3-6 정리 |

## 4. 사용자 제기 설계 결정 — 오프라인/토큰리스 화자분리 (Phase 7에 반영 완료)
- 질문: 오프라인 오픈소스인데 HF 토큰란이 있으면 배포 받은 사람은 어떻게 쓰나?
- 답/결정: **HF 토큰은 "다운로드 시점"에만 필요, "실행 시점"엔 불필요.** 배포본엔 pyannote 가중치를 번들하고 `HF_HUB_OFFLINE=1`(또는 로컬 `config.yaml`)로 토큰·네트워크 없이 로드 → 엔드유저 토큰 불필요. 토큰란은 개발자/온라인 업데이트용 선택값. 토큰·모델 둘 다 없으면 이미 단일화자(Speaker_00) graceful 동작. (구현은 Phase 7, 설계는 `implementation_plan.md` Phase 7 "pyannote 토큰리스 오프라인 로드"에 명시함.)

## 5. git 상태
- 브랜치 `master`. 이번 세션 변경 커밋됨: 6-3-1 코드+테스트+docs+본 핸드오프.
- 회귀: `pytest tests/` → 46 passed, 1 skipped.
- 모델 가중치(`prismflow/resources/models/`)는 `.gitignore` 제외 유지.

## 6. 환경 사실 (재확인 불필요 — 직전 핸드오프 §3과 동일)
- HW: Intel Core Ultra 7 258V + Arc 140V iGPU(16GB) + NPU. OpenVINO devices=GPU/NPU/CPU. NVIDIA 없음.
- `HF_TOKEN` 사용자 환경변수 등록됨(setx). pyannote 게이트 3종 동의 완료.
- Whisper: `whisper-small-int8-ov` 로컬 존재. STT 스택 설치 완료(openvino 2026.2.1 등).
- 라이브 STT 단독: `.venv\Scripts\python.exe stt_live_test.py`.

## 7. 다음 세션 우선순위 (권장 순서)
1. **6-3-4 하드닝 — 콜드스타트 + 가시성** (가장 체감 큰 두 이슈; 사용자 "미작동" 오인을 직접 해소)
   - `stt_agent._run_real_loop`: AudioCapture를 `_load_openvino_models()` 전/병행으로 시작하고 로드 동안 청크 버퍼링. 로드 완료 신호로 "엔진 준비 완료" 표시. status_changed 신호를 트레이/오버레이에 노출.
2. **6-3-3 멀티화자 전역 일관성** (발화 임베딩 누적 코사인 매칭 경량안 우선).
3. (Phase 7 착수 전) 6-3-5 다인 실회의 재검, 6-3-6 회귀·폰트 경고 정리.
- 각 단락마다 관련 `pytest` 즉시 실행. Phase(6-3) 완료 선언 전 `docs/history.md` 선행 작성(아직 미작성 — 6-3 전체 완료 시점에).

## 8. 다음 세션 시작 프롬프트 (복붙용)
> 본문은 채팅에 별도 안내. 요지: agent.md→본 핸드오프→plan §5/Phase7→task.md 순 정독 후 **6-3-4 콜드스타트+가시성**부터 외과적으로. 회귀 유지(46 passed 기준).
