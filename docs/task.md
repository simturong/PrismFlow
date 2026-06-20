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
- [ ] 6-3-1 설정 UI ↔ 실엔진 배선: `AppConfig` DB 오버라이드를 STT 설정(stt_mock_mode/whisper_model_name/stt_device/vad_threshold)까지 확장 + `SettingsDialog`에 Mock 토글·HF 토큰 필드 추가, 가속 옵션 실디바이스 정합, 모델크기↔OV 디렉토리 매핑
- [ ] 6-3-2 앱 통합 실측(에이전트): `stt_mock_mode=False`로 run.bat 풀 구동 — 실음성→전사→Flow→Chat→종료→보고서 육안 검증 + 버그 즉시 수정
- [ ] 6-3-3 멀티 화자 전역 일관성: 발화 임베딩 점증 클러스터링/코사인 매칭으로 전역 Speaker_XX 라벨 일관성 확보
- [ ] 6-3-4 첫 실행 UX·에러 하드닝: 모델 미존재 안내/다운로드 상태, STT 실패 UI 토스트+Mock 폴백, 토큰 부재 안내
- [ ] 6-3-5 이중 검증·개선 루프: 사용자 실회의(다인) 테스트 → 정확도/화자/지연/사용성 피드백 반영, vad/모델 튜닝
- [ ] 6-3-6 정리·회귀: 설정 오버라이드/매핑 단위테스트 추가, 전체 회귀 유지, stt_live_test 정리·Pretendard 폰트 잔여 처리

## Phase 7: 오프라인 원클릭 패키징 및 배포 (6-3 완료 후 착수)
- [ ] (6-3 이중 검증 통과 전 착수 금지) Embeddable Python + 모델 번들 + Inno Setup 통합 인스톨러
