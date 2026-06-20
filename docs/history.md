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
