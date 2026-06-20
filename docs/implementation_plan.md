# PrismFlow 최종 구현 계획서

> 본 문서는 PrismFlow 프로젝트의 **유일한 정본(Single Source of Truth)** 계획서입니다.
> 프로젝트 디렉토리 내 `docs/implementation_plan.md`는 이 문서의 미러(Mirror)이며,
> Phase 작업 진입 전 양쪽을 동기화하여 관리합니다.

---

## 1. 프로젝트 정의

**PrismFlow**는 Windows 시스템 트레이에 상주하면서, 로컬 디바이스에서 회의 음성을 실시간 감지·녹음·전사(STT)하고, 4개의 독립 AI 에이전트(STT · Flow · Chat · Docs)가 유기적으로 협업하여 회의 흐름 시각화, 맥락 기반 Q&A, 최종 회의록 생성을 수행하는 **차세대 AI 회의 어시스턴트**입니다.

### 핵심 제약 조건
- **On-Device 영역 (외부 네트워크 불필요)**
  - STT 음성 인식 및 화자 분리: `faster-whisper` + `pyannote.audio` 로컬 실행
  - PySide6 UI 프로그램 전체 운영: 시스템 트레이, 투명 오버레이, QWebEngineView
- **Claude CLI 경유 영역 (로컬 CLI가 Anthropic 서버와 통신)**
  - Flow Agent: 회의 흐름 Mermaid 구조도 생성 (Haiku)
  - Chat Agent: 맥락 기반 실시간 Q&A (Haiku)
  - Docs Agent: 최종 회의록 Markdown 생성 (Opus)
  - ※ 외부 REST API를 직접 호출하지 않고, 로컬에 설치된 `claude` CLI를 `subprocess.Popen` 파이프로 제어
- **하드웨어 가속 (STT 전용, 자동 감지)**
  - Windows 11 고정 — OS 호환성 보장
  - 사용자 하드웨어 환경이 다를 수 있으므로 프로그램 기동 시 **자동 감지 순서**를 적용:
    1. NVIDIA GPU 감지 → CUDA(float16/int8) 가속
    2. Intel GPU/NPU 감지 → OpenVINO 가속
    3. 위 둘 다 없을 경우 → **CPU 폴백** (속도는 느리지만 반드시 동작 보장)
  - 설정 화면에서 사용자가 수동으로 가속 방식을 오버라이드할 수 있음
- **UI 프레임워크** — PySide6 (투명 오버레이 + QWebEngineView)

---

## 2. 확정된 설계 결정 사항

### 2-1. 시각화 엔진: Mermaid.js + QWebEngineView (로컬 번들링)

| 항목 | 내용 |
|:---|:---|
| **선택** | Mermaid.js를 `QWebEngineView`에서 렌더링 |
| **이유** | CSS 기반 Glassmorphism 스타일링 자유도, 자동 레이아웃 엔진 |
| **오프라인 보장** | `mermaid.min.js`를 프로젝트 내부 `resources/`에 로컬 파일로 패키징 |

### 2-2. Claude CLI 세션 분리 및 컨텍스트 병합

| 세션 | 모델 | 역할 | 컨텍스트 전략 |
|:---|:---|:---|:---|
| **Flow 세션** | Haiku | 30초 주기 Mermaid 구조도 생성 | 누적 발화 전체를 슬라이딩 윈도우로 추출 |
| **Chat 세션** | Haiku | 사용자 Q&A 즉시 응답 | 최근 10분 발화 원본 + Flow 요약 + 현재 Mermaid 코드 결합 |
| **Docs 세션** | Opus | 회의 종료 시 최종 보고서 | 전체 STT 원본 + 최종 Flow + Chat 이력 통합 |

- **통신 방식**: `subprocess.Popen` 상주 세션 + 백그라운드 스레드 + `queue.Queue` 비차단 I/O
- Flow와 Chat은 **별도 프로세스**로 완전 분리하여 스레드 데드락 방지

### 2-3. STT 및 화자 분리

- 설정 화면에서 Whisper 모델 크기(base/medium/large) 및 가속(CUDA/OpenVINO/CPU) 선택
- 모델 미존재 시 다운로드 상태바 제공
- **개발용 Mock 모드**: 15~20초 주기로 가상 다자 대화 자동 주입 (토글)

### 2-4. 최종 보고서 저장

- 저장 경로: `%USERPROFILE%\Documents\PrismFlow\YYYY-MM-DD\`
- 포맷: Markdown (회의 요약 + 의제별 쟁점 + 결정 사항 + Todo + Mermaid 소스 포함)
- 저장 후 Windows 기본 연결 프로그램으로 자동 실행

---

## 3. 시스템 아키텍처

```mermaid
graph TD
    subgraph 진입점
        Main["main.py"] --> SystemTray["시스템 트레이<br/>(ui_common/tray.py)"]
    end

    subgraph "core/ — 중앙 제어 레이어"
        Config["config.py<br/>전역 설정"]
        Context["context.py<br/>MeetingContext 싱글톤"]
        DB["db.py<br/>SQLite 영구 저장"]
        CLI["cli_controller.py<br/>Claude CLI 비차단 파이프"]
    end

    subgraph "ui_common/ — 공통 UI"
        Tray["tray.py<br/>트레이 메뉴"]
        Overlay["overlay.py<br/>투명 오버레이 베이스"]
    end

    subgraph "agents/ — 수직 슬라이스 에이전트군"
        subgraph "agents/stt/"
            STT_Agent["stt_agent.py<br/>음성 캡처 + 전사"]
            Audio["audio.py<br/>WASAPI 루프백"]
        end
        subgraph "agents/flow/"
            Flow_Agent["flow_agent.py<br/>30초 주기 분석"]
            Flow_UI["flow_ui.py<br/>Mermaid 오버레이"]
        end
        subgraph "agents/chat/"
            Chat_Agent["chat_agent.py<br/>RAG Q&A"]
            Chat_UI["chat_ui.py<br/>채팅 오버레이"]
        end
        subgraph "agents/docs/"
            Docs_Agent["docs_agent.py<br/>회의록 컴파일"]
        end
    end

    SystemTray --> Context
    Audio --> STT_Agent --> Context
    Context <--> DB

    Flow_Agent -->|"Haiku 세션"| CLI
    Chat_Agent -->|"Haiku 세션"| CLI
    Docs_Agent -->|"Opus 세션"| CLI

    Context --> Flow_Agent
    Context --> Chat_Agent
    Context --> Docs_Agent

    CLI --> Flow_UI
    CLI --> Chat_UI
```

---

## 4. 프로젝트 트리 구조

```text
E:\Tak\Gemini\PrismFlow\
│
│   ── 프로젝트 관리 ──────────────────────────────────────────
├── agent.md                        # AI 내비게이션: 읽기 순서, 수정 위치 안내, 코딩 규칙
├── main.py                         # 앱 진입점: QApplication 생성, 트레이 기동, 에이전트 오케스트레이션
├── run.bat                         # Windows 원클릭 실행 (가상환경 활성화 + python main.py)
│
│   ── 산출물 문서 ─────────────────────────────────────────────
├── docs/
│   ├── implementation_plan.md      # Phase 진입 전 업데이트하는 상세 구현 설계서
│   ├── task.md                     # Phase 진행 중/완료 후 업데이트하는 진행률 상태판
│   └── history.md                  # Phase 완료 시 작성하는 시행착오 및 의사결정 위키 스토리
│
│   ── ReAct 검증 ──────────────────────────────────────────────
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # 공통 피스처: 임시 DB, Mock CLI, QApplication 인스턴스
│   ├── test_core.py                # config / context 싱글톤 스레드 세이프티 검증
│   ├── test_db.py                  # SQLite 스키마 생성, CRUD, 세션 복원 테스트
│   ├── test_cli.py                 # Claude CLI 파이프 비차단 I/O, 타임아웃, 데드락 검증
│   ├── test_stt.py                 # Mock 발화 스트림 → MeetingContext 파이프라인 검증
│   ├── test_flow.py                # Mermaid 코드 파싱, 노드 재사용(Upsert) 유효성 검사
│   ├── test_chat.py                # RAG 컨텍스트 조립 (10분 발화 + Flow 요약 + Mermaid) 검증
│   └── test_docs.py                # Markdown 최종 리포트 생성 및 파일 I/O 검증
│
│   ── 메인 패키지 ─────────────────────────────────────────────
└── prismflow/
    ├── __init__.py
    │
    ├── core/                       # ■ 중앙 제어 레이어 (모든 에이전트가 의존)
    │   ├── __init__.py
    │   ├── config.py               #   전역 환경설정 (경로, 모델, 가속, 윈도우 기본값)
    │   ├── context.py              #   Thread-safe MeetingContext 싱글톤 + Qt Signal 방출
    │   ├── db.py                   #   SQLite 연결, 스키마 마이그레이션, 세션/발화/채팅 CRUD
    │   └── cli_controller.py       #   Claude CLI Popen 래퍼: 세션 생성, 비차단 읽기, 모델 지정
    │
    ├── ui_common/                  # ■ 공유 UI 컴포넌트
    │   ├── __init__.py
    │   ├── tray.py                 #   시스템 트레이 아이콘 + 우클릭 메뉴 (회의 시작/종료/설정/종료)
    │   └── overlay.py              #   투명 오버레이 베이스: FramelessHint, 호버 페이드, 드래그 이동
    │
    └── agents/                     # ■ 수직 슬라이스 에이전트 (각 폴더가 독립 기능 단위)
        │
        ├── stt/                    # ① STT 에이전트 슬라이스
        │   ├── __init__.py
        │   ├── stt_agent.py        #   QThread: VAD 청크 → faster-whisper 전사 → context 적재
        │   └── audio.py            #   sounddevice / WASAPI 루프백 캡처 유틸
        │
        ├── flow/                   # ② Flow 시각화 에이전트 슬라이스
        │   ├── __init__.py
        │   ├── flow_agent.py       #   QThread: 30초 슬라이딩 윈도우 → Claude Haiku → Mermaid 코드
        │   ├── flow_ui.py          #   QWebEngineView 투명 오버레이 (overlay.py 상속)
        │   ├── mermaid_html.py     #   로컬 js 임베드 HTML 템플릿 생성기
        │   └── resources/
        │       └── mermaid.min.js  #   오프라인용 로컬 번들 Mermaid.js 라이브러리
        │
        ├── chat/                   # ③ Chat 어시스턴트 에이전트 슬라이스
        │   ├── __init__.py
        │   ├── chat_agent.py       #   QThread: RAG 컨텍스트 조립 → Claude Haiku → 스트리밍 응답
        │   └── chat_ui.py          #   입력창 + 대화 히스토리 투명 오버레이 (overlay.py 상속)
        │
        └── docs/                   # ④ Docs 보고서 에이전트 슬라이스
            ├── __init__.py
            └── docs_agent.py       #   Claude Opus → Markdown 컴파일 → 파일 저장 → 자동 실행
```

---

## 5. Phase별 개발 계획 및 ReAct 검증

### Phase 1: Core 인프라 + 시스템 트레이 + 투명 오버레이 GUI

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/core/config.py` | 전역 설정 클래스 정의 (경로, 모델 크기, 가속 방식, UI 기본값) |
| `prismflow/core/context.py` | `MeetingContext` 싱글톤 뼈대 — 스레드 Lock + Qt Signal 정의 |
| `prismflow/ui_common/overlay.py` | 투명 오버레이 베이스 윈도우 (FramelessHint, 호버 페이드 애니메이션, 드래그 이동) |
| `prismflow/ui_common/tray.py` | 시스템 트레이 아이콘 + 메뉴 (회의 시작/종료/대시보드/설정/종료) |
| `main.py` | QApplication 생성 → 트레이 기동 → 오버레이 인스턴스 테스트 |
| `tests/conftest.py` | QApplication 피스처, 임시 설정 경로 |
| `tests/test_core.py` | config 로드, context 싱글톤 스레드 세이프티 |

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_core.py -v
```

---

### Phase 2: SQLite DB + STT 실시간 엔진 & Mock 에뮬레이터 설계

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/core/db.py` | SQLite 연결, 스키마 생성 및 CRUD 구현 (시작/종료 시간 개별 필드 적용) |
| `prismflow/core/context.py` | DB 연동 확장 — 회의 시작/종료/발화 추가 시 DB에 실시간 저장 수행 |
| `prismflow/agents/stt/audio.py` | PyAudio 기반 마이크 오디오 실시간 캡처 유틸 (16000Hz, Mono, Float32, 링버퍼 적재 Lock 제어) |
| `prismflow/agents/stt/stt_agent.py` | `RealTimeEngineWorker` (QThread) 구현:<br/>1. OpenVINO GenAI 2025.0 Stateful Whisper 및 pyannote-openvino 실시간 추론 연동<br/>2. 가중치 미존재 시 안내 다이얼로그 처리<br/>3. Mock 모드: 가상 한국어 대화 큐를 통해 실제 엔진과 동일한 (start, end, speaker, text) 신호 주기적 방출 |
| `tests/test_db.py` | 스키마 자동 생성, 발화 및 세션 CRUD 검증 테스트 |
| `tests/test_stt.py` | STT 스레드 기동 후 실제 오디오 수집 버퍼 작동 및 Mock 모드 신호 발생 주기 검증 |

#### SQLite 테이블 상세 설계 (정밀화)
1. **회의 세션 (`meeting_sessions`)**:
   - `session_id` (TEXT, PK): timestamp 기반 ID (`YYYYMMDD_HHMMSS`)
   - `title` (TEXT): 회의 제목 (기본값: "새로운 회의")
   - `start_time` (TEXT): 회의 시작 일시 (ISO8601)
   - `end_time` (TEXT, NULLABLE): 회의 종료 일시 (ISO8601)
   - `summary` (TEXT, NULLABLE): 최종 요약 보고서 본문
2. **발화 데이터 (`transcripts`)**:
   - `id` (INTEGER, PK AUTOINCREMENT): 발화 순번
   - `session_id` (TEXT, FK): `meeting_sessions.session_id` 외래키
   - `speaker` (TEXT): 화자 식별자 (예: Speaker_00, Speaker_01 등)
   - `text` (TEXT): 전사된 대화 텍스트
   - `start_time` (REAL): 발화 시작 타임스탬프 (초)
   - `end_time` (REAL): 발화 종료 타임스탬프 (초)
3. **채팅 기록 데이터 (`chat_logs`)**:
   - `id` (INTEGER, PK AUTOINCREMENT): 채팅 로그 ID
   - `session_id` (TEXT, FK): `meeting_sessions.session_id` 외래키
   - `query` (TEXT): 사용자 질문 내용
   - `response` (TEXT): Claude CLI를 통해 전달받은 Q&A 답변 내용
   - `timestamp` (REAL): Q&A 시점 UNIX Epoch Timestamp
4. **애플리케이션 설정 (`settings`)**:
   - `key` (TEXT, PK): 설정 식별자 (예: `whisper_model_size`, `hardware_acceleration`, `vad_threshold` 등)
   - `value` (TEXT): 설정값

#### STT & Diarization 핵심 파이프라인 설계 규칙
* **오디오 표준 규격**: 샘플 레이트 `16000Hz`, 단일 채널(`Mono`), 데이터 타입 `Float32`
* **추론 윈도우 알고리즘**: 5.0초 분석 윈도우, 0.5초 시프트 슬라이딩 윈도우 적용
* **추론 파라미터 강제 제어**:
  - `condition_on_previous_text = False` (환각 누적 방지)
  - `language = "<|ko|>"` (언어 감지 생략, 약 50ms 지연 단축)
  - `word_timestamps = True` (정밀 타임라인 동기화)
  - Diarization: `duration = 5.0, step = 0.5, rho_update = 0.1`

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_db.py tests/test_stt.py -v
```

---

### Phase 3: Claude CLI 파이프 + Flow Agent + Mermaid 시각화 & 스마트 화면 융합

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/core/cli_controller.py` | Claude CLI 래퍼: `-p` (프린트) 모드 기반 단발성 비동기 호출 구현, `< NUL` 리다이렉션을 통한 TTY 경고 방어 및 데드락 0% 보장, UUID 기반 세션 관리 |
| `prismflow/agents/flow/flow_agent.py` | 30초 슬라이딩 윈도우 → Claude Haiku 프롬프트 → Mermaid 코드 파싱<br/>- **Stateful Update**: 직전 Mermaid 코드를 함께 전송하여 기존 노드 구조 재사용(Upsert) 유도<br/>- **계층화/필터**: 대주제 서브그래프화, 잡담 노이즈 필터 및 흐름선 매핑 |
| `prismflow/agents/flow/flow_ui.py` | QWebEngineView 투명 오버레이 + 동적 Mermaid 렌더링 |
| `prismflow/agents/flow/mermaid_html.py` | 로컬 js 임베드 HTML 템플릿 생성기 |
| `prismflow/agents/flow/resources/mermaid.min.js` | 오프라인용 라이브러리 다운로드 배치 |
| `prismflow/core/screen_detector.py` [NEW] | **스마트 화면 맥락 감지**: PPT 슬라이드 감지(Office COM API - win32com) 및 범용 감지(Pillow 32x32 초경량 픽셀 변화율 MSE 분석)<br/>- 30초 정착(Settled) 디바운스 및 가벼운 시각 지시어 매핑 적용 |
| `tests/test_cli.py` | 로컬 Claude CLI `-p` 호출 타임아웃, 세션 공유, 에러 발생 예외 처리 검증 |
| `tests/test_flow.py` | Mermaid 코드 문법 유효성, 노드 재사용(Upsert) 검사, 화면 전환 이벤트 연계 검증 |

#### 상세 기술 설계 명세

##### 1. Claude CLI 비차단 통신 (`cli_controller.py`)
- **비대화형(Print) 모드 강제 및 리다이렉션**:
  - `claude` CLI를 대화형 Popen 상주 프로세스로 유지하면 Windows의 입출력 버퍼 데드락, ANSI 이스케이프 코드 가공 등 극심한 불안정성에 노출됩니다.
  - 이를 원천 방어하기 위해 `claude -p "<프롬프트>" --session-id <UUID> --model <모델>` 형태로 호출하는 단발성 실행 모델을 채택합니다.
  - Windows TTY 미감지 대기 경고(`Warning: no stdin data received in 3s`)를 해결하기 위해 standard input을 `subprocess.DEVNULL` (또는 Windows CMD `< NUL`)로 리다이렉션합니다.
- **세션 격리 및 병렬 처리**:
  - 각 에이전트(Flow, Chat, Docs)는 초기화 시 고유한 `uuid.uuid4()` 세션 ID를 생성하여 요청 시 전달합니다.
  - Claude CLI 호출은 Python의 `subprocess.run(..., capture_output=True, text=True, timeout=30)`을 사용하여 동기 실행하되, 에이전트의 자체 `QThread` 안에서 독립적으로 작동하므로 메인 UI 스레드를 절대 블로킹하지 않습니다.
- **비차단 큐 피드백**:
  - UI 렌더러와 CLI 에이전트 간의 통신은 Qt Signal을 이용해 안전하게 비동기 스레드 바운더리를 넘어 데이터가 전송되도록 구현합니다.

##### 2. 오프라인 Mermaid 시각화 UI (`flow_ui.py`, `mermaid_html.py`)
- **오프라인 라이브러리 번들링**: 
  - `prismflow/agents/flow/resources/mermaid.min.js`에 번들링된 라이브러리를 로드하여 순수 오프라인 상태에서도 동작을 보장합니다.
- **HTML 템플릿 및 스타일링**:
  - `mermaid_html.py`는 로컬 `mermaid.min.js`를 상대경로로 참조하는 HTML 템플릿을 생성합니다.
  - Glassmorphism 느낌의 반투명 다크 디자인을 적용하기 위해 HSL 테마 컬러 및 `backdrop-filter: blur(10px)` 등을 CSS에 빌드합니다.
- **깜빡임 없는 동적 렌더링**:
  - 30초마다 새로운 Mermaid 다이어그램 신호가 도달할 때, `QWebEngineView.reload()`를 호출하면 화면이 깜빡이거나 하얗게 로딩이 드러나 시인성이 매우 낮아집니다.
  - 이를 방지하기 위해 HTML 로드 후, 신호가 들어올 때마다 `QWebEngineView.page().runJavaScript(f"updateDiagram(\"{encoded_mermaid_code}\")")`를 실행하여 JS DOM 상에서 점진적 다이어그램 리렌더링을 처리합니다.

##### 3. Flow Agent 분석 루프 및 스마트 화면 맥락 융합 (`flow_agent.py`, `screen_detector.py`)
- **Stateful 점진적 다이어그램 업데이트**:
  - 매 30초마다 `MeetingContext`에서 최신 발화 내역을 가져와 Claude Haiku에 전달합니다.
  - 프롬프트에 `[기존 Mermaid 코드]`를 함께 전송하며, *"기존 노드들의 ID를 최대한 재사용(Upsert)하고 새로운 소주제 논의 사항은 꼬리에 덧붙여 나가라"*는 프롬프트 제약을 가해 시각적 흐름의 연속성을 보존합니다.
- **스마트 화면 감지기 (ScreenTransitionDetector)**:
  - **30초 정착(Settled) 디바운스**:
    - 화면 변화가 발생하면 즉시 이벤트를 발생시키지 않고, `QTimer`를 기동하여 30초 타이머를 굴립니다.
    - 30초 이내에 추가 화면 변화가 감지되면 타이머를 리셋(Reset) 및 재시작하여, 사용자가 슬라이드를 빠르게 훑는 동안의 중간 전환 과정은 과도한 API 호출로 이어지지 않게 제어합니다.
  - **파워포인트 전체화면 감지 (win32com.client)**:
    - Windows COM API를 활용하여 실행 중인 PowerPoint.Application의 `SlideShowWindows` 및 `ActivePresentation` 객체를 추적합니다.
    - 슬라이드가 변경되어 `SlideShowWindow.View.CurrentShowPosition` (SlideIndex) 값이 바뀌는 순간을 정밀 추적합니다.
  - **범용 화면 감지 폴백 (Pillow + MSE)**:
    - PPT 실행 중이 아닐 경우 `PIL.ImageGrab.grab()`을 통해 1초 주기 스냅샷을 캡처합니다.
    - 오버헤드를 극단적으로 줄이기 위해 캡처본을 32x32 크기로 축소하고, GrayScale로 변환하여 numpy 배열로 바꿉니다.
    - 직전 32x32 이미지와 현재 이미지의 MSE (Mean Squared Error)를 계산하여 임계값(예: 10.0)을 넘을 때 화면 변화가 일어난 것으로 간주합니다.
  - **중복 전송 방지 (Deduplication)**:
    - PPT 화면: `Presentation.Name` + `SlideIndex`가 직전 확정 상태와 동일하면 무시합니다.
    - 범용 화면: 정착 완료된 32x32 캡처본의 픽셀 간 차이가 직전 확정본과 거의 동일한 경우(MSE < 1.0) 중복으로 판단해 캡처 이벤트를 생략(Skip)합니다.
  - **시각 지시어 결합**:
    - STT 발화 중 "여기 보시면", "이 슬라이드", "이 도표" 등 화면 지칭용 지시어가 가볍게 매칭되는 순간, 대기 중이던 확정 캡처 데이터를 결합하여 Claude CLI 측에 맥락 보조 자료로 제공합니다.
- **회의 논리 계층화**:
  - 논의의 큰 줄기는 Mermaid `subgraph`로 묶어서 구조화하고, 잡담이나 인사는 Haiku 프롬프트 수준에서 무시하도록 프롬프트를 고도화합니다.

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_cli.py tests/test_flow.py -v
```

---

### Phase 4: Chat Agent + 하이브리드 RAG + 대화창 UI

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/agents/chat/chat_agent.py` | 백그라운드 컨텍스트 주입기(Context Ingester) 및 Q&A 비동기 스레드 개발<br/>- 3분 간격 신규 발화 백그라운드 자동 주입(CLI 세션 적재)<br/>- 질문 시점의 미주입 실시간 잔여 발화 + 사용자 질문 병합 전송<br/>- 마이크 제어를 원천 배제한 텍스트 단독 입력 지원 |
| `prismflow/agents/chat/chat_ui.py` | QTextBrowser 기반 Markdown 대화 히스토리 및 QLineEdit 입력창을 탑재한 투명 오버레이 UI 개발 (QSS Glassmorphism 및 그라데이션 포커스 효과 적용) |
| `tests/test_chat.py` | 주기적 전사록 백그라운드 주입 로직, 미주입 발화 병합 쿼리 구성, 모의 스트리밍 렌더링 검사 |

#### 상세 기술 설계 명세

##### 1. 백그라운드 컨텍스트 주입(Context Ingestion) 및 Q&A 스레드 (`chat_agent.py`)
- **오디오 경합 방지**:
  - 로컬 STT 에이전트와의 사운드 장치 독점 경합을 피하기 위해 Chat 에이전트의 마이크 음성 입력 기능은 완전히 배제하고, 키보드 텍스트 입력창만 단독 제공합니다.
- **3분 주기 전사록 백그라운드 주입**:
  - 질문 시점에 무거운 전체 회의 전사록을 매번 전송하면 토큰 낭비 및 응답 지연이 심해집니다.
  - 이를 해결하기 위해 백그라운드 주입 루프(`BackgroundIngester`)를 구동하여, **3분 주기**로 새로 추가된 신규 발화문만 떼어내어 로컬 Claude CLI 세션에 빌드업해 둡니다:
    `claude -p "[시스템: 다음은 회의 중 추가된 신규 대화 내용입니다. 기억해 두세요.]\n{new_transcripts}" --resume chat-session-{session_id}`
  - 주입을 마치면 마지막 주입 완료 발화 인덱스(`last_ingested_idx`)를 업데이트합니다.
- **질문 시점 실시간 동기화 및 고속 쿼리**:
  - 사용자가 질문을 던지는 시점에는 이미 Claude 세션 메모리가 회의 전체 흐름을 알고 있으므로, 전체 텍스트를 보낼 필요가 없습니다.
  - 단, 3분 주기 주입 시점과 질문 시점 사이의 짧은 미주입 발화(0~3분 분량)가 있을 수 있으므로, 질문 시에는 미주입 잔여 발화만 질문 위에 가볍게 얹어서 호출합니다:
    `claude -p "[최근 대화 추가]\n{unsubmitted_transcripts}\n\n[질문]\n{user_query}" --resume chat-session-{session_id}`
  - 이를 통해 **API 토큰 소모량을 90% 이상 차감하고, 사용자 질문 시 즉각적인 답변 속도를 확보**합니다. 회의가 완전히 종료된 후에는 별도의 전사록 주입 없이 순수하게 질문/출력 세션만 복원하여 가볍게 연속 Q&A가 가능합니다.
- **비동기 스트리밍 출력**:
  - `subprocess.Popen`으로 `stdout`을 `PIPE`로 감시하여, Claude CLI의 스트리밍 토큰 출력을 줄 단위로 획득하고 Qt Signal(`token_delivered`)을 통해 UI 스레드로 비동기 안전 전송합니다.

##### 2. QSS 기반 Glassmorphism 대화 오버레이 UI (`chat_ui.py`)
- **디자인 테마 및 레이아웃**:
  - `TranslucentOverlay`를 상속하여 우측 하단에 상주하는 420x580 크기의 메신저 형태 대화창을 구현합니다.
  - 배경에 어두운 반투명 색상(`RGBA(25, 25, 30, 200)`) 및 14px 라운딩 처리, 테두리에 실버 그라데이션 보더를 QSS로 세밀하게 입힙니다.
- **입출력 컴포넌트 고도화**:
  - **대화 히스토리 뷰**: `QTextBrowser`를 활용해 마크다운 및 HTML 파싱을 활성화합니다. 이를 통해 코드 블록(syntax highlight), 볼드, 리스트가 아름다운 개발자 지향적 레이아웃으로 렌더링되게 만듭니다.
  - **텍스트 입력창**: `QLineEdit`를 사용하여 테두리를 반투명하게 둥글리고, 마우스 포커스가 들어갈 때 딥퍼플(`rgb(124, 77, 255)`) 그라데이션으로 빛나는 트랜지션 애니메이션 효과를 부여합니다.
  - **로딩 및 입력 잠금**: 답변이 생성 중인 동안에는 입력창을 `setEnabled(False)`로 잠그고, 대화창 하단에 부드럽게 점멸하는 'Claude가 생각하는 중...' 로딩 레이블을 노출합니다.

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_chat.py -v
```

---

### Phase 4-2: 예외 처리, 통합 최적화 및 융합 데모 (AppCoordinator 연동)

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `main.py` | `ChatAgent` 및 `ChatUI` 인스턴스화 및 우측 하단 자동 배치 연동<br/>- 메인 윈도우 좌표 배치: 화면 우측 하단 여백 (`x = screen.width() - chat_ui.width() - 40`, `y = screen.height() - chat_ui.height() - 100`) |
| `prismflow/agents/chat/chat_agent.py` | 백그라운드 비동기 스레드 클린업 로직 구현 (`cleanup` 메소드 추가 및 실행 중인 Ingest/QNA Worker 종료 처리)<br/>- 초기 세션 로드 완료 시그널 방출 및 대기 처리 |
| `prismflow/agents/chat/chat_ui.py` | 초기 세션 생성 대기 중 입력창 임시 비활성화 처리 및 완성도 보강 |
| `prismflow/core/screen_detector.py` | win32com 파워포인트 체크 시 예외 방어막 추가 (PPT 실행 중이 아니거나 로딩 에러 시 `GENERIC` 캡처 폴백 보장) |
| `tests/test_chat.py` | `ChatAgent.cleanup` 스레드 정리 및 예외 안전성 테스트 케이스 보강 |

#### 상세 기술 설계 명세
1. **AppCoordinator 연동 (`main.py`)**:
   - `AppCoordinator.__init__`에서 `self.chat_agent = ChatAgent(self.context, self.cli_controller)` 및 `self.chat_ui = ChatUI(self.chat_agent)`를 생성합니다.
   - 트레이 아이콘과 동일하게 앱 시작 시 메인 윈도우 우측 하단에 상주하도록 고정합니다.
   - 회의가 종료(`_on_meeting_ended`)될 때 `stt_worker`나 `flow_agent`는 멈추지만, Q&A 대화는 회의 종료 후에도 계속 가능하게 `chat_ui`는 그대로 유지합니다.
2. **백그라운드 스레드 누수 방지 (`chat_agent.py`)**:
   - `ChatAgent`에 `cleanup(self)` 메소드를 탑재하여 `ingest_timer.stop()`, 기동 중인 모든 QThread(`IngestWorker`, `ChatQNAWorker`) 인스턴스를 순회하며 `wait()` 및 종료 대기를 수행합니다.
   - `main.py`의 `AppCoordinator`가 소멸하거나 앱 종료 시 이를 명시적으로 호출합니다.
3. **스마트 화면 감지 PPT 예외 격리 (`screen_detector.py`)**:
   - win32com을 사용한 `_get_active_ppt_info` 내부에서 `pywintypes.com_error` 등 모든 COM 예외를 완전 캡처하여 `None`을 리턴하게 함으로써, 백그라운드 탐지 루프가 PPT 오류에 의해 무한 루프 폭사하지 않도록 합니다.

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_chat.py -v
.venv\Scripts\python -m pytest tests/test_flow.py -v
```

---

### Phase 4-3: 추가 최적화 및 설정/환경 고도화 (Settings, Screen DB, CLI Path Override, Local WebFont)

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/core/db.py` | `screen_logs` 테이블 생성 마이그레이션 및 화면 로그 추가/조회 기능 구현 (`add_screen_log`, `get_screen_logs`) |
| `prismflow/core/context.py` | `update_screen_info` 실행 시 SQLite `screen_logs` 테이블에 화면 맥락 로그 실시간 영구 적재 연동 |
| `prismflow/core/config.py` | `claude_cli_cmd` 초기 로드 시 DB의 `settings` 테이블 오버라이드 로직 적용 |
| `prismflow/ui_common/settings_ui.py` [NEW] | 콤보박스, 슬라이더, 파일 브라우저 및 SQLite `settings` 저장 버튼을 탑재한 설정 다이얼로그(`SettingsDialog`) GUI 개발 |
| `prismflow/ui_common/tray.py` | "설정" 메뉴 클릭 시 `SettingsDialog`를 기동하고 `AppConfig` 업데이트와 실시간 연동 |
| `prismflow/resources/Pretendard-Regular.ttf` [NEW] | 가독성이 뛰어난 Pretendard 폰트 파일을 프로젝트 로컬에 수동 패키징 및 번들 배치 |
| `main.py` | 앱 시작 시 `QFontDatabase`를 이용해 Pretendard 로컬 폰트를 등록하고 QSS 스타일시트(`font-family: 'Pretendard'`)에 바인딩 적용 |
| `tests/test_db.py` | `screen_logs` 테이블 스키마 생성 및 CRUD 검증 테스트 케이스 추가 |
| `tests/test_core.py` | DB에 저장된 `claude_cli_cmd`가 `AppConfig`에 로드 및 오버라이드되는지 검증하는 테스트 추가 |

#### 상세 기술 설계 명세
1. **`screen_logs` 데이터베이스 스키마 설계**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `session_id` (TEXT, FK): `meeting_sessions.session_id` 외래키 (ON DELETE CASCADE)
   - `screen_type` (TEXT): "PPT" 또는 "GENERIC"
   - `screen_info` (TEXT): PPT인 경우 `"파일명|페이지번호"`, GENERIC인 경우 32x32 픽셀 강도 데이터를 문자열(또는 base64)로 변환해 저장
   - `timestamp` (REAL): 로그가 적재된 에폭 시간
2. **Claude CLI 경로 동적 오버라이드**:
   - `AppConfig` 인스턴스화 또는 로드 시, `DatabaseManager`를 가볍게 열어 `get_setting("claude_cli_cmd")` 값이 존재할 경우 해당 객체의 `claude_cli_cmd` 멤버를 덮어씁니다.
   - 설정 화면에서 경로 저장 시 `DatabaseManager.set_setting("claude_cli_cmd", path)`를 실행해 DB에 영구 기록합니다.
3. **로컬 웹폰트 Pretendard 번들링**:
   - 폰트 파일 `prismflow/resources/Pretendard-Regular.ttf`를 internal 리소스로 다운로드/배치합니다.
   - `main.py` 진입점에서 `QFontDatabase.addApplicationFont(font_path)`를 사용해 메모리에 해당 폰트를 활성화하고, QApplication 단위의 QSS 또는 개별 UI QSS에 `font-family: 'Pretendard';`를 전역 선언합니다.

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_db.py -v
.venv\Scripts\python -m pytest tests/test_core.py -v
```

---

### Phase 5: Docs Agent + 최종 보고서 + 통합 최적화

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/agents/docs/docs_agent.py` | 전체 STT + 최종 Flow + Chat 이력 → Claude Opus → Markdown 컴파일 |
| `run.bat` | 가상환경 활성화 + `python main.py` 원클릭 실행 |
| `tests/test_docs.py` | Markdown 리포트 생성 검증, 파일 저장 경로 확인 |

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_docs.py -v
```

---

## 6. AI 바이브 코딩 문서 체계 및 운영 규칙

| 문서 | 위치 | 업데이트 시점 | 역할 |
|:---|:---|:---|:---|
| **agent.md** | 프로젝트 루트 | 트리 구조 변경 시 상시 | AI가 어디를 읽고 어디를 고칠지 안내하는 내비게이션 |
| **docs/implementation_plan.md** | docs/ | Phase 작업 **시작 전** | 해당 Phase의 상세 구현 설계서 |
| **docs/task.md** | docs/ | Phase 작업 **진행 중/완료 후** | 전체 과정 중 현재 위치, 수행 내역, 다음 목표 |
| **docs/history.md** | docs/ | Phase **완료 시** | 시행착오(Trial & Error), 대안 비교, 블로커 상황, 교훈을 **스토리텔링** 형식으로 기록 |

---

## 7. 검증 계획 요약

### 자동화 (매 Phase마다)
- `pytest tests/` 전체 실행으로 회귀(Regression) 방지
- 10분 Mock 시뮬레이션을 통한 메모리 누수 및 프레임 드랍 측정

### 수동 (Phase 3 이후)
- 마우스 호버 투명도 전환 시각 효과 점검
- 듀얼 모니터 드래그/스냅 동작 확인
- 실제 마이크 입력을 통한 로컬 Faster-Whisper 응답성 점검
- 회의 종료 → Docs 리포트 자동 생성 및 기본 뷰어 실행 확인
