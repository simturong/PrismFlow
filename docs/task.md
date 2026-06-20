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

## Phase 5: Docs Agent 문서 작성 및 전체 파이프라인 마무리
- [ ] `prismflow/agents/docs/docs_agent.py` 최종 요약 Markdown 회의록 작성 모듈 구현
- [ ] 요약 Markdown 문서 자동 저장(문서/PrismFlow/일자별폴더) 및 Windows 기본 연결 프로그램 연동
- [ ] `run.bat` 원클릭 실행 스크립트 작성
- [ ] 전체 연동 수동 시뮬레이션 및 최종 성능 최적화
