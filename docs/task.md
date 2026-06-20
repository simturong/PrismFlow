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
- [ ] 6-0-A: `claude` CLI로 모델명 3종 실검증 (Chat/Flow `claude-3-5-haiku`, Report `claude-opus-4-8`) — 거부 시 유효 별칭 교체 및 코드/테스트 동기화
- [ ] 6-0-B: `run.bat` E2E 1회 구동 (회의 시작→Mock 발화→Flow 표출→Chat Q&A→종료→보고서 팝업) 육안 확인 + 종료 크래시 수정 검증

### Phase 6-1: 실제 STT/화자분리 엔진 구현
- [ ] `stt_agent.py` `_load_openvino_models()` 실구현 (HW 자동감지 CUDA→OpenVINO/NPU→CPU 폴백, Whisper+pyannote 로드, 로컬 가중치 우선)
- [ ] `stt_agent.py` `_process_inference()` 실구현 (5.0s 윈도우/0.5s 시프트, ko 강제, word_timestamps, diarization 규격) — 스텁 대체
- [ ] `audio.py` 실제 마이크 캡처(16kHz/Mono/Float32) 동작 검증
- [ ] `prismflow/resources/models/` 가중치 로컬 번들 배치 (pyannote 게이트 처리 또는 비게이트 대안 결정)
- [ ] `requirements.txt`에 STT 의존성 추가 (openvino/openvino-genai, pyaudio·sounddevice, pyannote.audio/onnxruntime)

### Phase 6-2: 실시간 안정화 및 예외 차단
- [ ] 노이즈/무음 처리 + `config.vad_threshold` 연동
- [ ] 버퍼 병목·타임라인 드리프트·백프레셔 제어
- [ ] 하드웨어 가속 강제 제어 시 오류 → 안전 폴백
- [ ] `stt_mock_mode=False` 실측: 실제 한국어 발화 → 전사·화자분리 정확도 육안 검증
- [ ] `tests/test_stt.py` 확장 (HW감지/추론 인터페이스 단위 테스트, 실엔진 옵트인 마커 분리) + 전체 회귀 통과
