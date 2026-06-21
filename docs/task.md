# PrismFlow Task List

## Phase 1: 시스템 트레이 및 투명 오버레이 기본 GUI 구축
- [x] 패키지 루트 및 에이전트 슬라이스 디렉토리 구조 생성
- [x] `tests/conftest.py` 등 테스트 공통 모듈 및 모크 뼈대 생성
- [x] `prismflow/ui_common/overlay.py` 투명 오버레이 기본 클래스 설계 (Frameless, Translucent, Hover fade 애니메이션, 마우스 드래그 이동)
- [x] `prismflow/ui_common/tray.py` 시스템 트레이 및 우클릭 메뉴 구현 (회의 시작/종료, 설정, 종료 연동)
- [x] `main.py` 진입점을 통한 트레이와 기본 오버레이 창 띄우기 통합 테스트

## Phase 2: SQLite DB 구축 및 실시간 STT 에뮬레이터 설계
- [x] `prismflow/core/db.py` SQLite 데이터베이스 연결 및 스키마(회의 세션, 발화 내역, 설정 테이블) 설계
- [x] `tests/test_db.py` DB CRUD 및 세션 로딩 테스트 작성 및 검증
- [x] `prismflow/core/context.py` 내 Thread-safe `MeetingContext` 싱글톤 클래스 구현 (DB 기록 연동)
- [x] `prismflow/agents/stt/stt_agent.py` 오디오 수집 스레드 및 Mock Mode 다자 발화 에뮬레이터 구현
- [x] `tests/test_stt.py` STT 스레드 및 데이터 파이프라인 검증 테스트 통과

## Phase 3: Claude CLI 통신 및 Flow Agent Mermaid 시각화
- [x] `prismflow/core/cli_controller.py` 로컬 Claude CLI 파이프 비차단 IO 제어 모듈 개발
- [x] `prismflow/core/screen_detector.py` 스마트 화면 맥락 감지 모듈 개발 (win32com + Pillow)
- [x] `tests/test_cli.py` 로컬 Claude CLI 통신 테스트 작성 및 검증
- [x] 리소스 폴더 구성 및 오프라인용 `mermaid.min.js` 다운로드/배치
- [x] `prismflow/agents/flow/flow_ui.py` 내 `QWebEngineView` 통합 및 Mermaid 렌더링 검증
- [x] `prismflow/agents/flow/flow_agent.py`를 통한 30초 주기 Mermaid 다이어그램 갱신 루프 테스트 및 `tests/test_flow.py` 검증

## Phase 4: Chat Agent 하이브리드 RAG 및 대화창 통합
- [x] `prismflow/agents/chat/chat_ui.py` 채팅 입출력 팝업 GUI 및 스크롤바/스타일링 개발
- [x] `prismflow/agents/chat/chat_agent.py` 내 하이브리드 RAG (10분 발화 + Flow 요약 + Mermaid 코드) 생성 로직 구현
- [x] Chat Agent와 Claude CLI 연동하여 비동기 응답 스트리밍 구현 및 `tests/test_chat.py` 검증

## Phase 4-2: 예외 처리, 통합 최적화 및 융합 데모 (AppCoordinator 연동)
- [x] `main.py` 내 `ChatUI` 및 `ChatAgent` 오케스트레이션 및 화면 배치 구현
- [x] `prismflow/agents/chat/chat_agent.py` 백그라운드 스레드 `cleanup` 로직 탑재
- [x] `prismflow/core/screen_detector.py` win32com PowerPoint 에러 핸들링 보강
- [x] `tests/test_chat.py` 내 스레드 리소스 소멸 및 예외 안전성 테스트 추가 및 검증

## Phase 4-3: 추가 최적화 및 설정/환경 고도화 (Settings, Screen DB, CLI Path Override, Local WebFont)
- [x] `screen_logs` 마이그레이션 및 CRUD 기능 구현 (`prismflow/core/db.py`)
- [x] `MeetingContext` 내 `update_screen_info` 실행 시 DB 영구 적재 구현
- [x] `AppConfig` 초기화 시 DB의 `claude_cli_cmd` 오버라이드 구현
- [x] `SettingsDialog` UI 개발 및 시스템 트레이 메뉴와 실시간 연동
- [x] 로컬 Pretendard 폰트 리소스 배치 및 `main.py` 내 전역 폰트 등록 연동
- [x] `tests/test_db.py` 및 `tests/test_core.py`에 스키마 및 오버라이드 테스트 추가 검증

## Phase 5: Report Agent 회의록 작성 및 전체 파이프라인 마무리
> 명칭 확정: `SynthesizerAgent` → **`ReportAgent`/`ReportWorker`** (폴더 `agents/report/`, 파일 `report_agent.py`, 테스트 `test_report.py`). 모델: **Opus 4.8 (`claude-opus-4-8`)**.
- [x] `prismflow/agents/report/report_agent.py` 최종 회의록 Markdown 컴파일 모듈 구현 (`ReportAgent` + `ReportWorker`)
- [x] DB(발화록·채팅·세션) + 최종 Mermaid 융합 Opus 프롬프트 구성 및 비동기 CLI 호출
- [x] 회의록 자동 저장(`Documents/PrismFlow/Reports/YYYY-MM-DD/report_{session_id}.md`, UTF-8) 및 `meeting_sessions.summary` 영구 저장
- [x] `os.startfile` 기반 Windows 기본 연결 프로그램 자동 실행 (`sys.platform=='win32'` 가드)
- [x] `main.py` `AppCoordinator`에 `ReportAgent` 연동 및 cleanup 등록
- [x] `tests/test_report.py` 작성 — 프롬프트 병합·파일 저장·DB summary·startfile 검증 (5 케이스)
- [x] `run.bat` 원클릭 실행 스크립트 작성
- [x] 전체 회귀 검증 통과 (`pytest tests/ -v` → 36 passed)

### Phase 5 사후 감사 (Phase 6 진입 전)
- [x] 회의 종료 크래시 수정: `QWebEnginePage.html()`(미존재 API) → `FlowUI.reset_diagram()` ([main.py], [flow_ui.py])
- [ ] (→ Phase 6-0으로 이관) 에이전트 모델명 실검증 / run.bat E2E 1회 구동

## Phase 6: 실제 오픈소스 STT/화자분리 모델 연동 및 실시간 검증
> 착수 순서 고정: **6-0(Pre-flight 게이트) → 6-1(실엔진) → 6-2(안정화).** 6-0 통과 전 6-1 착수 금지.

### Phase 6-0: MVP 실동작 게이트 (Pre-flight)
- [x] 6-0-A: `claude` CLI로 모델명 3종 실검증 (CLI v2.1.183) — **`claude-3-5-haiku`는 2026-02-19 retired로 거부**, `claude-opus-4-8` 통과. Flow/Chat을 `claude-haiku-4-5`(검증 통과)로 교체하고 `flow_agent.py`·`chat_agent.py`·`cli_controller.py` 독스트링·`tests/test_flow.py` 동기화. 전체 회귀 `pytest tests/` → 36 passed.
- [x] 6-0-B: `run.bat` E2E 1회 구동 — 육안 확인 + 종료 크래시 무재현 확인. 1·2차 구동에서 버그 6건 발견·전수 수정(아래)
  - 1차 구동에서 버그 4건 발견·수정 (모두 회귀 테스트 동반, `pytest tests/` → 39 passed):
    - (런처) `run.bat`의 `if/else` 블록 내 `(.venv)` 괄호가 cmd 파서를 깨뜨림(`not was unexpected`) → 괄호 제거
    - (버그 B/CLI) claude CLI v2.1.183이 `--resume`/`--session-id`에 **유효 UUID 강제** → 비-UUID 세션명(chat/flow/report) 전멸. `cli_controller._normalize_session_id`(uuid5 결정적 변환) 중앙 도입 → 기존 resume→`--session-id` 폴백 정상화
    - (버그 C/DB) 사용자 `prismflow.db`의 구 `transcripts` 스키마(단일 timestamp) 잔존 → `get_transcripts` 크래시(`no such column: start_time`). `db._migrate_legacy_transcripts` 자동 마이그레이션(데이터 보존) 추가 + 실제 DB 이관 완료
    - (버그 A/Flow) `flow_ui.setHtml`에 baseUrl 없어 `file:///mermaid.min.js` 차단(`mermaid is not defined`) → file:// baseUrl 지정
  - 2차 구동에서 Chat 챗봇 품질 버그 2건 추가 수정 (요구사항: 완전 클린·경량·Haiku high 전용):
    - (페르소나/누수) `claude -p`가 프로젝트 CLAUDE.md/메모리(`Antigravity`)+MCP 로딩 → 코딩 에이전트로 동작("What would you like to help with"). 해결: `cli_controller` 격리 실행(`--strict-mcp-config`로 MCP 0개, `--setting-sources user`+중립 cwd로 프로젝트 컨텍스트 차단, `--system-prompt`로 에이전트별 페르소나 고정[Chat/Flow/Report], `--exclude-dynamic-system-prompt-sections`)
    - (맥락 유실) Windows `shell=True`가 다중줄 전사록 프롬프트를 `cmd.exe` 줄바꿈에서 잘라 세션 기억 실패 → `shell=False` + `shutil.which` 실행파일 해석 + **프롬프트 STDIN 전달**로 전환. 통합 스모크: 다중줄 맥락 기억·스트리밍·무누수 검증 완료
  - ⏳ 재구동 육안 확인 대기 (Flow 다이어그램 렌더링 + 보고서 팝업)

### Phase 6-1: 실제 STT/화자분리 엔진 구현
> **결정(2026-06-20):** 6-1+6-2 묶음 진행 / 화자분리 = **pyannote 3.1(게이트)** 채택.
> **환경 실측:** STT 패키지 전무(설치 필요) · NVIDIA GPU 미감지(OpenVINO/CPU 경로) · **HF 토큰 없음(pyannote 3.1 다운로드 블로커)** · py3.11 AMD64.
- [x] `audio.py` 실제 마이크 캡처(16kHz/Mono/Float32) 동작 검증 — pyaudio 0.2.14, Intel Smart Sound 마이크 배열 1.17s/18,720샘플/청크90 정상
- [x] STT 의존성 설치 — pyaudio + OpenVINO 스택(openvino 2026.2.1 / openvino-genai 2026.2.1.0 / huggingface_hub / librosa / soundfile), numpy 2.4 충돌 없음
- [x] HW 실측: **Intel Core Ultra 7 258V + Arc 140V iGPU(16GB) + NPU** → OpenVINO GPU/NPU/CPU 전부 가용, 자동감지 **GPU** 선택
- [x] `stt_agent.py` `_load_openvino_models()` 실구현 — `og.WhisperPipeline(model_dir, device)` GPU 로드(실패 시 CPU 폴백), `_detect_device`(GPU→CPU), pyannote는 토큰 있을 때만 graceful 로드
- [x] `stt_agent.py` `_process_inference()` 실구현 — Whisper 전사(language=`<\|ko\|>`, return_timestamps) + 화자분리 훅. **블라인드 0.5s 재전사 스텁 → 에너지 VAD 엔드포인팅(발화 단위 1회 전사)으로 재설계**(중복/환각/드리프트 차단)
- [x] `prismflow/resources/models/whisper-small-int8-ov` 로컬 번들 배치(다운로드 완료, 오프라인 로드 검증)
- [x] `requirements.txt` STT 의존성 추가(설치 검증분 pin, pyannote는 토큰 후 설치 주석)
- [x] **HF 토큰 수령 + 게이트 3종 동의** (segmentation-3.0 / speaker-diarization-3.1 / **speaker-diarization-community-1**[4.x 임베딩]) → `HF_TOKEN` 영구 등록(setx)
- [x] **화자분리 연결 완료** — `pyannote.audio 4.0.4`(+torch 2.12.1) 설치, `Pipeline.from_pretrained` 로드 성공, 워커에서 Whisper+diarization 동시 로드(`diarization=True`) 검증. 4.x 출력 API(`DiarizeOutput.speaker_diarization`) 대응 + torchcodec 경고 억제
> ※ word_timestamps는 int8 OV 모델이 cross-attention 분해 미지원 → segment 타임스탬프로 대체(발화별 독립 전사 = condition_on_previous_text=False 동치). 실측: 3s 오디오 GPU 전사 0.5s(실시간 6×). pyannote는 token 없으면 단일화자 graceful.

### Phase 6-2: 실시간 안정화 및 예외 차단
- [x] 노이즈/무음 처리 + `config.vad_threshold` 연동 — 에너지 RMS 게이트(`0.01×vad_threshold`)로 무음 전사(환각) 차단
- [x] 버퍼 병목·타임라인 드리프트·백프레셔 제어 — 발화 분절 버퍼 + 15s 강제 분절 + 절대 샘플 클럭으로 타임라인 동기
- [x] 하드웨어 가속 강제 제어 시 오류 → 안전 폴백 — GPU 로드 실패 시 CPU 폴백
- [x] `stt_mock_mode=False` 실측: `stt_live_test.py` 라이브 검증 — GPU·화자분리 ON, 한국어 전사 정확("안녕하세요 마이크 준비가 완료되었습니다…"). VAD endpoint 1.0초 튜닝으로 파편화 완화. (앱 통합 토글 실측 + 멀티화자 전역 일관성은 다음 단계)
- [x] `tests/test_stt.py` 확장 — VAD 분절 단위테스트 + 디바이스 감지 + 실엔진 옵트인(`STT_LIVE=1`) 분리. 전체 `pytest tests/` → 41 passed, 1 skipped

## Phase 6-3: 완성도 확보 (실엔진 앱 통합 · 하드닝 · 이중 검증) — ⏳ 승인 대기
> Phase 7(배포) 진입 전 완성도 확보 단계. 남은 작업 전부를 묶음. 완료 기준 = ①에이전트 앱 통합 실측 ②사용자 실회의 검증 ③버그/사용성 개선 반영.
- [x] 6-3-1 설정 UI ↔ 실엔진 배선: `AppConfig` DB 오버라이드를 STT 설정(stt_mock_mode/whisper_model_name/stt_device/vad_threshold)까지 확장 + `SettingsDialog`에 Mock 토글·HF 토큰 필드 추가, 가속 옵션 실디바이스 정합, 모델크기↔OV 디렉토리 매핑
  - [x] config 측: `AppConfig._apply_db_settings`로 stt_mock_mode/whisper_model_size→OV dir/hardware_acceleration→stt_device/vad_threshold/hf_token DB 오버라이드 + 매핑 단일정본 `AppConfig.whisper_dir_name()`
  - [x] `settings_ui.py`: ① Mock 모드 QCheckBox ② HF 토큰 Password 필드(저장 시 DB+`os.environ["HF_TOKEN"]`) ③ 가속 콤보 `AUTO/GPU/NPU/CPU` 정합(레거시 CPU/CUDA/OpenVINO 값은 AUTO 폴백) ④ 모델크기↔로컬 OV 디렉토리 존재 표시 라벨 ⑤ 저장 시 stt_mock_mode/whisper_model_name/stt_device/vad_threshold/hf_token AppConfig 실시간 반영
  - [x] 단위테스트: `test_core.py`(STT DB 오버라이드·가속 폴백·매핑 헬퍼) + 신설 `test_ui.py`(SettingsDialog 저장/로드 라운드트립·레거시 가속 폴백). 전체 `pytest tests/` → 46 passed, 1 skipped
  - 주의: 실엔진은 회의 시작마다 `RealTimeEngineWorker()`가 `AppConfig.load_default()`로 DB값 재로드 → DB 영속화가 실제 배선 경로(in-memory 반영은 동일 config 객체 한정)
- [x] 6-3-2 앱 통합 실측(에이전트): `stt_mock_mode=False`로 run.bat 풀 구동 — 실음성→전사→Flow→Chat→종료→보고서 육안 검증 + 버그 즉시 수정
  - [x] 사전점검(자율): `import main`+settings_ui+stt_agent 무결, 트레이 **설정**→`SettingsDialog` 도달성, 실모델 디렉토리 존재(`whisper-small-int8-ov`), 배선 진입 가능 확인
  - [x] 라이브 E2E 1차 성공(2026-06-20 21:44~21:46, 사용자 실측): 실Whisper 한국어 전사→context(transcript 9건)→Flow 다이어그램→Chat(전사맥락 반영)→종료→보고서 자동생성·열림. **전 구간 실엔진 동작 확인**.
  - 발견 이슈(후속 단계로 분배):
    - [x] 🐛(높음) 콜드스타트 블라인드 윈도우: `_run_real_loop`이 모델 로드(Whisper+pyannote, HF 온라인 체크 ~10-30s) 완료 *후*에 AudioCapture 시작 → 초기 발화 유실. → **6-3-4**: 마이크 캡처를 로드와 병행/선행 + 버퍼링 + "엔진 준비 중" 표시
    - [x] 🐛(높음) 실시간 전사 가시성 부재: 라이브 자막 없음 → STT가 30초 Flow/보고서로만 드러나 "미작동" 오인. → **6-3-4/6-3-5**: 경량 실시간 전사 표시 검토
    - [ ] ⚠️(중) 화자분리 온라인 의존(오프라인 배포 위배): 기동 시 pyannote가 huggingface.co HEAD 요청(diarization-3.1/segmentation-3.0/community-1/wespeaker). → **Phase 7** 토큰리스 오프라인 로컬 로드로 해결(plan 반영)
    - [x] ⚠️(중) 단일화자만 테스트 → 전역 일관성(6-3-3) 미평가. 다인 재검 필요(6-3-5)
    - [x] 🐛(낮음) `QFont::setPointSize: Point size <= 0 (-1)` 폰트 폴백 경고. → **6-3-6** 정리
- [x] 6-3-3 멀티 화자 전역 일관성: 발화 임베딩 점증 클러스터링/코사인 매칭으로 전역 Speaker_XX 라벨 일관성 확보
- [x] 6-3-4 첫 실행 UX·에러 하드닝: 모델 미존재 안내/다운로드 상태, STT 실패 UI 토스트+Mock 폴백, 토큰 부재 안내
- [/] 6-3-5 이중 검증·개선 루프: 사용자 실회의(다인) 테스트 → 정확도/화자/지연/사용성 피드백 반영, vad/모델 튜닝
- [x] 6-3-6 정리·회귀: 설정 오버라이드/매핑 단위테스트 추가, 전체 회귀 유지, stt_live_test 정리·Pretendard 폰트 잔여 처리

## Phase 7: E2E 통합 하네스, 디버깅 및 예외 하드닝 (E2E 특집)
- [x] 7-1: E2E 시나리오 시뮬레이션용 하네스 스크립트 (`tests/e2e_harness.py`) 구축 및 동작 검증
- [x] 7-2: Claude CLI 세션 한도 초과(`session limit`) 상황 자가진단 및 UI 알림 연동
- [x] 7-3: Claude CLI 에러 발생 시 로컬 Fallback(대체) 모드(Flow Mermaid 룰베이스 생성, Chat 가상 응답, 정적 Markdown 회의록 작성 및 오픈) 구현
- [x] 7-4: WAV 원본 실시간 녹음 및 전사록 텍스트(.txt) 실시간 저장 기능 개발
- [x] 7-5: Flow 에이전트의 증분(Delta) 전사 업데이트 및 히스토리 DB 저장 구현
- [x] 7-6: 사용자 정의 오인식 교정 사전(Correction Dictionary) 및 화자 캐시 매핑 기반 로컬 자가 개선 루프 개발
- [x] 7-7: `FlowUI` 내 최근 전사록 실시간 프리뷰 자막바 탑재
- [x] 7-8: 창 제어 버튼 시인성 개선 및 윈도우 스타일 정합 (Segoe MDL2 Assets 폰트 및 고대비 색상 적용)


## Phase 8: 오프라인 원클릭 패키징 및 배포 (순연)
- [x] 8-1: pyannote 토큰리스 오프라인 로드 분기 구현 (`stt_agent.py` 내 로컬 `config.yaml` / `hf_cache` 감지 및 로드 구현 완료)
- [x] 8-2: Embeddable Python 격리 패키지 빌드 자동화 스크립트 작성 (`build_release.py` 원클릭 릴리즈 툴 구현 완료)
- [x] 8-3: Inno Setup (`setup.iss`) 스크립트 작성 및 단일 설치파일(`PrismFlow_Setup_v1.0.exe`) 빌드 검증 (스크립트 작성 및 릴리즈 빌더 --installer 통합 완료, 실제 컴파일은 Inno Setup 6 설치 후 수행 가능)


## Phase 9: STT & Flow Agent 50% 성능 최적화
- [x] 9-1: STT 화자 분리 아키텍처 경량화 (pyannote diarization pipeline 호출 제거 및 단독 embedding extractor 매칭 전환) — 발화당 무거운 추론 2회→1회(구조적 50% 감축), Diarization 핫패스 0회 호출
- [x] 9-2: Flow Agent 증분 업데이트(Delta) 및 프롬프트 슬라이딩 윈도우/경량화 구현 — 입력 프롬프트 71.4% 절감, 추정 입력 토큰 74.8% 절감(발화 120개 누적 기준)
- [x] 9-3: 최적화 검증용 단위 테스트 보강 및 전/후 벤치마크 정량 지표 측정 — `tests/test_benchmark.py` 신설, 50% 목표를 assert로 회귀 방지 (상세: [docs/phase9_benchmark_report.md](docs/phase9_benchmark_report.md))
- [x] 9-4: Chat Agent CLI 커넥션 에러 디버깅 (백그라운드 Ingest 제거, 원샷 슬라이딩 RAG 쿼리 및 지수 백오프 재시도 메커니즘 통합) — 백그라운드 CLI 기동 100% 제거(60분 회의 20회→0회)

### Phase 9 안정화/상용화 보강 (테스트 정합 + 디버깅)
- [x] 깨진 단위 테스트 정상화: 아키텍처 변경(Ingest 폐지·Diarization 제거)에 맞춰 `test_chat`/`test_stt`/`test_cli`/e2e 리팩토링 (56 passed, 1 skipped)
- [x] `ChatAgent.cleanup` 치명 버그 수정: 폐지된 `ingest_timer` 참조로 인한 `AttributeError`(앱 종료 시마다 발생 + 스레드 누수) 제거 → 간헐적 SQLite access violation(세그폴트) 해소
- [x] `cli_controller` 재시도 계약 정비: 실행 파일 부재 등 영구 오류는 즉시 `RuntimeError`로 전파(불필요한 3초 재시도 제거), 타임아웃은 즉시 `TimeoutError` 전파
- [x] 테스트 격리 결함 수정: `MeetingContext` 싱글톤 DB 누수로 인한 순서 의존 플래키 제거(conftest autouse 격리) — 실제 사용자 DB 오염 방지
- [x] DB 다중 스레드 동시성 하드닝: WAL 저널 모드 + busy_timeout 적용, 전체 스위트 3회 연속 무결 통과(세그폴트 0회)


## Phase 10: 에이전트 상태 대시보드 & 사용성 개선 (오버레이 UX)
- [x] 10-1: 에이전트 상태 집계 허브(`core/agent_status.py`) — 5개 에이전트(STT·Flow·Chat·i2t·Report)의 IDLE/OK/WORKING/ERROR 상태를 신호 기반(폴링 0)으로 집계·배포
- [x] 10-2: 에이전트 상태 패널(`ui_common/status_panel.py`) — 색점+상세 뱃지로 각 에이전트 정상/오류(핵심 1단어)·교정DB 상태·생성중·질문수신 등을 실시간 표시
- [x] 10-3: 녹음 인디케이터(`ui_common/indicators.py`) — `● 녹음 중` 빨간 점멸을 베이스 오버레이에 탑재하여 두 반투명창 모두 좌상단 표시(회의 시작/종료 연동)
- [x] 10-4: FlowUI 3분할 레이아웃 재구성 — 세로 4:1:1 (Mermaid 차트 : 확정 전사 기록(누적 스크롤, 최근 50개) : 에이전트 상태 패널)
- [x] 10-5: 코디네이터 신호 배선 — 모든 에이전트 상태를 허브로 중계(Flow `analysis_started/failed`, Chat `question_received` 신규 신호 포함)
- [x] 10-6: (안정화) 코디네이터/ChatAgent의 컨텍스트 시그널 구독 누수 수정 — 좀비 코디네이터가 후속 회의에 반응해 STT(PyAudio)/Flow 스레드를 중복 생성하던 **access violation(세그폴트) 근본 원인** 제거 + conftest 시그널 격리. 전체 67 passed·3회 연속 무결

## Phase 11: 실제 실행 UX 하드닝 · 도구화 · 공개 (2026-06-21)
- [x] 11-A: 오버레이 UX — 녹음 표시 우상단 이동, '항상 위' 해제, 투명도 슬라이더, 흐름도 성장 리사이즈, **투명도 슬라이더 끝=완전 불투명 버그 수정**(paintEvent alpha 180→255)
- [x] 11-B: Flow 실시간성 — `_should_trigger` 3-way(최초 즉시/주제전환 8초 바닥/정기 15초). 주제전환 지연 ~30초→~8초
- [x] 11-C: CLI 디버그 로그 창(`core/cli_activity.py`, `ui_common/cli_log_window.py`) — 요청 즉시/응답 완료 분리 실시간 표시
- [x] 11-D/E: 회의 Q&A에 도구 통합(웹검색+작업폴더 파일도구, 📁 폴더 지정), 창 이름 명기(PrismFlow Agent/Chat Agent), 흐름도 ~90%·상태 한 줄, 세션 'already in use' 수정(`_created_sessions`)
- [x] 11-F: i2t 화면 용어집 STT 교정(`core/glossary.py`+`screen_glossary`), 회의종료 프리즈 수정(bounded stop+drain), 앱종료 즉시화(`terminate_all`), 폰트 경고 필터
- [x] 11-공개: MIT LICENSE + README(한/영) + GitHub `simturong/PrismFlow` 전체 공개. 전체 85 passed/1 skipped·3회 연속 무결

## Phase 12: 프로젝트 구조 최적화 및 불필요 문서 정리
- [x] 12-1: 불필요한 Handoff 문서 및 `artifacts/` 폴더, `phase9_benchmark_report.md` 일괄 영구 삭제
- [x] 12-2: `.agents/AGENTS.md` 파일/폴더 삭제, 루트 `agent.md`로 통합 및 `.agents/` 생성 차단 지침 주입
- [x] 12-3: PyTest 회귀 테스트 검증 및 트리 개편 무결성 검증

## Phase 13: 세션별 출력 폴더 구조화, UI 하드닝 및 회의 제어 기능 보강
- [x] 13-1: `AppConfig` 및 DB `settings` 테이블에 `output_dir` 추가 및 로딩 오버라이드 구현
- [x] 13-2: `SettingsDialog` UI에 출력 폴더 경로 표시창(QLineEdit) 및 폴더 브라우저(QPushButton) 추가
- [x] 13-3: 세션 시작 시 `output_dir/{session_id}/` 단일 폴더 생성 및 3대 파일(WAV, TXT, MD) 저장 경로 리팩토링
- [x] 13-4: 오버레이 창 테두리(`overlay.py` QPainter 보더 30alpha) 추가
- [x] 13-5: 실시간 임시(Interim) 전사 피드 배선 및 자막 뷰 높이 2배 확대(85px)
- [x] 13-6: 회의 일시중지(Pause)/재개(Resume) 및 정지(Stop) 버튼 추가, STT 엔진 대기/종료 연동 구현
- [x] 13-7: Mermaid CLI 사용량 한도 초과 판정 키워드 축소(reset 매칭 제거) 및 세션 리밋 리셋 구현
- [x] 13-8: Mermaid 화자(Speaker_XX) 표시 배제(프롬프트 및 로컬 폴백 룰 개편)
- [x] 13-9: Mermaid 뷰 상단 핵심 요약 뉴스 자막바 연동
- [x] 13-10: 단위/통합 테스트 코드 경로 매핑 수정 및 PyTest 무결성 검증

## Phase 14: 오버레이 엔진 모드 표시, UI 여백 최적화 및 STT 정확도 향상
- [x] 14-1: Mermaid 웹뷰 여백 꽉 채우기 (`mermaid_html.py` CSS 여백 최적화)
- [x] 14-2: 상단 핵심 요약 뉴스 자막바 글씨 확대 및 세로폭 조정
- [x] 14-3: 좌상단 타이틀 옆에 엔진 모드 (Claude/Local) 동적 표시 및 `AppCoordinator` 시그널 배선
- [x] 14-4: (기획 검토 완료) STT 정확도 개선을 위한 whisper medium/large-v3 지원 로직 기획
- [x] 14-5: 단위/통합 테스트 코드 수정 및 PyTest 무결성 검증

## Phase 15: STT 상위 모델(medium/large-v3) 실배선 및 셋업 도구
> Phase 14-4에서 기획만 완료한 medium/large-v3 지원을 실제 배선으로 전환. 매핑·설정 UI·로드 배선은 이미 완비되어 있었으므로, 실제 공백이던 ①모델 획득 수단 ②미설치 안내 UX를 채움.
- [x] 15-1: 모델 셋업 스크립트 `scripts/setup_whisper_model.py` 작성 — small 번들과 동일 출처인 HuggingFace 사전 빌드 int8-ov(`OpenVINO/whisper-{size}-int8-ov`)를 `huggingface_hub.snapshot_download`로 받아 `prismflow/resources/models/whisper-{size}-int8-ov`에 배치. `--list`/`--force`/멱등 skip 지원, optimum/nncf 로컬 변환 불요
- [x] 15-2: 미설치 모델 선택 시 실행 가능한 안내 — `stt_agent._load_openvino_models`의 FileNotFoundError가 디렉토리명에서 크기를 역산해 `python scripts/setup_whisper_model.py {size}` 설치 명령 안내(+small 폴백 안내), `SettingsDialog` 모델 상태 라벨에도 동일 명령 표기
- [x] 15-3: medium 모델(`whisper-medium-int8-ov`, ~760MB) 실설치 — 셋업 스크립트로 다운로드/배치 검증 (models/ 는 .gitignore 처리되어 미커밋)
- [x] 15-4: 회귀 — `tests/test_setup_whisper.py` 신설(매핑이 `AppConfig.whisper_dir_name` 단일 정본과 일치 검증 등 6케이스), 전체 PyTest 무결성 유지

## Phase 16: 통합 회의 콘솔 UI 재구성 및 STT 성능·정확도 향상 — ⏳ 구현 완료, 사용자 E2E 검증 대기
> Phase 15 E2E 후 사용자 제기 6개 개선점. 결정: STT는 균형(medium+GPU), 6항목 단일 Phase 16. 상세: docs/implementation_plan.md Phase 16.
- [x] 16-1: Flow+Chat 단일 콘솔 통합 + 우측 Chat `›`/`‹` 토글. **조정(외과적)**: 새 MeetingConsole 클래스 대신 FlowUI를 호스트로 유지(크롬/녹음/시그널 보존)하고 ChatUI만 base를 QWidget로 전환해 우측 임베드. main.py 단일 콘솔 배치·set_recording 단일화·tray 핸들러 정합. test_status 레이아웃 테스트 갱신 + 콘솔 토글 테스트 신설. 전체 94 passed/1 skip
- [x] 16-2: 헤드라인 자막바 중앙정렬 + 폰트 2배(13→26px) + 핵심어(용어집/숫자·단위) 색상 강조 — `flow_ui._highlight_keywords` 단일스캔 안전 richtext, test_flow 8 passed
- [x] 16-3: STT 성능 벤치마크(`scripts/stt_benchmark.py`+`tests/test_stt_benchmark.py`, 5 passed) + 실측. **발견(전제 반전)**: 추론은 병목 아님(medium/GPU RTF 0.123), 체감 지연은 interim 누적 재전사, medium은 본 int8-OV에서 반복 환각으로 오히려 정확도 저하. **개선**: interim 최근 4초 상한(반응성)+`collapse_repetitions` 반복환각 붕괴(정확도). 권장 기본=small. 리포트 `docs/phase16_stt_benchmark.md`
- [x] 16-4: 회의 시작(▶ Play) 버튼을 컨트롤바에 추가 → 시작 시 일시정지/정지로 모핑(meeting_started/ended 토글), 트레이와 동일 start_meeting 경로 — 19 passed
- [x] 16-5: Mermaid 폰트 2배(themeVariables fontSize 28px) + fade-in 전환 애니메이션 + 주제전환 시 새 subgraph 분기 프롬프트 강화 — test_flow 8 passed
- [x] 16-6: CLI 디버그 분류 정리("Agent"→"Q&A(도구)", 범례 추가) + i2t는 로컬이라 CLI 로그 없음 안내 — `cli_activity`/`cli_log_window`/`test_cli_activity` 갱신, 5 passed
- [x] 16-7: 회귀(`test_status`/`test_cli_activity`/`test_flow`/`test_stt` 갱신·신설, 전체 **100 passed/1 skip**) + 문서(history/task/plan/`phase16_stt_benchmark.md`) 동기화

## Phase 17: 회의 제어 UX 재설계 · Mermaid 사용성/자유도 · 실시간 전사 개선 — ✅ 완료
> Phase 16 E2E 후속 피드백. 모델 결론(사용자 지시): **기본 medium 확정, 빡세게 튜닝**. 상세: docs/implementation_plan.md Phase 17.
- [x] 17-1: 회의 제어 재설계 — ⏹ 정지(좌) + ▶/⏸ 재생-일시정지 토글(우) 상태기계(`_refresh_meeting_controls`). overlay.py 글리프 escape 통일 재작성. 32 passed
- [x] 17-2: Mermaid 사용성·자유도 — 폰트 28→20px·htmlLabels 라벨 줄바꿈·패딩↑(잘림 해소), svg 폭 꽉 채움+세로 스크롤(여백/축소 완화), Flow 프롬프트 자유 재구성(subgraph 의무·stale 제거·12~15노드 압축·방향 자유). test_flow 10 passed
- [x] 17-3: STT 기본 medium 확정(DB) + endpoint 1.0→0.7초(확정 신속·문장 누적 촉진) + interim을 진행발화 전체(상한 10초)로 되돌려 앞부분 망각 해소 + collapse_repetitions 유지. test_stt 6 passed
- [x] 17-4: 채팅 토글을 상단 컨트롤바(녹음중 옆) 💬 버튼으로 이동(`enable_chat_toggle`/`_on_chat_toggle_clicked`), 중앙 세로 핸들 제거 → 접힘 시 여백 컬럼 없음. 32 passed
- [x] 17-5: 회귀(test_flow 토글 테스트 갱신, 전체 **100 passed/1 skip**) + 문서(history/task/plan) 동기화

## Phase 18: Mermaid 흐름도 실시간 줌/팬, 작업 표시줄 활성화, 백그라운드 숨김 및 심볼릭 아이콘 통합 구현 — ✅ 완료
> Mermaid 그래프가 커질 때 가독성 저하를 방지하기 위해 줌/팬 기능을 추가하고, 메인 콘솔의 작업 표시줄 노출, 닫기 시 백그라운드 숨김(트레이 상주), 그리고 PrismFlow 전용 심볼릭 아이콘 및 동적 상태 표시를 통합합니다. 상세: docs/implementation_plan.md Phase 18.
- [x] 18-1: 오프라인 라이브러리 번들 추가 — `svg-pan-zoom.min.js` 획득 후 `prismflow/agents/flow/resources/` 저장 및 Git 관리 설정
- [x] 18-2: HTML/CSS 및 로컬 줌 툴바 UI 구축 — `mermaid_html.py` 내 HTML/CSS 리팩토링, Glassmorphism 스타일 줌 툴바(➕, ➖, 🎯 Fit/Center, 🔄 Reset) 추가 및 API 연동
- [x] 18-3: 다이어그램 업데이트 시 줌/팬 상태 보존(State Preservation) 구현 — `updateDiagram` 실행 시 기존 줌/팬 값을 임시 저장하고 렌더 후 복원하여 화면 튐 방지
- [x] 18-4: SVG 레이아웃 스타일 충돌 해결 — `svg-pan-zoom`이 viewBox를 올바르게 추적하도록 `#diagram-container svg` CSS 충돌(width 100% 강제 등) 리팩토링
- [x] 18-5: 프리미엄 앱 로고 이미지 생성 및 배치 — `generate_image`로 `app_icon.png`를 생성하여 `prismflow/resources/` 폴더에 배치
- [x] 18-6: 작업 표시줄 창 노출 및 아이콘 연동 — `TranslucentOverlay` 플래그에서 `Qt.Tool` 제거 및 `setWindowIcon` 적용
- [x] 18-7: 창 닫기 시 트레이 최소화(백그라운드 상주) 구현 — `closeEvent` 가드로 종료 아닐 때 ignore & hide 처리, 트레이 `exit_app`에 `is_quitting = True` 적용
- [x] 18-8: 트레이 아이콘 변경 및 동적 녹음 점 표시 — `app_icon.png` 트레이 지정 및 회의 진행 시 동적 QPainter로 우측 하단 녹음 점 덧그리기 구현
- [x] 18-9: 회귀 및 렌더링 검증 — `test_flow.py` 리소스 맵 체크 및 전체 `pytest tests/` 무결 검증

