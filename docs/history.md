# PrismFlow Development Wiki & History

이 문서는 PrismFlow 개발 여정의 모든 과정, 주요 의사결정 브랜치, 발생한 블로커(Blocker) 및 시행착오(Trial & Error)를 스토리텔링 형식으로 낱낱이 기록하는 구조화된 프로젝트 역사서(Wiki)입니다. 

매 개발 단계(Phase)가 완료될 때마다 반드시 업데이트됩니다.

---

## 📖 개발 타임라인 및 마일스톤

| 단계 | 상태 | 완료일 | 주요 다룬 내용 |
| :--- | :--- | :--- | :--- |
| **기획 및 아키텍처 수립** | ✅ 완료 | 2026-06-20 | 요구사항 분석, 에이전트 설계, 수직 슬라이스 트리 구성, 개발 지침 확정 |
| **Phase 1: 트레이 및 GUI 스캐폴딩** | ✅ 완료 | 2026-06-20 | 트레이 메뉴 구성 및 투명 오버레이 윈도우(페이드/드래그) 빌드 |
| **Phase 2: SQLite DB & STT 가동** | ✅ 완료 | 2026-06-20 | 데이터베이스 CRUD 작성 및 실시간 STT Mock 에뮬레이터 검증 |
| **Phase 3: Flow & Mermaid 연동** | ✅ 완료 | 2026-06-20 | Claude CLI 비차단 파이프 연결 및 Mermaid 렌더링 검증 |
| **Phase 4: Chat RAG & 질문 통합** | ✅ 완료 | 2026-06-20 | 최근 대화 context 주입 RAG 구현 및 비동기 스트리밍 연결 |
| **Phase 4-3: 설정 및 화면로그 고도화** | ✅ 완료 | 2026-06-20 | 설정 GUI 다이얼로그, 화면 DB 적재, CLI 경로 오버라이드 및 폰트 로드 |
| **Phase 5: Report Agent & 파이프라인 마무리** | ✅ 완료 | 2026-06-20 | Opus 4.8 최종 회의록 자동 생성/저장/실행, ReportAgent 명명 확정, run.bat 런처 |
| **Phase 6-3: 완성도 확보 및 하드닝** | ✅ 완료 | 2026-06-20 | 콜드스타트 블라인드 윈도우 제거, 실시간 전사 가시성(자막), 멀티화자 전역 일관성, QFont 경고 제거 |
| **Phase 7: 오프라인 포터블 배포 패키징** | ✅ 완료 | 2026-06-20 | `build_release.py` 포터블 빌더, Inno Setup 인스톨러(`setup.iss`), 오프라인 토큰리스 화자분리 로더 |
| **Phase 9: 성능 50%+ 최적화 & 상용화 안정화** | ✅ 완료 | 2026-06-21 | STT 핫패스 추론 절반, Flow 슬라이딩 윈도우(토큰 75%↓), Chat 백그라운드 주입 폐지, 벤치마크 회귀 차단, 세그폴트 근본 해결 |
| **Phase 10: 에이전트 상태 대시보드 & 오버레이 UX** | ✅ 완료 | 2026-06-21 | 신호 기반 5-에이전트 상태 허브/뱃지, 녹음 인디케이터, FlowUI 4:1:1 분할 |
| **Phase 11: 실제 실행 UX 하드닝 & 도구화 & 공개** | ✅ 완료 | 2026-06-21 | 오버레이 UX 정비, Flow 실시간성, CLI 디버그 창, 회의 Q&A 도구 통합, 화면 용어집 STT 교정, 프리즈/종료 수정, GitHub 공개 |
| **Phase 12: 구조 최적화 및 문서 정리** | ✅ 완료 | 2026-06-21 | 불필요 Handoff 및 artifacts 정리, 지침 문서 agent.md 일원화 및 단일 정본 통제 확보 |
| **Phase 13: 출력 구조화 및 제어 보강** | ✅ 완료 | 2026-06-21 | 세션별 output 디렉토리 격리, 3대 파일(WAV/TXT/MD) 통합 저장, 자막창 2배 확대 및 실시간 Interim, 일시중지/재개/정지 제어 |
| **Phase 14: 모드 표시 및 여백 최적화** | ✅ 완료 | 2026-06-21 | Mermaid 뷰 100% 꽉 채우기, 뉴스 자막바 확대(30px), 타이틀 옆 엔진 모드(Claude/Local) 동적 표시 배선, STT 고품질 기획 검토 |

---

## 🚀 기획 및 아키텍처 수립 단계 (2026-06-20)

### 1. 초기 컨셉 및 요구사항 분석
- **목적**: Windows 시스템 트레이에 상주하며, 로컬 STT와 로컬 Claude CLI(서브프로세스 파이프라인)를 사용하여 클라우드 연결 없이 동작하는 오프라인 회의 어시스턴트 개발.
- **주요 도메인**: 
  - **STT Agent**: 시간/화자/발화 데이터 누적 및 보정.
  - **Flow Agent**: 30초 단위 Mermaid.js 흐름도 투명 오버레이 표출 (Haiku 모델).
  - **Chat Agent**: 누적 대화 + 흐름 맥락 RAG 기반 실시간 응답 투명 오버레이 (Haiku 모델).
  - **Report Agent** (구 Docs/Synthesizer Agent): 회의 종료 시 Opus 4.8 모델로 구조화된 회의록 Markdown 저장 및 자동 실행.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: 시각화 엔진 선정 (Mermaid.js vs QGraphicsView)
- **논쟁**: 
  - `QGraphicsView`는 순수 파이썬/Qt 네이티브라 가볍지만, 동적 노드 배치와 간선 연결 알고리즘을 직접 코드로 수백 줄씩 짜야 하여 투박해지기 쉬움.
  - `Mermaid.js` + `QWebEngineView`는 웹 렌더러를 로드하므로 리소스 점유율이 올라가지만, CSS 스타일링(반투명 Glassmorphism 등)과 레이아웃 배치 최적화가 자동 구현되어 첫인상(Visual Wow)이 압도적임.
- **결정**: 비주얼 퀄리티와 빠른 오프라인 레이아웃 구현을 위해 **Mermaid.js CDN 파일을 프로젝트 내부 리소스 폴더에 번들링하여 로컬 로드**하는 방식으로 결정.

#### 🔍 이슈 2: Claude CLI 다중 세션 제어 방식
- **논쟁**: 단일 Claude CLI 프로세스 파이프를 열고 Flow와 Chat이 멀티스레드로 공유하게 할 것인가, 세션을 분리할 것인가?
  - 단일 세션 공유 시 한 에이전트의 답변을 받아오는 동안 다른 에이전트의 입출력 버퍼가 꼬여 데드락이 날 위험이 큼.
- **결정**: **Flow와 Chat의 Claude CLI 세션을 분리**하여 스레드 충돌을 원천 방지함. 대신 Chat 에이전트가 호출될 때, `MeetingContext`에서 최근 발화 이력과 Flow 에이전트가 만든 다이어그램 코드를 RAG 형태로 결합하여 Chat용 CLI 세션의 입력 버퍼에 매번 갱신하여 주입해 주는 방식으로 컨텍스트 단절을 보완함.

#### 🔍 이슈 3: AI 협업 최적화 폴더 구조화 (가장 큰 시행착오)
- **상황**: 초기에는 전통적인 레이어드 아키텍처(`ui/`, `agents/`, `utils/`)를 구성하였으나, AI가 코딩할 때 컨텍스트 탐색 범위가 지나치게 넓어져 토큰 낭비 및 잘못된 참조가 생길 여지가 컸음. 또한 DB 테이블 구성 및 테스트 자동화 영역이 누락되었었음.
- **피드백**: 사용자가 AI 바이브 코딩 및 ReAct(생각-실행-검증) 원칙에 부합하도록 테스트 환경을 추가하고, `features` 대신 `agents`라는 직관적인 네이밍의 수직 슬라이스 구조(Vertical Slice Architecture)를 설계할 것을 강하게 요구함.
- **결정**: 
  - `prismflow/agents/stt/`, `prismflow/agents/flow/` 등 기능 단위로 UI와 스레드 코드를 완전히 격리하고 독자적인 파일 내비게이션 파일인 `agent.md`를 최상위에 배치.
  - AI가 코드를 작성하자마자 바로 `pytest`를 활용해 "생각 - 실행 - 검증"을 자가 수행하도록 `tests/` 폴더 산하에 각 모듈별 독립 검증 코드를 맵핑함.
  - 데이터 영구 보관용 SQLite 관리 파일(`core/db.py`)을 아키텍처에 추가 명시함.
  - 개발 중 시행착오 스토리를 낱낱이 기록하고 위키처럼 작동하는 본 역사서(`docs/history.md`) 규칙을 신설함.

---

## 🚀 Phase 1: 시스템 트레이 및 투명 오버레이 기본 GUI 구축 (2026-06-20)

### 1. 주요 구현 내용
- `AppConfig`: 데이터베이스 경로, 오디오 설정 등을 독립적으로 유지할 수 있는 환경설정 클래스 구현.
- `MeetingContext` 싱글톤: 여러 스레드(STT, Flow 등)의 동시 발화 및 상태 전이에 대응하는 `threading.Lock` 기반 스레드 세이프 구조 구현. Qt 신호(`Signal`)를 내장하여 상태 변화 시 UI 스레드와 즉각적인 이벤트 기반 통신 연동.
- `TranslucentOverlay` & `DemoOverlay`: 프레임리스, 투명 배경, 항상 위 설정을 적용하고 마우스 드래그 동작 및 마우스 진입/이탈 시 불투명도를 제어하는 `QPropertyAnimation` 애니메이션 적용.
- `SystemTrayManager`: 트레이 아이콘을 통해 회의 시작/종료 메뉴 활성화 상태를 `MeetingContext` 신호와 실시간 연동.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: PySide6 테스트 가동 시 QApplication 리소스 초기화 에러
- **상황**: `MeetingContext`가 신호 전달을 위해 `QObject` 기반의 `MeetingSignals` 객체를 생성하면서, `QApplication` 인스턴스가 존재하지 않을 때 pytest 단독 실행 단계에서 런타임 크래시가 유발됨.
- **결정**: `tests/conftest.py`에 세션 단위 공유 피스처인 `q_app`을 정의하여, PyTest 세션 수명 주기 동안 단 하나의 `QApplication` 인스턴스만 유지되도록 설정함으로써 테스트의 안정성을 보장함.

#### 🔍 이슈 2: pytest 로드 경로 탐색 실패 (`ModuleNotFoundError`)
- **상황**: `pytest tests/test_core.py` 직접 호출 시 작업 디렉토리가 파이썬 임포트 경로에 누락되어 `prismflow` 모듈을 로드하지 못하는 오류가 발생함.
- **결정**: Windows 환경에서 현재 디렉토리를 임포트 패스로 주입할 수 있도록 `.venv\Scripts\python -m pytest tests/test_core.py` 형태로 우회 기동하여 의존성 임포트 버그를 극복함.

#### 🔍 이슈 3: 완전 투명 오버레이 윈도우 시인성 부족
- 상황: GUI 기동 시 백그라운드가 완전히 투명하게 설정될 경우, 내부에 레이블이 있어도 오버레이 영역의 경계를 마우스 드래그로 탐색하기가 매우 어려움.
- 결정: `paintEvent`를 오버라이딩하여 RGBA(30, 30, 30, 180)의 반투명 둥근 사각형을 그리도록 개선하여, 심미적인 Glassmorphism 효과와 GUI 가시성을 동시에 만족시킴.

---

## 🚀 Phase 2: SQLite DB 구축 및 실시간 STT 에뮬레이터 설계 (2026-06-20)

### 1. 주요 구현 내용
- `prismflow/core/db.py`: SQLite 연동을 위한 데이터베이스 매니저 작성. 회의 세션, 전사 발화문, 채팅 기록, 전역 설정 관리 테이블 스키마 자동 구축 및 CRUD 쿼리 추상화.
- `prismflow/core/context.py` 확장: 발화 이벤트(`add_transcript`) 발생 시 `DatabaseManager`를 경유해 실시간으로 SQLite에 적재 및 트랙 보존 구현.
- `stt_agent.py`: `QThread` 기반 워커 스레드로, 15~20초 주기로 다자 가상 대화 데이터(시작 시간, 화자, 텍스트)를 번갈아 주입하는 Mock Mode 가동 에뮬레이터 설계 및 실제 마이크 입력용 `AudioRecorder` WASAPI 캡처 파이프라인 연계.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: SQLite 다중 스레드 동시 접속 충돌 (`sqlite3.ProgrammingError`)
- **상황**: PySide6 GUI 메인 스레드, STT 스레드, Flow 스레드가 공유 리소스인 `MeetingContext` 싱글톤을 거쳐 SQLite 데이터베이스 파일에 동시에 쓰기 및 읽기를 시도함. 이때 SQLite3 모듈이 기본적으로 연결을 생성한 스레드 외의 타 스레드 접근을 차단하여 스레드 충돌 예외를 발생시킴.
- **결정**: `sqlite3.connect` 연결 시 `check_same_thread=False` 옵션을 인위적으로 가해 스레드 간 연결 개방을 조율함. 동시에 동시 쓰기(Write Race Condition)로 인한 DB Lock 데드락을 원천 제어하기 위해, 모든 CRUD 동작을 `MeetingContext` 싱글톤 내의 `threading.Lock` 임계 영역 안으로 강제 묶어 스레드 세이프하게 정렬함.

#### 🔍 이슈 2: 오디오 디바이스 없는 테스트 환경의 검증성 보장 (Mock Mode)
- **상황**: 로컬 개발 및 테스트 자동화 환경(CI 혹은 마이크가 없는 빌드 머신)에서 실제 오디오를 캡처하면 포트 점유 실패나 기기 없음 에러가 유발되어, STT 엔진 스레드의 정상 작동 여부를 pytest 수준에서 확인하기가 불가능했음.
- **결정**: STT 에이전트 내부에 `stt_mock_mode` 설정을 내장하여, True일 경우 가상의 한국어 회의 발화 시나리오 큐를 사용해 15~20초 간격으로 신호를 정밀 방출하도록 에뮬레이트함. 이로써 외부 하드웨어 없이도 상위 파이프라인(Flow, Chat 등) 전체가 연속 테스트될 수 있는 Mock 검증 체계를 확보함.

---

## 🚀 Phase 3: Claude CLI 통신 및 Flow Agent Mermaid 시각화 (2026-06-20)

### 1. 주요 구현 내용
- `ClaudeCLIController`: `-p` (print) 모드를 활용하여 동기식으로 단발성 실행을 유도하고, 에이전트의 QThread 내에서 이를 비동기 실행하여 메인 스레드 블로킹을 막는 CLI 래퍼 개발.
- `ScreenTransitionDetector`: `win32com.client`를 통한 PPT 활성 슬라이드(`SlideIndex`) 추적 및 `Pillow` 32x32 픽셀 MSE 변화율 분석을 통한 범용 감지 Fallback 체인 구현. 30초 디바운싱 정착(Settled)과 MSE/인덱스 기반 중복 방지(Deduplication) 로직 탑재.
- `FlowUI` & `mermaid_html.py`: QWebEngineView 투명 오버레이를 통해 깜빡임 없는 리렌더링(`runJavaScript` 및 Base64 인코딩 전달)을 구현하고 오프라인 동작용 `mermaid.min.js` 번들링 탑재.
- `FlowAgent`: 30초 주기로 발화를 분석해 Mermaid 코드를 갱신하며, 시각 지시어 감지 시 화면 맥락을 결합해 Stateful(Upsert) 다이어그램을 빌드하는 지능형 스레드 루프 구현.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: 대화형 Popen 상주 세션의 한계와 `--resume` 재시도 폴백 도입
- **상황**: 설계대로 로컬 `claude` CLI를 대화형 `subprocess.Popen` 상주 프로세스로 띄워 연속 대화를 시도하려 했으나, Windows 환경 특유의 입출력 버퍼링으로 인해 응답 대기 중 먹통이 되거나(데드락), Node.js CLI 단에서 TTY가 아님을 감지하고 입력을 거부하는 불안정성이 노출됨. 또한 `--session-id` 옵션 연속 호출 시 "already in use" 에러가 발생함.
- **결정**: 단발성 `-p` (print) 모드를 사용하여 매번 프로세스를 띄우되, TTY 대기를 스킵하기 위해 `stdin`을 `DEVNULL`로 리다이렉션함. 그리고 **`--resume <UUID>` 호출을 먼저 시도하여 기존 세션을 복원하고, 세션이 존재하지 않아 에러(No conversation found)가 날 경우 자동으로 `--session-id <UUID>`로 폴백(Fallback)해 세션을 생성하는 '재시도 폴백' 방식**을 구현하여 데드락 0% 및 완벽한 세션 유지를 성취함.

#### 🔍 이슈 2: HTML/CSS/JS 템플릿의 파이썬 f-string 이스케이프 지옥
- **상황**: `mermaid_html.py`에서 웹뷰에 실어 보낼 HTML/CSS/JS 소스코드를 파이썬 f-string으로 작성하자, 중괄호가 넘쳐나는 CSS 스타일 및 자바스크립트 블록에서 단일 중괄호와 이중 중괄호(`{{`, `}}`) 짝이 맞지 않아 f-string 파서가 `SyntaxError: f-string: single '}' is not allowed` 컴파일 에러를 수시로 뿜어내고 소스코드 가독성이 극도로 훼손됨.
- **결정**: f-string 접두사 `f`를 과감히 떼어내어 일반 트리플 쿼트 `"""` 문자열로 변경하고, CSS와 JS 내부의 모든 이중 중괄호를 표준 단일 중괄호로 환원하여 네이티브 가독성을 지킴. 라이브러리 참조 경로는 `__MERMAID_JS_URL__` 이라는 단순 플레이스홀더를 심어둔 뒤, `.replace()` 메소드로 문자열 치환하여 주입함으로써 구문 해석 에러를 원천 차단함.

#### 🔍 이슈 3: 슬라이드 전환 및 픽셀 변화 감지의 리소스 폭주와 디바운싱
- **상황**: 화면 전환을 1초 주기로 실시간 캡처해 OCR이나 AI 전사로 처리하면 리소스 사용량이 폭주하고, 사용자가 슬라이드를 빠르게 스킵하며 넘어갈 때 불필요한 연쇄 캡처 이벤트가 발생하는 낭비가 초래됨.
- **결정**: 화면 변화가 감지되는 즉시 이벤트를 쏘지 않고, `QTimer` 기반의 **30초 디바운싱 타이머**를 가동하여 추가 변화가 없이 완전히 고정(Settled)되었을 때만 최종 화면으로 확정되게 필터링함. 또한 범용 캡처본을 **32x32 초소형 크기**로 줄여 픽셀 MSE(Mean Squared Error) 연산을 적용함으로써 CPU 점유율을 1% 미만으로 극한까지 최적화함.

---

## 🚀 Phase 4: Chat RAG & 질문 통합 (2026-06-20)

### 1. 주요 구현 내용
- `ChatAgent`: 백그라운드 3분 주기의 신규 대화 자동 주입(Context Ingestion) 루프와 Q&A 스레드를 탑재한 비동기 에이전트 개발. 질문 시점에는 최근 주입 완료 시점 이후의 미주입된 잔여 발화만 질문에 병합해 넘김으로써 CLI 토큰 소모를 극적으로 절감하고 응답 시간을 단축함.
- `ChatUI`: `TranslucentOverlay`를 상속하고 QSS Glassmorphism을 적용한 420x580 고정 크기의 우측 하단 상주형 대화 팝업 GUI 개발. 자체 정규식 기반의 Markdown-to-HTML 렌더러와 펄스 효과 답변 대기 로딩 마이크로 애니메이션 연동.
- `cli_controller.py` 확장: 실시간 스트리밍 출력을 줄 단위로 비차단 획득하기 위한 `execute_command_stream` generator 메서드 추가.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: 최상위 윈도우 투명도 속성 전파와 QSS 둥근 모서리 렌더링 깨짐
- **상황**: 최상위 `QWidget`에 직접 스타일시트로 `border-radius: 14px;`과 반투명 배경을 입히면, Windows OS의 창 마스크 렌더링 한계로 인해 모서리 주변에 검은색 잔상이 끼거나 스타일시트 테두리가 둥글게 깎이지 않는 현상이 관측됨.
- **결정**: `TranslucentOverlay`에서 직접 백그라운드를 그리던 `paintEvent` 기본 동작을 비우고, 내부에 여백 0의 레이아웃을 통해 QFrame `chat-container`를 배치함. 이 프레임 위젯에만 QSS 스타일시트를 적용하여 배경과 실버 그라데이션 보더를 렌더링함으로써 투명 둥근 모서리를 정밀하고 노이즈 없이 표현하는 데 성공함.

#### 🔍 이슈 2: 비가시 상태 위젯의 `isVisible()` 리턴값 오류로 인한 테스트 실패
- **상황**: UI 통합 테스트인 `test_chat_ui_integration` 실행 도중, 질문을 전송한 뒤 `assert ui.loading_label.isVisible() is True` 검사에서 가시성이 확보되었음에도 `False`로 인식되며 실패함.
- **원인**: Qt 프레임워크 명세 상 부모 창이 완전히 `show()` 되지 않은 상태라면, 자식 컴포넌트가 개념적으로 보이기 설정되어 있어도 화면 상에 물리적으로는 그려지지 않았으므로 `isVisible()`이 `False`를 리턴함.
- **결정**: 테스트 쿼리 전송 전에 `ui.show()`를 먼저 명시적으로 호출해 주어 윈도우 가시 상태를 활성화함으로써, 자식 컴포넌트의 가시성 상태가 정상적으로 검출되도록 수정해 테스트를 통과시킴.

#### 🔍 이슈 3: 최초 세션 기동 시 레이스 컨디션 방지를 위한 `session_initialized` 시그널 도입
- **상황**: 회의가 켜지자마자 `ChatAgent`는 Claude CLI 세션을 최초 생성하기 위해 비동기 찔러넣기를 시도하는데, 그 초기화가 채 완료되기 전에 사용자가 질문 입력 후 Enter를 누를 경우, 세션 미설정 및 CLI 호출 동시성 충돌로 비차단 통신 파이프라인 에러가 초래됨.
- **결정**: 에이전트 생성자에 `session_initialized` 시그널을 추가하고, `ChatUI` 시작 시에는 입력 필드를 비활성화 및 안내 문구("세션 초기화 중...")로 잠가 두었다가 세션 준비 완료 신호를 받는 즉시 입력창을 동적으로 개방하도록 설계해 인터랙션 충돌을 방지함.

---

## 🚀 Phase 4-3: 추가 최적화 및 설정/환경 고도화 (2026-06-20)

### 1. 주요 구현 내용
- `screen_logs` 마이그레이션 및 적재: SQLite 데이터베이스에 `screen_logs` 테이블을 신설하여, 감지된 화면 전환 정보(PPT의 `"파일명|페이지번호"`, GENERIC의 32x32 픽셀 데이터 콤마 스트링)를 실시간 영구 적재하는 `add_screen_log` 및 `get_screen_logs` CRUD를 구현하고 `MeetingContext`와 자동 연동함.
- `SettingsDialog`: Whisper 모델 크기, 하드웨어 가속, VAD 임계값, Claude CLI 오버라이드 경로를 통합 제어하고 DB에 영구 upsert하는 QDialog 기반 Glassmorphism 설정 GUI 빌드 및 트레이 "설정" 메뉴 연동.
- Claude CLI 경로 동적 오버라이드: 프로그램 기동(`AppConfig.__post_init__`) 시 sqlite3를 통해 settings의 `claude_cli_cmd`를 우선 조회하고 오버라이드하여, 순환 참조 없이 동적 경로 오프라인 실행을 완비.
- 로컬 Pretendard 폰트 로드: `main.py` 시작 시 Pretendard ttf 파일의 로컬 동적 등록(`QFontDatabase.addApplicationFont`)을 연동해 오프라인 룩앤필 일관성을 확보함.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: SQLite 외래키 제약조건 정의 오류로 인한 스키마 크래시
- **상황**: `screen_logs` 테이블 생성 시 `REFERENCES meeting_sessions.session_id` 형태로 마침표를 사용하여 외래키를 지정하자, SQLite3 엔진이 `OperationalError: near ".": syntax error` 문법 오류를 일으키며 6개 DB 단위 테스트 전체가 셋업 단계에서 폭사함.
- **결정**: 표준적인 SQLite REFERENCES 문법 규격에 맞게 소괄호 형식인 `REFERENCES meeting_sessions(session_id)`로 신속하게 교정하여 스키마 생성을 정상화함.

#### 🔍 이슈 2: Config 초기화 시 DB 매니저 참조에 따른 순환 참조(Circular Dependency) 예외
- **상황**: `AppConfig` 로딩 시점에 DB 내 `claude_cli_cmd` 오버라이드 값을 불러오기 위해 `DatabaseManager` 모듈을 임포트 및 인스턴스화하려 하자, `DatabaseManager` 역시 `AppConfig`를 사용하므로 악명 높은 파이썬 순환 참조 런타임 예외가 발생함.
- **결정**: `AppConfig.__post_init__`에서 상위 `db.py` 라이브러리를 임포트하지 않고, 내부에서 직접 순수 `sqlite3.connect`를 단발성 기동하여 settings 테이블의 존재 여부 및 키-값 데이터를 초경량으로 직접 조회 및 주입하도록 아키텍처를 우회 설계해 순환 참조를 타파함.

---

## 🚀 Phase 5: Report Agent 및 전체 파이프라인 마무리 (2026-06-20)

### 1. 주요 구현 내용
- `ReportAgent` (QObject): `MeetingContext`의 `signals.meeting_ended`를 독립 구독하여, 회의가 끝나는 즉시 최종 회의록 컴파일을 자동 트리거하는 경량 오케스트레이터. 메인 스레드 시점에 `current_mermaid_code`를 선(先)캡처해 워커로 넘김으로써 `context.reset()`과의 레이스 컨디션을 차단함.
- `ReportWorker` (QThread): 백그라운드에서 ① SQLite 발화록·채팅로그·세션 메타데이터 수집 → ② 최종 Mermaid 흐름도와 융합한 Opus 프롬프트 구성 → ③ `claude-opus-4-8` 단발 호출(타임아웃 120초) → ④ `Documents/PrismFlow/Reports/YYYY-MM-DD/report_{session_id}.md` UTF-8 저장 → ⑤ `meeting_sessions.summary` DB 영구 적재 → ⑥ `os.startfile` 자동 실행까지 한 호흡으로 수행.
- `main.py` `AppCoordinator`: `ReportAgent`를 생성·연동하고 `report_generated`/`error_occurred` 시그널을 로깅에 연결했으며, 앱 종료 시 `cleanup()`에서 워커를 안전 대기 종료하도록 등록.
- `run.bat`: `.venv` 활성화 후 `python main.py`를 원클릭 기동하고, 가상환경 부재 및 비정상 종료 시 `pause`로 콘솔을 잡아두는 Windows 통합 런처 작성.
- `tests/test_report.py`: 프롬프트 병합·CLI 인자(모델/타임아웃)·날짜별 폴더 UTF-8 저장·DB summary 갱신·`os.startfile` 호출·빈 응답 예외·`meeting_ended` 배선까지 5개 케이스로 엄격 검증. 전체 회귀 `pytest tests/ -v` 결과 **36 passed**.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: 추상적 명칭 `SynthesizerAgent`의 직관성 부족 → `ReportAgent`로 일괄 리네이밍
- **상황**: 직전 세션에서 `DocsAgent`를 `SynthesizerAgent`로 개명했으나, "Synthesizer"가 실제 산출물(회의 보고서)을 직관적으로 드러내지 못해 코드 탐색·온보딩 시 인지 비용이 높다는 피드백이 제기됨.
- **결정**: 산출물 자체를 가리키는 **`ReportAgent`/`ReportWorker`** 로 클래스명을 확정하고, 폴더(`agents/docs/` → `agents/report/`), 파일(`docs_agent.py` → `report_agent.py`), 테스트(`test_docs.py` → `test_report.py`)까지 트리 구조 전반과 `implementation_plan.md`·`task.md`·`history.md` 문서를 일괄 동기화함. 빈 껍데기로 남아 있던 `agents/docs/` 폴더는 깨끗이 제거함.

#### 🔍 이슈 2: 보고서 모델을 구형 `claude-3-opus-20240229`에서 최신 Opus 4.8로 격상
- **상황**: 최초 계획서는 회의록 생성 모델로 구형 별칭 `claude-3-opus-20240229`를 명시하고 있었으나, 최종 보고서는 회의 전체 맥락을 종합·구조화하는 가장 무거운 추론 작업이므로 품질을 최우선해야 함.
- **결정**: 사용자 지시에 따라 추론 품질이 가장 높은 **`claude-opus-4-8`** 로 교체함. (Flow/Chat은 응답성이 중요해 Haiku 유지, Report만 Opus 4.8로 차등 적용하는 모델 분리 전략을 확정.)

#### 🔍 이슈 3: `os.startfile` 자동 실행의 크로스 플랫폼 테스트 안전성
- **상황**: 보고서 자동 팝업을 위한 `os.startfile`은 Windows 전용 API라, 타 플랫폼이나 CI에서 단위 테스트를 돌릴 때 `AttributeError`로 파이프라인 전체가 폭사할 위험이 있음.
- **결정**: 실행부에 `sys.platform == 'win32' and hasattr(os, 'startfile')` 이중 가드를 씌우고, 테스트에서는 `patch(..., create=True)`로 속성을 안전 모킹하되 호출 단언은 win32에서만 수행하도록 분기함. 또한 `startfile` 실패 자체도 `try/except`로 흡수해, 뷰어 연동 오류가 보고서 생성 성공 자체를 무효화하지 않도록 분리함.

#### 🔍 이슈 4: 회의 종료 시각(end_time) 이중 기록으로 인한 덮어쓰기 방지
- **상황**: `MeetingContext.end_meeting()`이 이미 `end_session(session_id, end_time=...)`로 종료 시각을 기록한 뒤 `meeting_ended` 신호를 쏘는데, `ReportWorker`가 summary 저장을 위해 다시 `end_session(...)`을 호출하면서 `end_time`이 워커 실행 시점으로 잘못 덮어써질 우려가 있었음.
- **결정**: 워커가 summary를 쓰기 전에 `get_session`으로 **원본 `end_time`을 읽어 그대로 재전달**하도록 설계하여, 실제 회의 종료 시각을 보존하면서 summary만 안전하게 갱신하도록 정렬함. (테스트에서 `end_time`이 원본 값으로 유지되는지 명시적으로 단언.)

---

## 🚀 Phase 6: 실제 STT/화자분리 모델 연동 및 실시간 검증 (2026-06-20)

> Mock 4-에이전트 파이프라인 위에 `stt_agent.py`의 스텁을 실제 **OpenVINO Whisper + pyannote 화자분리** 엔진으로 교체. 착수 순서 6-0(Pre-flight 게이트)→6-1(실엔진)→6-2(안정화)를 고정 진행.

### 1. 주요 구현 내용
- **6-0 모델명 실검증**: 로컬 `claude` CLI(v2.1.183)로 3개 에이전트 모델을 실호출 검증. `claude-3-5-haiku`가 2026-02-19 retired되어 거부됨을 확인하고 Flow/Chat을 `claude-haiku-4-5`로 교체(Report는 `claude-opus-4-8` 유지). 코드·테스트 동기화.
- **6-0 E2E 게이트에서 발견된 버그 4건 수정**: ① `run.bat`의 `(.venv)` 괄호 cmd 파서 깨짐, ② claude CLI의 세션 ID UUID 강제 사양 변경, ③ 사용자 DB 구 스키마 잔존, ④ Flow `mermaid.min.js` 미로드. (각 항목은 아래 시행착오 참조)
- **Chat 챗봇 격리·경량화**: `claude -p`를 코딩 에이전트가 아닌 회의 비서로 동작시키기 위해 `cli_controller`를 격리 실행(`--strict-mcp-config`로 MCP 0개, `--setting-sources user`+중립 cwd로 프로젝트 컨텍스트 차단, 에이전트별 `--system-prompt` 페르소나)으로 재설계. 프롬프트는 STDIN 전달로 전환.
- **6-1 실엔진**: `_load_openvino_models()`/`_process_inference()` 실구현. HW 자동감지(`_detect_device`: OpenVINO GPU→CPU), `openvino_genai.WhisperPipeline`(language=`<|ko|>`, return_timestamps) 전사 + `pyannote.audio 4.0.4` 화자분리. 블라인드 0.5초 재전사 스텁을 **에너지 VAD 엔드포인팅(발화 단위 1회 전사)** 으로 재설계.
- **6-2 안정화 내장**: `vad_threshold` 에너지 게이트 연동, 발화 분절 버퍼 + 20초 강제 분절(백프레셔), 절대 샘플 타임라인 동기, GPU 로드 실패 시 CPU 폴백.
- **모델 로컬 번들**: `prismflow/resources/models/whisper-small-int8-ov` 다운로드 배치. `tests/test_stt.py`에 VAD 분절·디바이스 감지 단위테스트 + 실엔진 옵트인(`STT_LIVE=1`) 분리. 전체 회귀 `pytest tests/` → **41 passed, 1 skipped**.
- **실측 환경**: Intel Core Ultra 7 258V + **Arc 140V iGPU(16GB)** + NPU. 라이브 한국어 전사 정확도 우수(예: "안녕하세요 마이크 준비가 완료되었습니다…"), 3초 오디오 GPU 전사 0.5초(실시간 6×).

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: 은퇴한 모델 별칭 `claude-3-5-haiku` 거부
- **상황**: 6-0 모델 실검증에서 `claude-3-5-haiku`가 "retired on February 19, 2026"로 거부(exit 1). Mock 테스트만 돌던 탓에 그동안 드러나지 않았음.
- **결정**: 유효 별칭 `claude-haiku-4-5`로 실검증 통과 후 Flow/Chat 코드·`test_flow` 동기화(테스트를 모델 인자 실검증으로 강화).

#### 🔍 이슈 2: claude CLI의 세션 ID UUID 강제 (Chat/Report 전멸)
- **상황**: CLI 사양이 바뀌어 `--resume`/`--session-id`가 **유효 UUID만 허용**. `chat-session-...`·`report-session-...` 같은 의미 기반 세션명이 전부 거부되어 Chat/Report가 동작 불능. (Flow도 동일 원인 잠복)
- **결정**: `cli_controller._normalize_session_id`로 의미 세션명을 `uuid5` 결정적 변환(동일 입력→동일 UUID로 resume 안정성 보장). 기존 resume→`--session-id` 폴백을 정상화. 단위테스트 추가.

#### 🔍 이슈 3: 사용자 DB의 구 `transcripts` 스키마 잔존 (보고서 크래시)
- **상황**: 실행 중 `ReportWorker`가 `no such column: start_time`로 실패. 원인은 Phase 2 이전에 생성된 사용자 `prismflow.db`의 `transcripts`가 단일 `timestamp` 컬럼 구조로 남아 있었고, `CREATE TABLE IF NOT EXISTS`는 컬럼을 갱신하지 못함. `add_transcript`도 조용히 -1 실패 중이었음.
- **결정**: `db._migrate_legacy_transcripts`로 구 스키마 감지 시 테이블을 신 스키마로 재생성하며 `timestamp→start_time/end_time` 매핑으로 데이터 보존. 실제 DB 이관 + 마이그레이션 단위테스트 추가.

#### 🔍 이슈 4: QWebEngine의 `file://` 스크립트 차단 (`mermaid is not defined`)
- **상황**: Flow 오버레이가 `mermaid is not defined` 콘솔 에러로 다이어그램 미표출. `setHtml(html)`을 baseUrl 없이 호출해 페이지 origin이 `about:blank`가 되면서 `<script src="file:///mermaid.min.js">` 로컬 번들 로드가 보안 차단됨.
- **결정**: `setHtml(html, baseUrl)`에 resources 디렉토리 file:// baseUrl을 지정해 로컬 콘텐츠 origin을 부여, 오프라인 번들 로드를 복구.

#### 🔍 이슈 5: Chat 챗봇이 코딩 에이전트로 동작 + 프로젝트 메모리 누수
- **상황**: 회의 질문에 "What would you like me to help with, Antigravity?"로 되묻고 응답이 느림. `claude -p`가 프로젝트 CLAUDE.md/메모리(`Antigravity`)와 MCP 서버들을 매번 로딩해 **Claude Code 코딩 에이전트 페르소나**로 동작했기 때문.
- **결정**: 사용자 요구("완전 클린·경량·Haiku 전용")에 맞춰 격리 실행 도입 — `--strict-mcp-config`(MCP 0개·고속), `--setting-sources user`+중립 cwd(프로젝트 컨텍스트 차단), 에이전트별 `--system-prompt` 페르소나, `--exclude-dynamic-system-prompt-sections`. 실측으로 누수 차단·경량화 확인.

#### 🔍 이슈 6: Windows `shell=True`의 다중줄 프롬프트 훼손 (세션 맥락 유실)
- **상황**: Chat 세션이 회의 맥락을 기억하지 못함. 단일줄 프롬프트는 기억하나 **다중줄(전사록) 프롬프트는 유실**. Windows에서 `shell=True`로 다중줄 인자를 넘기면 `cmd.exe`가 줄바꿈에서 명령을 잘라 첫 줄만 전달됐음.
- **결정**: `shell=False` + `shutil.which`로 실행파일(`claude.CMD`) 해석 + **프롬프트를 명령줄 인자가 아닌 STDIN으로 전달**. 통합 스모크로 다중줄 맥락 기억·스트리밍·무누수 검증.

#### 🔍 이슈 7: OpenVINO int8 Whisper의 word_timestamps 미지원
- **상황**: 추론 규격의 `word_timestamps=True` 설정 시 `m_decompose_cross_attention_spda_ops` 실패. int8 OV 모델이 word-level alignment용 cross-attention 분해를 미지원.
- **결정**: `return_timestamps=True`의 **segment 타임스탬프(`chunks[].start_ts/end_ts`)로 대체**. 발화별 독립 전사이므로 `condition_on_previous_text=False`와 동치이며, (speaker, text, start, end) 출력엔 충분. 또한 무음에 환각("MBC 뉴스…")이 발생함을 확인해 **VAD 게이팅 필수**를 도출.

#### 🔍 이슈 8: pyannote 게이트 모델 접근 사가 (fine-grained 토큰 + community-1)
- **상황**: pyannote 3.1은 HF 게이트 모델. 토큰을 받았으나 ① fine-grained 토큰 자체로는 메타데이터(200)는 보여도 파일은 403, ② 실제 원인은 `GatedRepo`("not in the authorized list") — 계정 약관 동의 미완. 동의 후엔 ③ pyannote.audio **4.x가 추가 게이트 모델 `speaker-diarization-community-1`** (4.x 임베딩/PLDA)을 끌어와 또 403.
- **결정**: 응답 헤더(`x-error-code: GatedRepo`)로 원인을 정밀 진단. 사용자에게 segmentation-3.0 / speaker-diarization-3.1 / **community-1** 3종 약관 동의를 순차 안내하고 `HF_TOKEN`을 `setx`로 영구 등록. 토큰 부재 시 단일화자 graceful 동작하도록 설계해 게이트가 전체 파이프라인을 막지 않게 격리.

#### 🔍 이슈 9: pyannote.audio 4.x 출력 API 변경
- **상황**: `pipeline(...)` 결과에 `itertracks`가 없어 `AttributeError`. 4.x는 `Annotation` 직접 반환이 아니라 `DiarizeOutput` 래퍼를 반환.
- **결정**: `getattr(out, "speaker_diarization", out)`로 4.x/구버전 모두 호환되게 Annotation을 추출. 토큰 인자도 `use_auth_token=`→`token=`(TypeError 폴백)로 대응. torchcodec(FFmpeg) DLL 미로드 경고는 waveform 직접 입력이라 무해 → 억제.

#### 🔍 이슈 10: 라이브 발화 파편화 (VAD 튜닝)
- **상황**: 실제 음성 라이브 테스트에서 첫 문장은 완벽 전사됐으나, 이후 말 중간 pause(0.6초 무음 endpoint)에서 발화가 "오픈 모델", "무디" 등으로 파편화. pyannote도 초단 발화에서 std/mean NaN 경고를 냄.
- **결정**: endpoint 무음을 0.6→**1.0초**로 완화하고 `min_utt`를 0.6초로 올려 초단 파편을 폐기. 경고는 `warnings.catch_warnings`로 억제. 재테스트로 개선 확인.

### 3. 교훈 (Lessons Learnt)
- **Mock 통과 ≠ 동작 보장**: 36 passed였지만 실 구동에서 CLI 사양 변경·DB 잔존 스키마·셸 인자 훼손 등 Mock이 가리던 실 버그가 한꺼번에 드러남. 게이트(6-0 E2E)가 실엔진 착수 전 이 문제들을 잡아준 것이 결정적.
- **Windows 셸 인자는 신뢰 금물**: 다중줄/특수문자 프롬프트는 STDIN으로 넘긴다. `shell=True`는 데드락뿐 아니라 줄바꿈 훼손의 원인.
- **게이트 모델은 토큰·약관·전이 의존까지**: 토큰 유효성, 계정 약관 동의, 라이브러리 버전이 끌어오는 추가 게이트 모델(community-1)까지 3중으로 막힐 수 있음. 응답 헤더의 `x-error-code`로 정밀 진단이 빠름.
- **무음 환각 → VAD는 선택이 아닌 필수**: Whisper는 무음에도 그럴듯한 문장을 환각하므로, 에너지 VAD 엔드포인팅으로 발화 구간만 전사하는 설계가 정확도의 핵심.

### 4. 남은 과제 (다음 단계)
- **오프라인/토큰리스 화자분리 배포**: pyannote를 완전히 오프라인 상태(HF_HUB_OFFLINE=1)에서 huggingface.co HEAD 요청 및 토큰 없이 로드할 수 있도록 로컬 가중치 디렉토리 및 config.yaml 구조 설계 완료 (Phase 7 예정).
- **사용자 다인 실회의 이중 검증**: 실제 2인 이상의 실사용 환경에서 화자 분류 매칭율 및 전사 정확도 추가 피드백 보완 (Phase 6-3-5 예정).

---

## 🚀 Phase 6-3: 완성도 확보 및 실엔진 앱 통합·하드닝 (2026-06-20)

### 1. 주요 구현 내용
- **콜드스타트 블라인드 윈도우 제거**: 실엔진 구동 시 Whisper와 pyannote 로딩 및 HF 체크 구간(~10-30초) 동안 발생하는 초기 발화 유실을 막기 위해, `RealTimeEngineWorker._run_real_loop`의 구동 시퀀스를 재설계하였습니다. `AudioCapture` 마이크 입력을 모델 로딩보다 선행하여 가동하고, 로드 중 발생하는 오디오 데이터를 큐에 안전하게 버퍼링하여 로딩이 끝난 즉시 전사 루프로 가져와 처리하도록 정렬하였습니다.
- **실시간 전사 가시성 (Live Subtitle)**: 회의 중 엔진 작동 여부를 사용자가 시각적으로 즉시 인지하도록 돕기 위해, `FlowUI` 오버레이 하단에 반투명 자막 레이블(`status_label`)을 결합하였습니다. STT 엔진의 4대 상태(`loading` - "엔진 준비 중", `running` - "엔진 준비 완료", `idle` - "대기 중", `error` - "오류 발생")가 트레이 알림/툴팁과 자막바에 부드럽게 노출되며, 음성이 전사될 때마다 `transcript_updated` 신호와 동기화되어 `💬 Speaker_XX: [내용]` 형태로 자막이 실시간 업데이트됩니다.
- **멀티화자 전역 일관성 (Global Speaker Matching)**: 발화 단위 독립 분리로 인해 화자 라벨이 매번 리셋되는 문제를 타파하기 위해, `pyannote/wespeaker-voxceleb-resnet34-LM` 임베딩 추출 파이프라인을 추가 연동하였습니다. 발화 오디오 윈도우가 들어오면 화자 임베딩을 추출하고, 기존 전역 화자들과의 **코사인 유사도(Cosine Similarity)**를 연산합니다. 유사도가 임계값(0.55) 이상이면 매칭되는 기존 화자 라벨로 맵핑함과 동시에 `rho_update = 0.1` 가중치로 전역 임베딩을 점진적 업데이트(블렌딩)하며, 임계값 미만인 경우 신규 화자로 분류 등록합니다.
- **QFont 폰트 폴백 경고 및 깨진 테스트 정리**:
  - Windows 환경 기동 시 폰트 사이즈가 지정되지 않아 콘솔을 오염시키던 `QFont::setPointSize: Point size <= 0 (-1)` 경고를 해결하기 위해 `main.py`의 QApplication 초기화 직후 명시적 기본 9pt 크기의 QFont를 적용하였습니다.
  - `tests/test_cli.py`에서 DB 오버라이드로 인해 invalid command 테스트가 무조건 성공해 실패하던 문제를 dummy db_path 설정을 가해 완전히 해결하였습니다.

### 2. 시행착오 및 의사결정 브랜치 (Trial & Error)

#### 🔍 이슈 1: PyAudio 기동 대기에 따른 Fallback 테스트 타임아웃
- **상황**: `AudioCapture`를 모델 로드 전에 먼저 켜면서, Windows의 마이크 리소스를 할당받는 물리적 딜레이(약 0.5~1.5초)가 추가 발생하였습니다. 이 때문에 `test_stt_real_mode_error_fallback` 테스트의 완료 루프 대기 시간(100회 * 10ms = 1초) 내에 스레드 종료 신호가 들어오지 않아 테스트가 깨지는 현상이 관측되었습니다.
- **결정**: 스레드가 리소스를 안전하게 닫고 나갈 수 있도록 에러 폴백 테스트 대기 횟수를 300회(최대 3초)로 늘려 타이밍 마진을 확보함으로써 테스트 정합성을 복구하였습니다.

#### 🔍 이슈 3: STT 에이전트 내 `logger` 누락에 따른 NameError
- **상황**: 전역 화자 매칭 로직에서 디버깅과 로깅 분석을 위해 `logger.info`를 작성해 올렸으나, `stt_agent.py` 파일 상단에 파이썬 `logging` 모듈 임포트와 `logger` 인스턴스 생성이 빠져 있어 `NameError`로 pytest가 실패하였습니다.
- **결정**: 파일 선두에 `import logging` 및 `logger = logging.getLogger(__name__)`를 외과적으로 신속히 주입하여 문제를 해결하고, 코사인 유사도 매칭 알고리즘을 로컬에서 100% 모의 검사하는 `test_global_speaker_matching` 단위 테스트를 추가해 회귀를 강화하였습니다.

### 3. 교훈 (Lessons Learnt)
- **오디오 선(先) 캡처와 버퍼링의 결합**: 비동기 오디오 큐의 강점을 활용하여, 스레드가 뜰 때 마이크를 먼저 점유하고 무거운 딥러닝 가중치를 나중에 올림으로써 데이터 손실 없는 부드러운 콜드스타트를 구현할 수 있었습니다.
- **가시성은 사용자의 신뢰와 직결**: 실시간 자막 한 줄을 UI에 얹음으로써 앱이 살아 움직이고 마이크 입력을 성실히 감지하고 있음을 확실하게 체감하게 하였습니다.

### 4. Phase 7 배포용 오프라인 설계 조기 연동 (2026-06-20)
- **오프라인 토큰리스 Diarization 로더**: `stt_agent.py` 내의 `_load_diarization_if_available` 함수를 수정하여, 로컬 리소스 폴더에 `diarization/config.yaml`과 로컬 `hf_cache` 디렉토리가 감지될 경우 `HF_HUB_OFFLINE=1`을 적용해 오프라인으로 모델을 즉시 로드하도록 분기 처리를 구현하였습니다. 이를 통해 토큰이나 인터넷 HEAD 요청 없이 번들된 가중치만으로 pyannote가 기동하는 기반을 조기 확보하였습니다.
- **Portable 릴리즈 자동화 툴 빌드**: 임베디드 파이썬 zip 다운로드, path 설정 파일(`python311._pth`) 자동 구성, site-packages 격리 pip 설치, 소스코드 및 로컬 허깅페이스 캐시(`~/.cache/huggingface/hub`) 자동 수집 이식, 그리고 오프라인용 `config.yaml` 자동 생성을 아우르는 `build_release.py` 스크립트를 작성하여 배포 단계를 원클릭으로 간소화시켰습니다.

---

## 🚀 Phase 7: 오프라인 포터블 배포 패키징 (2026-06-20)

### 1. 주요 구현 내용
- **`build_release.py` 포터블 빌더**: 인터넷이 없는 PC에서도 더블클릭으로 도는 자기완결형 배포본을 만든다. 임베디드 파이썬(zip) 내려받기 → `python311._pth`로 import 경로 고정 → 격리된 site-packages에 pip 설치 → 소스/리소스/로컬 HF 캐시 수집 이식 → 오프라인 `config.yaml` 생성까지 원클릭으로 수행한다.
- **Inno Setup 인스톨러(`setup.iss`)**: `release/` 산출물을 단일 `PrismFlow_Setup.exe` 설치 파일로 묶어 일반 사용자 배포를 단순화한다(시작메뉴/바탕화면 바로가기, 언인스톨러 포함).
- **오프라인·토큰리스 화자분리 로더**: 로컬 `diarization/config.yaml`과 `hf_cache`가 있으면 `HF_HUB_OFFLINE=1`로 분기하여, HF 토큰이나 네트워크 HEAD 요청 없이 번들 가중치만으로 pyannote가 기동하도록 했다.

### 2. 교훈
- **"오프라인"은 가중치만의 문제가 아니다**: 라이브러리가 런타임에 게이트 모델/메타데이터를 끌어오는 경로까지 모두 차단해야 진짜 오프라인이 된다. 캐시 디렉토리 구조와 `HF_HUB_OFFLINE` 분기를 함께 설계해야 한다.

---

## 🚀 Phase 9: 성능 50%+ 최적화 & 상용화 안정화 (2026-06-21)

> 목표: "성능 안정화 + 상용화 수준 성능 만족도". 성능 주장은 **벤치마크 테스트로 증명**하고, 버그는 증상이 아닌 **근본 원인**을 고친다.

### 1. 주요 구현 내용
- **9-1 STT 화자분리 핫패스 경량화**: 발화당 두 번(Diarization + Embedding) 돌던 무거운 추론을 임베딩 단독 코사인 매칭(`_match_global_speaker`)으로 축소. 발화당 무거운 추론 2회 → 1회(구조적 50% 감축).
- **9-2 Flow 입력 다이어트**: 전체 발화록을 매번 보내던 것을 **최근 15개 슬라이딩 윈도우**로 교체. 입력 프롬프트 문자 71.4%↓, 추정 입력 토큰 74.8%↓.
- **9-3 벤치마크 회귀 차단**: `tests/test_benchmark.py`가 50% 목표를 `assert`로 못박아, 이후 누가 되돌리면 테스트가 깨지도록 했다(`docs/phase9_benchmark_report.md`).
- **9-4 Chat 백그라운드 주입 폐지**: 3분 주기 IngestWorker를 영구 제거하고 **질문 시점 단발 Q&A**로 전환. 60분 회의 기준 백그라운드 CLI 기동 20회 → 0회. 지수 백오프 재시도 정비.
- **안정화**: DB에 WAL 저널 + `busy_timeout` 적용, `conftest`에 autouse DB 격리 픽스처 도입.

### 2. 시행착오 및 의사결정 브랜치

#### 🔍 이슈 1: 회의 2회차 진입 시 세그폴트(access violation)의 진짜 원인
- **상황**: 회의를 시작/종료/재시작하면 간헐적으로 네이티브 접근 위반으로 프로세스가 죽었다. SQLite 동시성을 의심했으나 WAL/lock 보강 후에도 재현됐다.
- **근본 원인**: `AppCoordinator`/`ChatAgent`가 싱글톤 `MeetingContext`의 시그널을 `__init__`에서 구독하는데, `cleanup()`에서 **disconnect하지 않아** 소멸된 '좀비' 객체가 다음 회의 신호에 반응 → STT(PyAudio)/Flow 스레드를 중복 생성하면서 충돌했다.
- **결정**: 각 컴포넌트의 `cleanup()`에서 컨텍스트 시그널을 **명시적으로 disconnect**하고, `conftest`가 매 테스트마다 컨텍스트 시그널 슬롯을 비워 백스톱하도록 했다. "새 컨텍스트-시그널 구독자를 추가하면 반드시 cleanup에서 끊는다"를 불변식으로 못박았다.

#### 🔍 이슈 2: 같은 버그 클래스의 쌍둥이 사냥
- **상황**: `ingest_timer` 정리 크래시를 고친 뒤, 같은 "GC-중-실행 QThread" 패턴이 다른 곳에도 있을 수 있다고 보고 스캔.
- **결정**: `ReportAgent.cleanup`에서 동일 패턴(실행 중 QThread의 파이썬 참조를 drop → 'Destroyed while thread is still running')을 발견해 **bounded wait + 미완료 워커는 참조 유지** 방식으로 함께 하드닝했다.

### 3. 교훈
- **싱글톤 시그널 누수 = 세그폴트의 진짜 원인**: 네이티브 크래시는 SQLite가 아니라 Qt 시그널 슬롯 수명 관리에서 왔다. 싱글톤을 구독하면 구독 해제까지가 한 세트다.
- **성능은 말이 아니라 숫자로**: 50% 주장을 `assert`로 박아두니 회귀가 원천 차단됐다.

---

## 🚀 Phase 10: 에이전트 상태 대시보드 & 오버레이 UX (2026-06-21)

### 1. 주요 구현 내용
- **`core/agent_status.py` AgentStatusHub**: 5개 에이전트(STT·Flow·Chat·i2t·Report)의 IDLE/OK/WORKING/ERROR 상태를 한 곳에서 집계하고 **신호 기반으로 푸시**(폴링 0)하는 허브. 에이전트와 UI를 느슨하게 결합해 테스트가 쉽다.
- **`ui_common/status_panel.py`**: 색점 + 상세 뱃지 패널. **`ui_common/indicators.py`**: `● 녹음 중` 점멸 인디케이터(두 오버레이 공용).
- **FlowUI 4:1:1 분할**: Mermaid 차트 : 확정 전사 기록(누적) : 에이전트 상태 패널.
- 신규 신호: `FlowAgent.analysis_started/analysis_failed`, `ChatAgent.question_received`. 코디네이터가 모든 에이전트 상태를 허브로 중계.

### 2. 교훈
- **상태 가시화는 신뢰**: 각 엔진이 살아 동작하는지 한눈에 보이면 사용자가 앱을 믿는다. 폴링 없는 신호 기반 집계로 비용은 사실상 0으로 유지했다.

---

## 🚀 Phase 11: 실제 실행 UX 하드닝 · 도구화 · 공개 (2026-06-21)

> 사용자가 `.venv\Scripts\python.exe main.py`로 **실제 앱을 구동**하며 캡처와 함께 던진 피드백을, 검증 → 계획 → 실행 → **실측 증명**의 루프로 단계별 커밋했다. 각 단계마다 전체 테스트 무결 + 실제 앱 스모크 + (가능하면) 실 CLI 실측으로 증명했다.

### 1. 주요 구현 내용 (커밋 단위)
- **Phase A — 오버레이 UX**: 녹음 인디케이터를 좌상단 → 우상단 컨트롤 묶음(최소화 버튼 옆)으로 이동, **'항상 위(StaysOnTop)' 해제**(다른 창이 포커스를 가지면 자연스럽게 뒤로), **투명도 슬라이더**(20~100%) 추가, FlowUI 상태 패널 최대 높이 제한으로 세로 확대분을 흐름도가 흡수.
- **Phase B — Flow 실시간성**: 30초 고정 틱을 **3-way 트리거**(`_should_trigger` 순수 함수)로 교체 — 최초 즉시 / 주제 전환(발화 ≥3개 누적) 시 8초 바닥만 지나면 즉시 / 정기 15초. 주제 전환 지연을 ~30초 → ~8초로.
- **Phase C — CLI 디버그 로그 창**: `core/cli_activity.py` 허브 + `ui_common/cli_log_window.py`. 백그라운드 에이전트들이 claude CLI에 주고받는 프롬프트/응답을 색 뱃지로 실시간 표시(개발 디버깅용).
- **Phase D~E — 회의 Q&A 도구 통합**: 처음엔 모드 토글로 분리했다가, 사용자 결정에 따라 **단일 회의 Q&A 흐름으로 통합**. 회의 맥락을 주입하면서도 웹 검색 + 작업 폴더 내 파일 도구(읽기/쓰기/수정/이동)를 함께 쓰고, 작업 폴더는 📁 버튼으로 지정(DB 영구 저장). 창 이름을 "PrismFlow Agent"(흐름도)·"PrismFlow Chat Agent"(채팅)로 명기, 흐름도 블록이 세로의 ~90%를 차지하고 에이전트 상태는 한 줄로 압축.
- **Phase F — 남은 항목**: ① i2t **화면 용어집 STT 교정**(PPT 슬라이드 텍스트 → 용어집 → 근접 오인식 보정), ② 회의종료 프리즈/앱종료 지연 수정, ③ 폰트 경고 필터.
- **공개**: MIT 라이선스 + README + GitHub `simturong/PrismFlow` 공개.

### 2. 시행착오 및 의사결정 브랜치

#### 🔍 이슈 1: 투명도 슬라이더를 끝까지 올려도 창이 비쳐 보임
- **상황**: 슬라이더가 `windowOpacity`를 1.0으로 올려도 창 뒤가 ~30% 비쳤다.
- **근본 원인**: 배경을 그리는 `paintEvent`가 항상 반투명(`alpha 180/255 ≈ 70%`)이라, windowOpacity가 1.0이어도 배경 자체의 alpha가 곱해져 절대 불투명해질 수 없었다.
- **결정**: 배경 채움을 **불투명(alpha 255)** 으로 바꿔 투명도를 전적으로 슬라이더(windowOpacity)가 제어하게 했다. 이제 끝까지 올리면 완전 불투명.

#### 🔍 이슈 2: "Session ID … is already in use"로 두 번째 질문부터 실패
- **상황**: 도구 모드 채팅에서 첫 질문은 되는데 두 번째 질문부터 세션 충돌 에러로 전멸.
- **근본 원인**: 스트리밍 세션 존재 확인용 **프로브가 `--resume`로 빈 턴을 실제 실행**해 세션을 오염/잠금시키고, 게다가 매번 다른 판정을 내려 `--session-id`를 재사용하다 충돌했다.
- **결정**: 프로브를 제거하고 **프로세스 내 `_created_sessions` 집합**으로 결정(최초 `--session-id` 생성, 이후 `--resume`) + 충돌 시 `--resume` 1회 폴백. 실 CLI로 동일 세션 2연속 질의(ONE→TWO) 성공을 실측.

#### 🔍 이슈 3: 회의 종료 시 UI가 멈춤(프리즈)
- **상황**: Flow 에이전트가 CLI 호출 중일 때 회의를 끝내면, `stop()`의 무한 `wait()`가 메인 스레드를 호출이 끝날 때까지(최대 30초) 붙들었다.
- **결정**: `FlowAgent.stop(wait_ms)` 바운드 대기 + 코디네이터가 끝나지 않으면 신호를 끊고 **백그라운드로 배수(drain)**(참조 유지로 GC 크래시 방지). 8초 in-flight 호출에도 종료 블록을 ~266ms로 실측. 또한 **앱 완전 종료**는 `cli_controller.terminate_all()`로 in-flight 서브프로세스를 즉시 사살(~0ms)해 빠르게 닫히게 했다.

#### 🔍 이슈 4: 화면 글자를 STT 교정에 쓰되 과교정은 막기
- **상황**: 발표 슬라이드의 정확한 표기로 음성인식 오인식을 되돌리고 싶지만, 섣부른 자동 치환은 멀쩡한 단어를 망칠 위험이 크다.
- **결정**: `core/glossary.py`에서 **보수적 근접 보정** — 같은 문자 체계, 길이 차 작음, 유사도 0.8 이상일 때만 치환(긴 단어의 1자 오인식은 잡고, 짧고 흔한 단어·전사(transliteration)는 건드리지 않음). PPT 텍스트는 COM으로 읽어 `screen_glossary` 테이블에 적재.


### 3. 교훈
- **Mock 통과 ≠ 실사용 보장(재확인)**: 세션 충돌·프리즈·투명도 버그는 모두 테스트가 아니라 **실제 앱 구동**에서 드러났다. 실 CLI 실측(파일 생성, 세션 2연속, 프로세스 사살 0ms)으로 증명한 것이 결정적.
- **단순화가 곧 안정화**: 도구 모드를 별도 세션으로 분리했던 설계가 세션 충돌의 씨앗이었다. 단일 회의 Q&A로 통합하니 충돌이 사라지고 UX도 단순해졌다.
- **보수적 자동화**: 자동 교정은 "확실할 때만" 동작해야 신뢰를 얻는다. 임계값과 가드로 과교정을 원천 차단했다.

---

## 🚀 Phase 12: 프로젝트 구조 최적화 및 불필요 문서 정리 (2026-06-21)

### 1. 주요 구현 내용
- **불필요한 Handoff 문서 및 레거시 폴더/파일 일괄 영구 삭제**: 프로젝트 인수를 거치며 생성된 수많은 아티팩트 및 문서 내 `handoff_*.md` 파일들과 더불어, 인계 전용 레거시 폴더였던 `artifacts/` 폴더 전체 및 중복 기록인 `docs/phase9_benchmark_report.md` 파일을 영구 삭제하여 소스 트리의 제어권을 완전 확보했습니다.
- **커스텀 룰 단일 지침서 통합 및 Handoff/설정 폴더 완전 차단**: 
  - 기존의 분산되어 있던 `.agents/AGENTS.md` 파일과 `.agents/` 디렉토리를 완전히 영구 삭제했습니다.
  - 해당 파일에 명시되어 있던 계획서 다이렉트 협의 의무, 상세 설계 완료 의무, 작업 상태판 업데이트 규칙 등 핵심 프로젝트 수칙을 루트의 `agent.md`로 통합하여 일원화했습니다.
  - AI 에이전트가 앞으로 임의로 `.agents/` 디렉토리나 `AGENTS.md` 지침 파일을 생성하는 것을 금지하도록 `agent.md` 지침에 명문화했습니다.
- **구조 청소 및 무결성 검증**: 불필요한 폴더/파일을 모두 제거하고 PyTest 전체 스위트를 2회 연속 수행하여 트리 개편 중 소스 코드 무결성이 유지됨을 완벽하게 검증했습니다.

### 2. 교훈
- **프로젝트 통제권 확보 및 지침 일원화**: 파편화된 규칙들과 설정 파일, 레거시 빈 폴더들을 깔끔하게 제거하고 모든 지침을 루트 `agent.md` 단일 정본으로 관리함으로써 에이전트가 단일 소스로 규칙을 학습하고 혼선을 방지할 수 있습니다.
- **설정 폴더 재생성 방어**: AI 에이전트가 시스템적으로 custom rule 파일을 자동으로 만들거나 사용하지 못하게 루트 `agent.md` 파일의 명확한 차단 지침을 작성하여 방어하는 것이 매우 유효합니다.


---

## 🚀 Phase 13: 출력 구조화 및 제어 보강 (2026-06-21)

### 1. 주요 구현 내용
- **세션별 출력 격리**: `AppConfig` 및 DB `settings` 테이블에 `output_dir` 설정을 확장하여 기동 경로를 동적으로 오버라이드하고, `SettingsDialog`를 통해 사용자가 GUI에서 직접 출력 경로를 변경할 수 있도록 브라우저 버튼을 탑재했습니다. 세션 시작 시 `output_dir/{session_id}/` 단일 폴더를 생성하고 회의 녹음(WAV), 전사록(TXT), 보고서(MD) 3대 핵심 파일을 이 세션별 격리 폴더 하위로 정합시켜 데이터 유실 위험을 방지하고 관리를 직관화했습니다.
- **실시간 Interim 피드 및 자막창 확장**: 라이브 음성을 말하는 즉시 눈으로 볼 수 있도록 실시간 임시(Interim) 전사 피드를 UI 배선하고, 2~3줄의 문장이 잘림 없이 표출되도록 자막창의 세로 높이를 2배(85px) 확대하여 사용성 가시성을 대폭 개선했습니다.
- **STT 회의 제어 보강**: 우측 상단 컨트롤 바에 회의 일시중지(Pause), 재개(Resume), 정지(Stop) 버튼을 신설하여 STT 오디오 캡처 루프 및 엔진의 연동 제어를 안정적으로 제어했습니다.
- **Mermaid 시각화 정비**: CLI 사용량 한도 초과 판정 키워드를 축소 조율하고, 회의 대화 흐름의 구조적 명확성을 위해 Mermaid 프롬프트와 로컬 폴백 룰을 개편하여 화자 표시(`Speaker_XX`)를 시각적으로 제거했습니다. 상단에는 핵심 요약 뉴스 자막바를 얹어 전반적인 아젠다 추이를 파악하도록 설계했습니다.

### 2. 교훈
- **구조화된 산출물 관리의 중요성**: 모든 일회성 파일들을 임의의 루트 폴더가 아닌 세션별 격리 디렉토리에 정합해 둠으로써 향후 프로젝트 디렉토리의 청결도와 관리 복잡도를 비약적으로 축소할 수 있었습니다.
- **버튼 및 시그널의 유기적 연동**: 복잡한 비동기 백그라운드 엔진 상태에 맞춰 GUI 컨트롤 버튼이 유기적으로 반응하도록 설계하는 과정이 사용자 신뢰도를 크게 향상시킵니다.


---

## 🚀 Phase 14: 모드 표시 및 여백 최적화 (2026-06-21)

### 1. 주요 구현 내용
- **Mermaid 뷰 꽉 채우기 (여백 최적화)**: QWebEngineView와 외부 테두리 간의 과도하게 낭비되던 이중 여백을 없애기 위해 `mermaid_html.py` 의 CSS 설정을 수정하여 `body padding`을 2px로 극단화하고, `#diagram-container` 의 가로/세로를 100%로 팽창시켜 흐름도 렌더링 공간을 꽉 채웠습니다. border-radius도 8px로 조절하여 하단 전사기록창의 둥근 모서리와 통일감을 주었습니다.
- **상단 핵심 요약 뉴스 자막바 가독성 향상**: 상단 뉴스 헤드라인의 텍스트가 눈에 잘 띄도록 글씨 크기를 11px에서 13px로 격상시키고, 커진 글자가 잘리지 않도록 세로폭을 24px에서 30px로 상향 조정하였습니다.
- **좌상단 엔진 모드 (Claude/Local) 동적 명시**: 현재 시각화 흐름도가 원격 Claude AI 에 의해 갱신되었는지, 혹은 한도 초과 등에 따라 로컬 폴백 모드로 생성되었는지 판별하도록 `update_engine_mode` API를 구현하고 `AppCoordinator` 의 `_on_flow_diagram_updated` 핸들러에서 세션 리밋 상태를 검사해 동적으로 표기하도록 배선했습니다. 또한 상태 뱃지 디테일에도 `(Claude)` / `(Local)` 과 같이 동기화 적용했습니다.
- **중복 실행 방지 기능 추가**: 사용자가 `run.bat` 또는 직접적인 파이썬 인터프리터 등으로 앱을 중복 기동하는 문제를 막기 위해 `main.py` 의 `main` 진입 시점에 `QLockFile` 을 이용한 단일 인스턴스 락 확인 로직을 통합하였습니다. 만약 이미 락이 소유되어 있다면 경고 메시지 상자를 보여준 뒤 즉시 안전하게 종료합니다.
- **기본 투명도 100% (완전 불투명) 적용**: 앱 초기 실행 시 오버레이 화면의 높은 시인성을 위해 기본 투명도를 0.5(50%)에서 1.0(100%) 완전 불투명 상태로 변경하였습니다. 이에 맞춰 `overlay.py` 의 `normal_opacity`와 `hover_opacity`를 1.0으로 조정하여 슬라이더로 조절하기 전까지는 또렷한 화면을 제공합니다.
- **STT 정확도 향상을 위한 기획 분석 검토**:
  - Intel Core Ultra 7 258V (Arc GPU, VRAM 16GB) 사양 등 고스펙 로컬 장비에 맞게 한국어 전사 성능을 올릴 수 있도록, 상위 모델(`whisper-medium-int8-ov` (760MB), `whisper-large-v3-int8-ov` (1.5GB)) 번들의 동적 로딩 및 Hugging Face 감지 셋업 로직을 기획 검토했습니다.

### 2. 교훈
- **디테일한 UI 일관성의 시각적 영향력**: 단 몇 px 수준의 HTML/CSS 마진 조율과 폰트 크기 조정만으로도 화면이 조밀하고 견고한 프로덕션급 제품으로 거듭나는 경험을 얻었습니다.
- **동적 상태 명시의 사용성**: AI 모드(Claude vs Local)를 창 타이틀과 대시보드에 솔직하고 투명하게 노출하여, 사용자가 AI 작동 결과를 오인하거나 한도 초과 오류 상태를 방지할 수 있는 신뢰 체인을 확보했습니다.
- **중복 자원 점유 방지**: 오디오 장치 등 하드웨어 리소스를 독점 제어해야 하는 STT 엔진이 중복 기동될 경우 디바이스 충돌이 발생할 우려가 있으므로, 프로세스 기동 진입점 단계에서 단일 락으로 중복 실행을 확실히 막는 것이 상용 안정성에 필수적임을 학습했습니다.


---

## 🚀 Phase 15: STT 상위 모델(medium/large-v3) 실배선 및 셋업 도구 (2026-06-21)

### 1. 주요 구현 내용
- **사전 점검으로 실제 공백 식별**: Phase 14-4에서 "기획"으로 남겨 둔 medium/large-v3 지원에 착수하며 먼저 현행 코드를 점검한 결과, 모델 크기→OpenVINO 디렉토리 매핑(`AppConfig.whisper_dir_name`), 설정 다이얼로그 콤보(tiny~large-v3) 및 설치 상태 라벨, `stt_agent._load_openvino_models`의 동적 로드까지 **배선은 이미 완비**되어 있음을 확인했습니다. 즉 진짜 빠진 것은 "상위 모델을 받을 수단"과 "미설치 선택 시의 안내"뿐이었습니다.
- **출처 정합 발견**: 기존 `whisper-small-int8-ov` 번들의 README가 HuggingFace `OpenVINO` org의 사전 빌드 int8-ov 모델임을 가리키고 있었습니다. 같은 org가 `OpenVINO/whisper-medium-int8-ov`·`OpenVINO/whisper-large-v3-int8-ov`를 제공하므로, optimum/nncf 로컬 변환(무겁고 torch 의존) 없이 이미 설치된 `huggingface_hub`의 `snapshot_download`만으로 small과 동일한 출처·레이아웃을 그대로 재현할 수 있었습니다.
- **셋업 스크립트(`scripts/setup_whisper_model.py`) 신설**: 모델 크기를 받아 `OpenVINO/whisper-{size}-int8-ov`를 `prismflow/resources/models/whisper-{size}-int8-ov`로 내려받습니다. `--list`로 설치 상태 일람, `--force`로 재다운로드, 이미 설치된 경우 멱등 skip을 지원하며, 순수 헬퍼(`repo_id_for`/`dir_name_for`/`target_dir_for`/`is_installed`)를 분리해 네트워크 없이 단위 테스트가 가능하도록 했습니다.
- **미설치 안내 UX 보강**: 사용자가 설정에서 medium을 고른 뒤 회의를 시작했는데 가중치가 없으면 기존에는 경로만 알려 주는 에러였습니다. 이제 `_load_openvino_models`가 디렉토리명에서 크기를 역산해 `python scripts/setup_whisper_model.py medium` 설치 명령(+small 폴백)을 그대로 안내하고, 설정 다이얼로그의 "✗ 미설치" 라벨에도 동일 명령을 노출합니다.
- **medium 실설치 및 검증**: 셋업 스크립트로 `whisper-medium-int8-ov`(748MB)를 실제 다운로드·배치하고, OpenVINO `WhisperPipeline` 로드(CPU 2.1s)까지 스모크 검증했습니다. 대용량 가중치는 `.gitignore` 처리되어 리포지토리에 커밋되지 않습니다.

### 2. 교훈
- **"기획→구현" 전 반드시 현행 코드부터 점검**: 계획서가 medium/large를 "다음 Phase"로 미뤄 둔 탓에 큰 작업으로 보였지만, 실제로는 배선의 대부분이 이미 존재했습니다. 코드를 먼저 읽었기에 중복 구현 없이 진짜 공백(획득 수단·안내)만 최소 변경으로 채울 수 있었습니다.
- **기존 산출물의 출처를 따라가면 가장 단순한 해법이 나온다**: small 번들 README 한 줄(공식 사전 빌드 int8-ov)이 optimum 로컬 변환이라는 무거운 우회로를 통째로 제거해 주었습니다.
- **에러 메시지는 곧 복구 절차여야 한다**: 미설치 에러가 "경로 안내"에서 "복붙 가능한 설치 명령"으로 바뀌면서, 사용자가 막힘 없이 자가 해결할 수 있는 경로를 확보했습니다.

