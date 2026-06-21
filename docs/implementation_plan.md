# PrismFlow 최종 구현 계획서

> 본 문서(`docs/implementation_plan.md`)는 PrismFlow 프로젝트 계획의 **유일한 정본(Single Source of Truth)** 입니다.
> 별도의 미러나 복제본을 두지 않으며, 모든 Phase 설계 변경은 이 문서에 직접 점진적으로 반영합니다.
> (`docs/task.md` 역시 진행률 상태판의 유일한 정본입니다. 이 프로젝트에서는 handoff 문서를 작성하지 않으며, artifacts/ 폴더는 임시 관리 폴더이나 수시로 정리됩니다.)

---

## 📌 목차 (Table of Contents)

1. [1. 프로젝트 정의](#1-프로젝트-정의)
2. [2. 확정된 설계 결정 사항](#2-확정된-설계-결정-사항)
   * [2-1. 시각화 엔진: Mermaid.js + QWebEngineView (로컬 번들링)](#2-1-시각화-엔진-mermaidjs--qwebengineview-로컬-번들링)
   * [2-2. Claude CLI 세션 분리 및 컨텍스트 병합](#2-2-claude-cli-세션-분리-및-컨텍스트-병합)
   * [2-3. STT 및 화자 분리](#2-3-stt-및-화자-분리)
   * [2-4. 최종 보고서 저장](#2-4-최종-보고서-저장)
3. [3. 시스템 아키텍처](#3-시스템-아키텍처)
4. [4. 프로젝트 트리 구조](#4-프로젝트-트리-구조)
5. [5. Phase별 개발 계획 및 ReAct 검증](#5-phase별-개발-계획-및-react-검증)
   * [Phase 1: Core 인프라 + 시스템 트레이 + 투명 오버레이 GUI](#phase-1-core-인프라--시스템-트레이--투명-오버레이-gui)
   * [Phase 2: SQLite DB + STT 실시간 엔진 & Mock 에뮬레이터 설계](#phase-2-sqlite-db--stt-실시간-엔진--mock-에뮬레이터-설계)
   * [Phase 3: Claude CLI 파이프 + Flow Agent + Mermaid 시각화 & 스마트 화면 융합](#phase-3-claude-cli-파이프--flow-agent--mermaid-시각화--스마트-화면-융합)
   * [Phase 4: Chat Agent + 하이브리드 RAG + 대화창 UI](#phase-4-chat-agent--하이브리드-rag--대화창-ui)
   * [Phase 4-2: 예외 처리, 통합 최적화 및 융합 데모 (AppCoordinator 연동)](#phase-4-2-예외-처리-통합-최적화-및-융합-데모-appcoordinator-연동)
   * [Phase 4-3: 추가 최적화 및 설정/환경 고도화 (Settings, Screen DB, CLI Path Override, Local WebFont)](#phase-4-3-추가-최적화-및-설정환경-고도화-settings-screen-db-cli-path-override-local-webfont)
   * [Phase 5: Report Agent + 최종 보고서 + 통합 최적화](#phase-5-report-agent--최종-보고서--통합-최적화)
   * [Phase 6: 실제 오픈소스 STT/화자분리 모델 연동 및 실시간 검증](#phase-6-실제-오픈소스-stt화자분리-모델-연동-및-실시간-검증)
6. [6. AI 바이브 코딩 문서 체계 및 운영 규칙](#6-ai-바이브-코딩-문서-체계-및-운영-규칙)
7. [7. 검증 계획 요약](#7-검증-계획-요약)
8. [8. 상세 구현 설계서: Phase 7 & Phase 8](#8-상세-구현-설계서-phase-7--phase-8)
   * [Phase 7: E2E 통합 하네스, 디버깅 및 예외 하드닝 (E2E 특집)](#phase-7-e2e-통합-하네스-디버깅-및-예외-하드닝-e2e-특집)
     * [7-1. E2E 통합 테스트 하네스 (tests/e2e_harness.py) 구축](#7-1-e2e-통합-테스트-하네스-testse2e_harnesspy-구축)
     * [7-2. Claude CLI 에러 하드닝 및 로컬 Fallback(대체) 모드 구현](#7-2-claude-cli-에러-하드닝-및-로컬-fallback대체-모드-구현)
     * [7-3. WAV 원본 실시간 녹음 및 전사록 텍스트(.txt) 실시간 저장](#7-3-wav-원본-실시간-녹음-및-전사록-텍스트txt-실시간-저장)
     * [7-4. Flow 에이전트의 증분(Delta) 전사 업데이트 및 히스토리 저장](#7-4-flow-에이전트의-증분delta-전사-업데이트-및-히스토리-저장)
     * [7-5. I2T 에이전트 (Image-to-Text Agent) 신설 및 캡처 연동](#7-5-i2t-에이전트-image-to-text-agent-신설-및-캡처-연동)
     * [7-6. 사용자 오인식 교정(Auto-Correction Map) 및 자가 개선 루프](#7-6-사용자-오인식-교정auto-correction-map-및-자가-개선-루프)
     * [7-7. 실시간 전사 가시성(라이브 자막) 제공](#7-7-실시간-전사-가시성라이브-자막-제공)
   * [Phase 8: 오프라인 원클릭 패키징 및 가중치 모델 통합 배포 (순연)](#phase-8-오프라인-원클릭-패키징-및-가중치-모델-통합-배포-순연)
     * [8-1. pyannote 토큰리스 오프라인 로컬 로드 설계 상세](#8-1-pyannote-토큰리스-오프라인-로컬-로드-설계-상세)
     * [8-2. Portable Python 격리 패키지 구조 설계 상세](#8-2-portable-python-격리-패키지-구조-설계-상세)
     * [8-3. Inno Setup 인스톨러 빌드 상세](#8-3-inno-setup-인스톨러-빌드-상세)
9. [9. 상세 구현 설계서: Phase 12 (프로젝트 구조 최적화 및 불필요 문서 정리)](#9-상세-구현-설계서-phase-12-프로젝트-구조-최적화-및-불필요-문서-정리)

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
        subgraph "agents/report/"
            Report_Agent["report_agent.py<br/>회의록 컴파일"]
        end
    end

    SystemTray --> Context
    Audio --> STT_Agent --> Context
    Context <--> DB

    Flow_Agent -->|"Haiku 세션"| CLI
    Chat_Agent -->|"Haiku 세션"| CLI
    Report_Agent -->|"Opus 세션"| CLI

    Context --> Flow_Agent
    Context --> Chat_Agent
    Context --> Report_Agent

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
│   └── test_report.py              # Markdown 최종 리포트 생성 및 파일 I/O 검증
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
        └── report/                 # ④ Report 보고서 에이전트 슬라이스
            ├── __init__.py
            └── report_agent.py     #   Claude Opus → Markdown 컴파일 → 파일 저장 → 자동 실행
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
   - `ChatAgent`에 `cleanup(self)` 메소드를 탑재하여 기동 중인 모든 QThread(`ChatQNAWorker`) 인스턴스를 순회하며 `wait()` 및 종료 대기를 수행합니다.
     (※ Phase 9-4에서 `IngestWorker`와 `ingest_timer`가 폐지되어 `cleanup`은 더 이상 타이머를 참조하지 않으며, DB·CLI 접근 중인 워커를 즉시 `terminate()`하지 않고 우선 `wait(5000)`으로 안전 합류시킵니다.)
   - `main.py`의 `AppCoordinator`가 소멸하거나 앱 종료 시 이를 명시적으로 호출합니다. 각 정리 단계는 개별 try/except로 격리되어 한 단계의 실패가 나머지 스레드 종료를 가로막지 않습니다.
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

### Phase 5: Report Agent (구 Docs/Synthesizer Agent) + 최종 보고서 + 통합 최적화

> **명칭 확정**: 추상적이던 `SynthesizerAgent` 대신, 산출물(보고서/리포트)을 직관적으로 드러내는 **`ReportAgent`** / **`ReportWorker`** 로 클래스·폴더·파일명·테스트·문서를 일괄 통일합니다. (폴더 `agents/report/`, 파일 `report_agent.py`, 테스트 `test_report.py`)
> **모델 확정**: 최종 회의록은 추론 품질이 가장 높은 **Opus 4.8 (`claude-opus-4-8`)** 모델로 단발 생성합니다.

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/agents/report/__init__.py` [NEW] | ReportAgent 모듈 진입점 제공 |
| `prismflow/agents/report/report_agent.py` [NEW] | `ReportAgent` (QObject) 및 `ReportWorker` (QThread) 구현:<br/>- `signals.meeting_ended` 구독 및 세션 종료 자동 감지<br/>- SQLite DB에서 회의 정보, 전체 발화록(`transcripts`), 채팅 히스토리(`chat_logs`) 추출<br/>- `MeetingContext`에서 최종 Mermaid 흐름도 추출<br/>- Claude Opus 4.8 (`claude-opus-4-8`)용 단발 프롬프트 구성 및 비동기 CLI 호출<br/>- Markdown 포맷 회의록 컴파일 (회의 요약 + 아젠다 쟁점 + 최종 Mermaid 소스 + Todo 리스트)<br/>- `%USERPROFILE%\Documents\PrismFlow\Reports\YYYY-MM-DD\` 경로 하위에 `report_{session_id}.md` 파일 실시간 저장<br/>- SQLite `meeting_sessions.summary` 컬럼에 보고서 본문 영구 저장 업데이트<br/>- `os.startfile`을 이용한 Windows 기본 연결 프로그램 자동 실행 및 타 플랫폼 예외 방어 |
| `main.py` | `AppCoordinator`에 `ReportAgent` 인스턴스 연동 및 `signals.meeting_ended` 발생 시 보고서 컴파일 흐름 연결 |
| `run.bat` [NEW] | Windows 원클릭 통합 실행 스크립트 작성 (가상환경 활성화 및 `python main.py` 실행) |
| `tests/test_report.py` [NEW] | ReportAgent 최종 보고서 생성 검증:<br/>- SQLite DB 적재 데이터 및 최종 Mermaid 코드가 올바르게 병합된 프롬프트 구성 확인<br/>- `ClaudeCLIController` Mocking을 통한 Claude Opus 응답 생성 검증<br/>- 임시 디렉토리 하위의 `YYYY-MM-DD` 날짜별 폴더 구조 생성 및 Markdown 파일 인코딩(UTF-8) 저장 검증<br/>- DB의 `meeting_sessions` 테이블 내 `summary` 필드 업데이트 여부 확인<br/>- `os.startfile` 모크 호출 횟수 및 인자 검증 |

#### 상세 기술 설계 명세

##### 1. Report Agent 데이터 융합 및 비동기 생성 스레드 (`report_agent.py`)
- **회의 종료 감지 및 스레드 가동**:
  - `ReportAgent`는 `MeetingContext` 인스턴스의 `signals.meeting_ended` 시그널에 `_on_meeting_ended` 메소드를 바인딩합니다.
  - 해당 시그널이 도달하면 전달받은 `session_id`를 기반으로 `ReportWorker` (QThread) 인스턴스를 동적으로 생성 및 시작하여 백그라운드에서 보고서를 생성하도록 합니다. 이를 통해 회의 종료 시 발생할 수 있는 UI 스레드 멈춤 현상을 원천 방지합니다.
  - 슬롯 진입 시점(메인 스레드)에 `context.current_mermaid_code`를 캡처하여 워커에 전달함으로써, 이후 `context.reset()` 호출과의 레이스 컨디션을 방지합니다.
- **SQLite DB 데이터 수집**:
  - `ReportWorker` 내에서 `db_manager.get_session(session_id)`를 호출해 회의 메타데이터(회의 제목 `title`, 시작 시간 `start_time`, 종료 시간 `end_time`)를 로드합니다.
  - `db_manager.get_transcripts(session_id)`를 통해 회의 시작부터 종료까지 누적된 모든 화자별 발화 목록을 가져옵니다.
  - `db_manager.get_chat_logs(session_id)`를 통해 회의 중 사용자와 어시스턴트 사이에 주고받은 Q&A 채팅 로그 목록을 로드합니다.
  - `context.current_mermaid_code`를 읽어 최종 시각화 Mermaid 흐름도를 가져옵니다.
- **Claude Opus 정밀 보고서 프롬프트 설계**:
  - 수집된 모든 자료를 유기적으로 조합하여 하나의 컨텍스트로 구성하고, Claude Opus 4.8 (`claude-opus-4-8`) 모델에 전달할 프롬프트를 빌드합니다.
  - **프롬프트 템플릿 구조**:
    ```text
    [시스템 역할]
    당신은 PrismFlow 프로젝트의 전문 회의 기록관 및 비즈니스 분석가입니다. 제공된 회의 컨텍스트(STT 발화문, 채팅 히스토리, Mermaid 흐름도)를 정밀 분석하여 임원진 보고용 고품질 Markdown 회의록을 작성하십시오.

    [회의 기본 정보]
    - 세션 ID: {session_id}
    - 회의 제목: {title}
    - 일시: {start_time} ~ {end_time}

    [최종 Mermaid 흐름도]
    {mermaid_code}

    [회의 중 질의응답 (Chat Logs)]
    {chat_logs}

    [전체 STT 전사록]
    {transcripts}

    [작성 규칙 및 구조 가이드라인]
    1. 회의 요약: 회의의 목적, 주요 의제, 핵심 결론 및 합의 내용을 3-4문장으로 명확히 정리하십시오.
    2. 아젠다별 쟁점: 각 세부 아젠다별로 의견이 엇갈렸던 쟁점 사항, 대립된 의견의 흐름, 그리고 최종적으로 합의된 솔루션을 구체적으로 작성하십시오.
    3. 최종 Mermaid 소스: 회의 중 도출된 최종 Mermaid 코드를 코드 블록(```mermaid) 안에 그대로 온전히 포함시키십시오.
    4. Todo 리스트: 회의에서 결정된 향후 작업 항목(Action Item), 담당자, 그리고 언급된 마감 기한을 명확한 리스트 포맷으로 추출하십시오.
    5. 서론, 결론, 혹은 "알겠습니다. 작성해 드리겠습니다"와 같은 AI의 불필요한 메타 설명 문구는 제외하고, 오직 순수한 Markdown 내용만 반환하십시오.
    ```
- **Claude CLI 단발 실행**:
  - `cli_controller.execute_command(prompt, session_id="report-session-{session_id}", model="claude-opus-4-8", timeout=120)`를 수행합니다.
  - Opus 모델 특성상 긴 회의록의 경우 추론 시간이 오래 소요될 수 있으므로 타임아웃 값을 120초로 넉넉하게 지정합니다.
- **날짜별 폴더 구조 저장 및 DB 동기화**:
  - 오늘 날짜에 해당하는 `YYYY-MM-DD` 형식의 폴더를 `%USERPROFILE%\Documents\PrismFlow\Reports\` 하위에 생성합니다. (예: `C:\Users\<사용자>\Documents\PrismFlow\Reports\2026-06-20\`)
  - 생성된 폴더 내에 `report_{session_id}.md` 형태로 파일명을 구성하고, UTF-8 인코딩으로 마크다운 파일을 기록합니다.
  - 파일 저장이 정상적으로 끝나면, SQLite 데이터베이스의 `meeting_sessions` 테이블에서 해당 `session_id` 레코드의 `summary` 컬럼에 생성된 Markdown 보고서 텍스트 전체를 업데이트합니다. (`db_manager.end_session(session_id, end_time=original_end_time, summary=report_content)` 호출)
- **Windows 연결 프로그램 연동**:
  - 파일 생성이 완료되면 `os.startfile(report_filepath)`를 실행하여, 사용자의 Windows 시스템에 기본값으로 지정된 마크다운 뷰어 또는 텍스트 편집기로 문서를 즉시 띄웁니다.
  - 단위 테스트 환경이나 Windows 이외의 플랫폼(예: macOS, Linux)에서는 `os.startfile`이 존재하지 않아 예외가 발생하므로, `sys.platform == 'win32'` 및 `hasattr(os, 'startfile')` 가드가 포함되도록 예외 방어 처리를 합니다.

##### 2. Windows 원클릭 실행 런처 (`run.bat`)
- 가상환경의 활성화 여부를 자동으로 판단하고 애플리케이션 진입점 `main.py`를 원클릭 실행할 수 있는 배치 스크립트를 작성합니다.
```batch
@echo off
title PrismFlow - AI Meeting Assistant
cd /d "%~dp0"

echo [PrismFlow] Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment (.venv) not found. Please run setup first.
    pause
    exit /b 1
)

echo [PrismFlow] Launching application...
python main.py
if %errorlevel% neq 0 (
    echo [ERROR] Application exited with error code %errorlevel%.
    pause
)
endlocal
```

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_report.py -v
.venv\Scripts\python -m pytest tests/ -v
```

---

### Phase 6: 실제 오픈소스 STT/화자분리 모델 연동 및 실시간 검증

> Mock 모드로 완성된 4-에이전트 파이프라인 위에, `stt_agent.py`의 스텁(`_load_openvino_models` / `_process_inference`)을 실제 OpenVINO Whisper + pyannote 화자분리 엔진으로 교체하여 **진짜 마이크 입력으로 동작하는 MVP**를 완성하는 단계.
> **착수 순서 고정: 6-0(Pre-flight 게이트) → 6-1(실엔진) → 6-2(안정화).** 6-0을 통과하지 못하면 6-1 착수 금지.

#### Phase 6-0: MVP 실동작 게이트 (Pre-flight) — STT 코드 수정 전 선행

실제 STT 모델을 얹기 전에, **현재 Mock 기반 MVP가 실제로 구동되는지부터 증명**한다. (Phase 5 감사에서 도출된 필수 선결 항목 #2·#5)

| 항목 | 작업 내용 |
|:---|:---|
| **6-0-A. 에이전트 모델명 실검증** | 로컬 `claude` CLI로 3개 에이전트 모델명을 실제 단발 호출하여 통과 여부 확인:<br/>- Chat/Flow: `claude-3-5-haiku` (구형 별칭 — 거부 가능성 있음)<br/>- Report: `claude-opus-4-8`<br/>- 거부 시 유효 별칭으로 교체(예: Haiku → `claude-haiku-4-5`)하고 `chat_agent.py`·`flow_agent.py`·`report_agent.py` 및 관련 테스트를 동기화<br/>- 검증: 실제 CLI 1회 응답 확인 (옵트인 마커 `@pytest.mark.live` 또는 수동 스모크)<br/><br/>**✅ 결과(2026-06-20, CLI v2.1.183):** `claude-3-5-haiku`는 **2026-02-19 retired**되어 거부(`exit=1`, "It may not exist or you may not have access to it"). `claude-opus-4-8`는 통과(PONG). 대체 별칭 `claude-haiku-4-5`도 통과(PONG) 확인. → **Flow/Chat을 `claude-haiku-4-5`로 교체**(Report는 `claude-opus-4-8` 유지). 동기화 파일: `flow_agent.py`, `chat_agent.py`(2곳), `cli_controller.py`(독스트링 예시), `tests/test_flow.py`(모델 인자 실검증으로 강화). `pytest tests/` → 36 passed. |
| **6-0-B. run.bat E2E 1회 구동** | `run.bat` 실행 → 트레이 → **회의 시작 → Mock 발화 누적 → Flow 다이어그램 표출 → Chat Q&A → 회의 종료 → 보고서 자동 생성·팝업**까지 육안 확인.<br/>- Phase 5에서 수정한 회의 종료 크래시(`QWebEnginePage.html()` → `FlowUI.reset_diagram()`)가 실제로 막혔는지 포함 검증<br/>- 산출물: E2E 체크리스트 + 스크린샷, 발견 이슈 즉시 패치 |

#### Phase 6-1: 실제 STT/화자분리 엔진 구현 (핵심)

| 대상 파일 | 작업 내용 |
|:---|:---|
| `prismflow/agents/stt/stt_agent.py` | `_load_openvino_models()` 실구현:<br/>- 하드웨어 자동 감지 체인 **NVIDIA CUDA → Intel OpenVINO/NPU → CPU 폴백** (설정 수동 오버라이드 허용)<br/>- `openvino-genai` Stateful Whisper 로드 + pyannote 화자분리 파이프라인 탑재<br/>- 가중치 **로컬 경로(`prismflow/resources/models/`) 우선 탐색**으로 오프라인 강제, 미존재 시 안내 다이얼로그/다운로드 상태바<br/><br/>`_process_inference()` 실구현 (현재 `return "Speaker_00", ""` 스텁 대체):<br/>- 추론 규격(§2-3 준수): 5.0초 윈도우 / 0.5초 시프트, `condition_on_previous_text=False`, `language="<|ko|>"`, `word_timestamps=True`<br/>- Diarization: `duration=5.0, step=0.5, rho_update=0.1`<br/>- `(speaker, text)` 반환 → 기존 `_run_real_loop` 버퍼 파이프라인 연결 |
| `prismflow/agents/stt/audio.py` | 실제 마이크 캡처(16kHz / Mono / Float32) 동작 검증 및 링버퍼 안정화 |
| `prismflow/resources/models/` [NEW] | Whisper / pyannote 가중치 로컬 번들 배치 경로 (Phase 7 오프라인 배포 전제) |

> **모델 출처 메모**: Whisper는 Hugging Face(OpenVINO 변환본 또는 `faster-whisper`) 자유 다운로드. 화자분리 `pyannote/speaker-diarization-3.1`은 **게이트(gated) 모델**로 HF 계정·약관 동의·액세스 토큰 필요. 최초 1회 온라인 수신 후 로컬 번들링. 게이트가 부담되면 비게이트 diarization 대안 검토 가능. (6-1 착수 시 결정)

#### Phase 6-2: 실시간 안정화 및 실사용 예외 차단

- 노이즈/무음 처리 및 `config.vad_threshold` 연동
- 버퍼 병목·타임라인 드리프트·백프레셔 제어
- 하드웨어 가속 강제 제어 시 오류 → 안전 폴백 보장
- `stt_mock_mode = False` 실측: 실제 한국어 발화 → 실시간 전사·화자분리 정확도 육안 검증

#### 의존성 추가 (`requirements.txt`)
- `openvino` / `openvino-genai`, `pyaudio`(또는 `sounddevice`), Whisper 추론 백엔드, `pyannote.audio` / `onnxruntime`
- ※ 현재 `requirements.txt`는 venv 스냅샷이라 위 STT 패키지 부재 — 6-1 착수 시 추가

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/test_stt.py -v   # 기존 Mock 회귀 + HW감지/추론 인터페이스 단위 테스트
.venv\Scripts\python -m pytest tests/ -v
```
- 실엔진 테스트는 가중치/하드웨어 의존 → 옵트인 마커로 분리(CI 기본 제외), 수동 실측으로 정확도 확인

---

### Phase 6-3: 완성도 확보 (실엔진 앱 통합 · 하드닝 · 이중 검증)  ※승인 대기

> Phase 6-1/6-2로 STT 실엔진은 **standalone(`stt_live_test.py`)에서 검증**되었으나, **풀 앱(run.bat) 안에서 실엔진으로 회의를 돌린 적은 없다**. 또한 설정 UI가 실엔진 파라미터를 제어하지 못하고, 멀티 화자 전역 일관성·첫 실행 UX 등 미완 영역이 남아 있다.
> Phase 6-3은 **Phase 7(배포) 진입 전 완성도를 확보**하는 단계로, 남은 작업을 모두 묶는다. 완료 기준 = ① 내(에이전트) 앱 통합 실측 통과 ② 사용자 실회의 검증 ③ 도출된 버그/사용성 개선 반영.

#### 6-3-1. 설정 UI ↔ 실엔진 배선 (현재 최대 갭)
| 대상 | 작업 |
|:---|:---|
| `prismflow/core/config.py` | `__post_init__`의 DB 오버라이드를 STT 설정까지 확장: `stt_mock_mode`, `whisper_model_name`(모델 크기 선택 → 실제 OV 모델 디렉토리 매핑), `stt_device`(가속 선택), `vad_threshold`. (claude_cli_cmd처럼 경량 sqlite 직접 조회) |
| `prismflow/ui_common/settings_ui.py` | ① **Mock 모드 토글**(체크박스) 추가 ② **HF 토큰 입력 필드** 추가(저장 시 DB+`HF_TOKEN` 반영) ③ 하드웨어 가속 옵션을 실제 디바이스(`AUTO/GPU/NPU/CPU`)에 정합 ④ 모델 크기↔로컬 모델 디렉토리 매핑/존재 표시 ⑤ 저장 시 `vad_threshold` 등 실엔진 설정도 `AppConfig`에 실시간 반영 |
| 매핑 규칙 | 모델 크기(tiny/base/small/medium/large-v3) → `whisper-{size}-int8-ov` 디렉토리. 미존재 시 안내(다음 항목). |

#### 6-3-2. 앱 통합 실측 (에이전트 자체 검증)
- `stt_mock_mode=False`로 `run.bat` 풀 구동: **실제 마이크 발화 → 실시간 전사 → Flow 다이어그램 → Chat Q&A(전사 맥락) → 종료 → 보고서**까지 일관 동작 육안 검증.
- 발견 버그(스레드/레이스/UI 멈춤/성능) 즉시 외과적 수정. 산출물: 통합 E2E 체크리스트.

#### 6-3-3. 멀티 화자 전역 일관성 (online diarization)
- 현재 발화 단위 독립 화자분리 → 회의 전체에서 화자 라벨 불일치. 발화 임베딩 누적·점증 클러스터링(spec `rho_update=0.1` 취지)으로 **전역 Speaker_XX 일관성** 확보. 과한 복잡도면 "발화 임베딩 코사인 매칭" 경량안으로 대체 검토.

#### 6-3-4. 첫 실행 UX · 에러 하드닝
- 모델 미존재 시: 크래시 대신 안내/다운로드 상태 표시(설정 또는 트레이 알림).
- STT 실패(장치/모델/토큰): UI 토스트로 사용자 가시화 + Mock 폴백 옵션.
- HF 토큰 부재: 단일화자 동작 안내.
- **[6-3-2 실측 도출] 콜드스타트 마이크 블라인드 윈도우 제거**: `_run_real_loop`이 모델 로드 완료 후 AudioCapture를 시작해 로드 구간(~10-30s, HF 온라인 체크 포함)의 초기 발화가 유실됨 → 마이크 캡처를 모델 로드와 병행/선행하고 로드 중 오디오 버퍼링 + "엔진 준비 중" 상태 표시.
- **[6-3-2 실측 도출] 실시간 전사 가시성**: 라이브 자막이 없어 STT 동작이 30초 Flow/최종 보고서로만 드러나 사용자가 "미작동"으로 오인 → 경량 실시간 전사 표시(또는 트레이/오버레이 상태) 검토.

#### 6-3-5. 이중 검증 & 개선 루프
- 사용자 실회의(다인) 테스트 → 전사 정확도/화자/지연/사용성 피드백 수집 → 우선순위화하여 반영.
- `vad_threshold`/모델 크기 실측 튜닝.

#### 6-3-6. 정리 & 회귀
- `tests/` 확장(설정 오버라이드·매핑 단위테스트), 전체 회귀 유지.
- `stt_live_test.py` 위치 정리(유지/도구화), Pretendard 폰트 누락 등 잔여 정리.

#### ReAct 검증
```bash
.venv\Scripts\python -m pytest tests/ -v
# 앱 통합은 run.bat 수동 E2E + STT_LIVE 옵트인 실측
```

> **Phase 7 (E2E 하드닝)** 은 STT 실엔진 구동 및 Claude CLI 세션 리밋/장애 상황에 대처하기 위한 통합 디버깅 및 예외 처리 고도화 단계이다.
> **Phase 8 (배포)** 로 오프라인 원클릭 패키징 및 배포 단계를 순연한다.

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

---

## 8. 상세 구현 설계서: Phase 7 & Phase 8

### Phase 7: E2E 통합 하네스, 디버깅 및 예외 하드닝 (E2E 특집)

#### 7-1. E2E 통합 테스트 하네스 (`tests/e2e_harness.py`) 구축
*   **목적**: 음성을 직접 내지 않고도 전체 라이프사이클을 반복 및 자동 시뮬레이션하며, 세션 한도 초과 등 다양한 예외 상황에서의 E2E 흐름을 검출하고 회귀를 방지하기 위함.
*   **구현 아키텍처 및 상세 설계**:
    *   **클래스 설계**: `E2EHarness` 클래스 제공.
        *   `__init__(self, config: AppConfig)`: 테스트용 DB 및 설정을 인자로 받아 초기화.
        *   `run_simulation(self, session_limit: bool = False) -> dict`: 10초 E2E 흐름 시뮬레이션을 수행하고, 수집된 결과(전사 개수, 생성된 Mermaid 코드, 채팅 응답, 생성된 보고서 경로 등)를 딕셔너리로 반환.
    *   **가상 오디오 공급 및 STT 가속화 (Mock STT)**:
        *   `stt_worker`를 Mocking하여 실제 마이크 대신 1~2초 간격으로 `MeetingContext`에 가상 발화(예: "안녕하세요", "회의를 시작하겠습니다", "Mermaid 다이어그램을 업데이트합니다")를 `add_transcript`를 통해 적재.
        *   실제 `RealTimeEngineWorker` 기동을 차단하거나 빠른 가상 이벤트 기동으로 교체하여 지연 없는 테스트 수행.
    *   **장애 조건 주입 (Claude CLI Session Limit)**:
        *   `ClaudeCLIController`의 `execute_command`와 `execute_command_stream` 메소드를 몽키패칭(Monkeypatch)하여 장애 상태 시뮬레이션.
        *   `session_limit=True` 주입 시, `Exit Code 1` 에러와 함께 `RuntimeError("Claude CLI execution failed: You've hit your session limit. Please try again after 1:10am.")`를 발생시킴.
        *   네트워크 끊김 상태나 API 키 미설정 상태도 옵션으로 주입할 수 있도록 설계.
    *   **E2E 흐름 10초 가속 루프**:
        1. **회의 기동**: `MeetingContext.start_meeting()` 및 `AppCoordinator` 인스턴스화.
        2. **STT 데이터 적재**: 1.5초 간격으로 3회 이상의 가상 발화 주입.
        3. **Flow Agent 갱신 주기 단축**: Flow Agent의 갱신 주기(`check_interval_sec`)를 2.0초로 단축 설정하여 시뮬레이션 중 1회 이상 Flow 생성 루프가 돌도록 유도.
        4. **Chat Q&A**: 5초 시점에 `chat_agent.send_query("핵심 주제 요약")`을 호출.
        5. **회의 종료**: 8초 시점에 `MeetingContext.end_meeting()`을 호출하여 회의 종료 시그널 방출 및 `ReportAgent` 구동 유도.
        6. **QApplication 이벤트 루프 가속**: `QApplication.processEvents()`와 `QTest.qWait()` 또는 PySide6 타이머 루프를 통해 UI 블로킹 없이 10초간의 백그라운드 스레드 및 시그널-슬롯 처리를 완벽하게 구동.
    *   **결과 및 자원 검증 (Assert Points)**:
        *   정상 동작 조건:
            *   DB `transcripts` 테이블에 발화가 정상 기록되었는가?
            *   `FlowUI` 및 `MeetingContext`에 Mermaid 다이어그램 코드가 정상 갱신되었는가?
            *   Chat Q&A 응답이 수신되었는가?
            *   회의 종료 후 `%USERPROFILE%/Documents/PrismFlow/Reports/...` 하위에 보고서 파일이 정상 생성 및 저장되었고 DB `summary`에 기록되었는가?
        *   장애 주입 동작 조건:
            *   `session limit` 발생 시 앱이 비정상 종료(Crash)되지 않는가?
            *   (7-2, 7-3 구현 후 연동) Fallback 모드로 전환되어, 로컬 룰베이스 Mermaid가 생성되었고 정적 Markdown 보고서가 안전하게 컴파일 및 저장되었는가?

#### 7-2. Claude CLI 에러 하드닝 및 로컬 Fallback(대체) 모드 구현
*   **배경**: Claude CLI가 세션 한도 초과나 네트워크 단절로 에러(Exit Code 1)를 낼 때, 앱이 크래시되거나 비정상 종료되는 현상을 막고, 제한 상황 하에서도 정상적으로 회의록을 생성 및 저장할 수 있는 안전장치 마련.
*   **설계 상세**:
    *   `cli_controller.py`에서 CLI 실행 실패 시 단순히 `RuntimeError`를 던지기 전에 stderr를 분석하여 세션 리밋(`You've hit your session limit`) 여부를 식별.
    *   **Fallback CLI Runner** 탑재: 세션 리밋 감지 시, 전역 설정(`AppConfig`) 혹은 세션 상태에 경고 플래그를 세우고 UI(상태바/QMessageBox)를 통해 사용자에게 경고 표출.
    *   **대체 응답 생성기(Fallback Generator)** 구현:
        *   **FlowAgent Fallback**: 전사된 발화록을 바탕으로 Mermaid 다이어그램 코드를 파이썬 내에서 규칙 기반(예: 화자 간 단순 발화 순서 시퀀스 차트)으로 생성하여 렌더링 유지.
        *   **ChatAgent Fallback**: 사용자의 채팅 입력 시 "현재 Claude CLI 사용량 한도에 도달하여 로컬 가상 비서 모드로 동작 중입니다. 최근 발화 요약: ..."와 같은 중립 응답 및 발화록에 기반한 로컬 매칭 답변 반환.
        *   **ReportAgent Fallback**: Opus 호출이 불가능할 경우, SQLite DB에서 읽어온 발화 내역을 시간/화자별로 정렬하여 깔끔한 정적 Markdown 텍스트 회의록으로 조합하고, `Documents/PrismFlow/Reports/` 경로에 자동 저장 후 로컬 뷰어로 오픈.

#### 7-3. WAV 원본 실시간 녹음 및 전사록 텍스트(.txt) 실시간 저장
*   **배경**: 법적/보안적 이유나 회의 아카이빙을 위해 원본 음성 데이터와 정적 텍스트 전사록을 디렉토리에 영구 보존해야 함.
*   **설계 상세**:
    *   **원본 음성 실시간 파일 저장**:
        *   회의 시작 시 `Documents/PrismFlow/Recordings/YYYY-MM-DD/meeting_{session_id}.wav` 파일을 생성.
        *   `AudioCapture`가 캡처하는 16kHz/Mono/Float32 오디오 스트림 전체를 VAD 분절 여부와 상관없이 백그라운드 스레드에서 `wave` 모듈을 이용해 실시간으로 WAV 파일에 계속해서 이어붙여 저장.
    *   **정적 전사록 실시간/종료 시 저장**:
        *   `Documents/PrismFlow/Transcripts/YYYY-MM-DD/transcript_{session_id}.txt` 생성.
        *   새로운 전사가 완료될 때마다 `[HH:MM:SS] [Speaker_XX]: 전사 텍스트` 형식으로 포맷팅하여 TXT 파일에 추가(UTF-8). 회의 종료 시 최종 플러시 수행.

#### 7-4. Flow 에이전트의 증분(Delta) 전사 업데이트 및 히스토리 저장
*   **배경**: 30초마다 전체 전사록을 다시 Claude CLI에 전달하면 입력 토큰량 누적으로 인해 하이쿠(Haiku) 모델임에도 성능 및 속도 지연(latency)이 심각해짐.
*   **설계 상세**:
    *   **증분 전사 업데이트 (Delta Context)**:
        *   `cli_controller.py`의 세션 재개(`--resume <UUID>`) 기능을 적극 활용.
        *   `FlowAgent`는 이전 30초 루프에서 마지막으로 읽은 전사록의 ID(또는 타임스탬프)를 저장.
        *   30초 주기 업데이트 시, 새로 누적된 **신규 전사록만** 추출하여 해당 세션의 컨텍스트에 추가 주입 프롬프트로 전달.
        *   **프롬프트 규칙**:
            *   `"이전 다이어그램을 바탕으로, 다음 추가된 대화 내용을 반영하여 Mermaid 다이어그램 코드의 내부를 업데이트하라: [추가된 30초분 텍스트]"`
            *   **이미지 맥락 통합**: 만약 I2T Agent에 의해 추출된 화면 텍스트 맥락(배경 정보)이 있다면, 프롬프트에 동적 삽입하여 해당 자료/이미지 맥락에 핵심적인 중요도를 부여해 다이어그램 노드에 반영되도록 유도.
            *   **신규 다이어그램 분기**: 대화의 흐름이나 주제 전환이 감지될 경우, 이전 구조도에서 이어붙이지 않고 다이어그램을 완전히 새로 교체하여 생성하도록 프롬프트 지시자 탑재.
    *   **구조도 히스토리(Flow History) 저장**:
        *   회의 주제 전환이나 대화 진행에 따라 다이어그램의 흐름이 변하므로, 유의미한 Mermaid 코드가 갱신될 때마다 타임스탬프와 함께 DB `flow_history` 테이블에 영구 저장.
        *   최종 리포트(.md) 컴파일 시 시간대별 흐름 변천사를 다중 섹션으로 포함하여 히스토리를 보존.

#### 7-5. I2T 에이전트 (Image-to-Text Agent) 신설 및 캡처 연동
*   **배경**: 화면 캡처(회의 발표 자료 등) 이미지 처리를 Flow Agent 루프와 결합하면 대기 시간이 과도하게 늘어남. 따라서 이미지를 텍스트 맥락으로 변환하는 독립된 `I2T Agent`를 구축하여 비동기로 화면 자료 정보를 DB에 정규화해 추출.
*   **설계 상세**:
    *   **비동기 이미지 텍스트 변환**:
        *   `ScreenTransitionDetector`에 의해 슬라이드 전환/화면 변화가 감지되어 새로운 이미지가 캡처되면, `I2TAgent`가 비동기 백그라운드 태스크로 구동됨.
        *   Claude CLI 멀티모달 입력 방식을 활용해 캡처 이미지 파일을 로컬 인자로 첨부하여 분석 지시. (예: `claude -p "이 발표 자료 슬라이드 이미지에서 핵심 의제, 핵심 단어, 표/텍스트 콘텐츠를 요약 추출하라" C:\path\to\captured.png`)
        *   추출된 텍스트 결과는 SQLite DB의 `screen_context` 테이블에 영구 적재.
    *   **추출 결과의 활용**:
        *   **교정 힌트 자동 주입**: 이미지에서 추출된 고유 대명사, 프로젝트 전문 용어들을 **사용자 정의 오인식 교정 사전(Auto-Correction Map)**의 정합성 향상을 위한 보정 힌트 리스트로 자동 추가.
        *   **Flow Agent 맥락 주입**: Flow Agent가 30초 주기로 전사록을 보낼 때, DB에서 읽은 최신 화면 텍스트 요약본을 배경 정보(Image Context Context)로 결합하여 프롬프트 품질 극대화.

#### 7-6. 사용자 오인식 교정(Auto-Correction Map) 및 자가 개선 루프
*   **배경**: 로컬 CPU/iGPU 사양 한계로 인해 딥러닝 Whisper/pyannote 가중치 모델 자체를 파인튜닝하는 자가 학습 루프는 실시간 구동이 불가능함. 대신 사용자가 UI에서 오인식 단어 및 화자명을 교정한 내역을 기반으로 학습/치환하는 실질적인 로컬 개선 루프를 구현.
*   **설계 상세**:
    *   **사용자 정의 교정 사전 (Custom Correction Dictionary)**:
        *   SQLite DB에 `correction_dictionary` 테이블 신설 (`pattern` -> `replacement`).
        *   사용자가 채팅창이나 리포트 피드백에서 오인식 단어(예: `"프리즘프로"` ➔ `"프리즘플로우"`)를 정정하면 DB 사전에 자동 등록.
        *   이후 STT 추론 결과물 텍스트가 확정되어 DB에 인서트되기 전에, 정규식을 이용하여 등록된 패턴들을 매칭해 실시간 교정 치환을 거친 뒤 DB에 영구 적재. (I2T Agent에 의해 수집된 슬라이드 키워드 리스트를 참조하여 오인식 유추 정밀도 향상).
    *   **화자 프로필 캐시 매핑**:
        *   특정 전역 화자(`Speaker_01` 등)의 실제 이름(예: `"홍길동 과장"`)을 사용자가 입력하면, 세션이 전환되어도 해당 화자의 고유 임베딩 벡터와 연동하여 자동으로 이름 매핑을 유지하는 프로필 캐시 레이어 구현.

#### 7-7. 실시간 전사 가시성(라이브 자막) 제공
*   **배경**: 실시간 전사 동작 여부가 시각적으로 보이지 않아 사용자가 오인하는 것을 방지하기 위해 `FlowUI` 하단 혹은 오버레이 창 영역에 실시간 자막 프리뷰 연동.
*   **설계 상세**:
    *   `FlowUI` 하단의 빈 영역 또는 툴팁 자막바에 최근 감지된 3개의 `(화자: 전사내용)` 자막을 스크롤하여 노출.
    *   `MeetingContext`에서 신규 발화 추가 시 이벤트를 수신하여 UI에 즉시 반영.

#### 7-8. 창 제어 버튼 시인성 개선 및 윈도우 스타일 정합
*   **배경**: 프레임리스 반투명 오버레이 창 우측 상단의 창 제어 버튼(최소화, 최대화, 닫기) 아이콘 기호가 글꼴 호환성이나 폰트 크기 및 색상 대비 부족으로 인해 렌더링되지 않거나 보이지 않는 현상 해결. 닫기 버튼과 일반 조작 버튼의 색상을 확실히 구분하여 시인성과 편의성을 보장.
*   **설계 상세**:
    *   **Segoe MDL2 Assets 글꼴 적용**: Windows 환경에서 기본으로 내장되어 있으며, UWP/Win11 표준 벡터 기호를 100% 지원하는 `Segoe MDL2 Assets` 폰트를 스타일시트의 `font-family` 1순위로 지정.
    *   **표준 기호 코드 매핑**:
        *   최소화(Minimize): `\uE921` (MDL2) / 폴백 `—` (Segoe UI 등)
        *   최대화(Maximize): `\uE922` (MDL2) / 폴백 `□`
        *   이전 크기로 복원(Restore): `\uE923` (MDL2) / 폴백 `❐`
        *   닫기(Close): `\uE8BB` (MDL2) / 폴백 `✕`
    *   **색상 대비 및 구분 강화**:
        *   평상시 기호 글자 색상을 어두운 투명 배경 위에 뚜렷이 대비되도록 밝은 회색/흰색(`color: #e2e8f0;`)으로 고정.
        *   최소화/최대화 버튼: hover 시 배경 `rgba(255, 255, 255, 0.12)`, 글자 흰색(`#ffffff`).
        *   닫기 버튼: 평소 글자색을 약간 붉은 계열 혹은 뚜렷하게 하고, hover 시 배경색 `#e81123`, 글자 흰색(`#ffffff`)으로 매핑하여 강한 색상 대비 제공.
        *   버튼의 폰트 사이즈를 `9px` 정도로 조정하여 Segoe MDL2 Assets 아이콘의 정밀도를 윈도우 스타일바와 정합시킴.


---

### Phase 8: 오프라인 원클릭 패키징 및 가중치 모델 통합 배포 (순연)

#### 8-1. pyannote 토큰리스 오프라인 로컬 로드 설계 상세
*   **원리**: pyannote 파이프라인이 기동 시 huggingface.co 허브를 참조하지 않도록, 허브의 `config.yaml` 설정을 로컬 리소스 디렉토리(`prismflow/resources/models/diarization/config.yaml`)에 고정 패키징하여 로컬 파일 경로를 직접 전달합니다.
*   **환경 변수 제어**:
    *   `os.environ["HF_HUB_OFFLINE"] = "1"` 설정을 활성화하여 모든 허깅페이스 서버 HEAD/GET API 접속 시도를 강제로 차단하고 오프라인 구동을 보장합니다.
    *   `os.environ["HF_HOME"] = os.path.join(self.config.models_dir, "hf_cache")` 설정을 통해 pyannote가 하위 의존 모델(`segmentation-3.0`, `wespeaker-voxceleb-resnet34-LM`)을 검색할 때 로컬 디렉토리 내부의 캐시 구조(`models/hf_cache/hub/models--...`)만 탐색하도록 격리합니다.
*   **로컬 캐시 이식**: 
    *   이미 개발 계정으로 동의 완료되어 캐싱된 모델 디렉토리 3종(`models--pyannote--segmentation-3.0`, `models--pyannote--speaker-diarization-3.1`, `models--pyannote--wespeaker-voxceleb-resnet34-LM`)을 개발자 PC의 `~/.cache/huggingface/hub/` 경로에서 통째로 추출하여 `prismflow/resources/models/hf_cache/hub/` 경로로 복사 및 패키징합니다.

#### 8-2. Portable Python 격리 패키지 구조 설계 상세
*   **이유**: PyInstaller 단일 파일 빌드는 기동 시 수 기가바이트(PyTorch, OpenVINO 등)의 압축 해제 오버헤드로 인해 Windows에서 극심한 기동 지연(10초 이상)과 임시 폴더 리소스 누수를 일으킵니다. 이를 극복하기 위해 압축 해제 지연이 없는 **Portable Python (Python Embeddable Package)** 구조를 설계합니다.
*   **디렉토리 트리 구성**:
    ```text
    PrismFlow_Release/
    ├── python-3.11.9-embed-amd64/     # 경량 임베디드 파이썬 런타임 (공식 zip 바이너리)
    │   ├── python.exe
    │   ├── python311.dll
    │   └── ...
    ├── site-packages/                 # pip install --target=. 으로 빌드된 완전 격리 의존성 패키지 풀
    ├── prismflow/                     # PrismFlow 메인 패키지 소스코드
    │   ├── resources/
    │   │   ├── models/                # Whisper(base/small) 및 pyannote hf_cache 가중치 번들
    │   │   └── Pretendard-Regular.ttf
    ├── main.py                        # 앱 진입점
    ├── AppLauncher.exe                # C++/C#으로 작성될 경량 런처 (콘솔 창 없이 임베디드 파이썬으로 main.py 기동)
    └── run.bat                        # 런타임 디버그용 배치 스크립트
    ```
*   **런처 작동 원리**:
    *   임베디드 파이썬 패키지의 `python311._pth` 파일을 수정하여 `./site-packages`와 `./`를 sys.path 검색 경로에 추가합니다.
    *   이를 통해 엔드유저 환경에 Python이나 환경변수가 없어도, Portable 폴더 내부의 격리된 런타임 및 가중치로 100% 즉시 오프라인 구동됩니다.

#### 8-3. Inno Setup 인스톨러 빌드 상세 ✅ DONE
*   **스크립트 작성 (`setup.iss`)**: Portable 폴더 트리 전체를 패키징하는 인스톨러 스크립트 작성 완료.
    *   **압축**: 대용량 모델 가중치(~3GB)를 포함한 배포본 크기 최소화를 위해 `lzma2/ultra64` 솔리드 압축 적용.
    *   **바로가기**: 시작 메뉴 및 바탕화면 바로가기(`launcher.bat` 기동)와 프로그램 추가/제거 레지스트리 자동 ### Phase 18: Mermaid 흐름도 실시간 줌/팬, 작업 표시줄 활성화, 백그라운드 숨김 및 심볼릭 아이콘 통합 구현

> **배경**: 
> 1. 실시간 회의 중 누적되는 전사록을 기반으로 Mermaid 다이어그램(Flow)이 점차 확장되거나 상세해짐에 따라, 전체 화면에 그래프가 가득 차면서 글씨가 축소되거나 일부 노드를 읽기 어려운 UX 피드백이 발생했습니다. 이를 해결하기 위해 사용자가 웹 캔버스 영역 내에서 **마우스 휠 줌(Zoom)**, **마우스 좌클릭 드래그 팬(Pan)**을 수행하게 하고, **유리(Glassmorphic) 스타일 줌 툴바 UI**를 우측 하단에 제공합니다.
> 2. 추가적으로 메인 오버레이 콘솔이 활성화될 때 **작업 표시줄(Taskbar)**에 표시되도록 하고, 창을 닫을 때는 프로그램이 종료되지 않고 **작업 표시줄에서만 사라지며 백그라운드(트레이 상주)**로 숨겨지도록 합니다. 또한 기본 컴퓨터 아이콘 대신 PrismFlow 전용 **심볼릭 아이콘**을 적용하고, 회의 중일 때는 트레이 아이콘에 동적으로 빨간 녹음 점이 덧그려지도록 통합합니다.

#### 핵심 과제 및 설계 사양

1. **오프라인 라이브러리 탑재**
   - 인터넷 연결 없이 작동해야 하는 배포 규격(Phase 8)에 맞추어 `svg-pan-zoom.min.js` (~20KB) 라이브러리를 로컬 리소스 디렉토리 `prismflow/agents/flow/resources/`에 번들로 배치하고 Git 추적 대상에 포함합니다.
   - `mermaid_html.py`의 `get_mermaid_html()`에서 `__SVG_PAN_ZOOM_JS_URL__` 플레이스홀더를 통해 로컬 URL을 동적으로 주입합니다.

2. **SVG 레이아웃 CSS 충돌 제거**
   - 기존의 `#diagram-container svg`에 지정된 `width: 100% !important; height: auto !important; max-width: 100% !important;` 스타일은 `svg-pan-zoom`이 계산하는 인라인 transform 및 viewBox 제어 로직과 강하게 충돌하므로 제거하고 구조를 리팩토링합니다.
   - `#diagram-container`는 `overflow: hidden`으로 설정하여 브라우저 기본 스크롤바를 숨기고 줌/팬 캔버스 영역으로 전환합니다.

3. **다크 Glassmorphism 줌 컨트롤 툴바 UI**
   - HTML/CSS를 통해 웹뷰 우측 하단에 `position: absolute; bottom: 16px; right: 16px; z-index: 100;` 형태로 반투명 유리 컨트롤 바를 띄웁니다.
   - **디자인 토큰**: `background: rgba(30, 30, 35, 0.65); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; display: flex; gap: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);`
   - **버튼 구성**:
     - ➕ 확대 (Zoom In) -> `panZoomInstance.zoomIn()`
     - ➖ 축소 (Zoom Out) -> `panZoomInstance.zoomOut()`
     - 🎯 중앙 맞춤 (Fit & Center) -> `panZoomInstance.fit(); panZoomInstance.center();`
     - 🔄 원래 비율 (Reset Zoom 1:1) -> `panZoomInstance.reset();`
   - 버튼 호버(hover) 시 은은한 배경 전환(`rgba(255,255,255,0.08)`) 및 청록색 강조(`color: #5eead4`) 효과를 적용합니다.

4. **다이어그램 갱신 시 상태 보존 (State Preservation) 알고리즘**
   - 8초/15초 주기로 다이어그램 코드가 갱신될 때마다 전체 SVG가 재렌더링되는데, 이때 줌 레벨과 화면의 중심 위치가 매번 초기화되면 사용성이 극단적으로 저하됩니다.
   - 이를 방지하기 위해 `updateDiagram(mermaidCode)`이 실행될 때 다음 4단계 복원 로직을 순수 JavaScript로 구현합니다.
     - **백업**: 새 코드를 받으면 기존 `panZoomInstance`가 존재하는 경우 `lastZoom = panZoomInstance.getZoom(); lastPan = panZoomInstance.getPan();`으로 상태를 저장하고 `panZoomInstance.destroy()`로 메모리를 정리합니다.
     - **렌더링**: `mermaid.run()`을 수행해 DOM에 새 SVG 렌더링합니다.
     - **재구성**: 렌더링된 새 SVG 요소를 바탕으로 `svgPanZoom`을 다시 호출하여 인스턴스를 새롭게 생성합니다.
     - **복원**: `lastZoom`과 `lastPan`이 백업되어 있다면 이를 즉시 신규 인스턴에 `panZoomInstance.zoom(lastZoom)` 및 `panZoomInstance.pan(lastPan)`으로 복구합니다. (최초 실행 시에는 복원 없이 `fit: true, center: true`로 중앙에 배치합니다).

5. **프리미엄 앱 로고 이미지 생성 및 리소스 배치**
   - `generate_image` 도구를 이용하여 PrismFlow 소프트웨어의 정체성(투명하고 빛나는 그라데이션 기하학 프리즘 로고)에 어울리는 심볼릭한 `app_icon.png` 이미지를 생성합니다.
   - 생성된 파일을 `prismflow/resources/app_icon.png` 위치에 복사하여 패키징 리소스에 통합합니다.

6. **작업 표시줄(Taskbar) 창 노출 및 아이콘 연동**
   - `TranslucentOverlay` 클래스의 `setWindowFlags()` 설정에서 창을 작업 표시줄에서 숨기던 `Qt.Tool` 플래그를 제거하고 `Qt.Window | Qt.FramelessWindowHint` 조합으로 수정하여, 창이 화면에 노출될 때 윈도우 작업 표시줄에도 아이콘이 정상 노출되도록 제어합니다.
   - `setWindowIcon(QIcon("app_icon.png"))`를 통해 창의 시스템 아이콘을 설정함으로써 작업 표시줄에 고유한 심볼릭 아이콘이 매핑되도록 합니다.

7. **창 닫기 시 트레이 최소화(백그라운드 상주) 구현**
   - 사용자가 콘솔 창의 닫기(X) 버튼을 누르거나 창을 닫을 때 프로그램이 완전히 종료되는 것을 막기 위해, `TranslucentOverlay.closeEvent()`를 재정의합니다.
   - `MeetingContext` 내부 `__init__`에 `self.is_quitting = False` 플래그를 추가합니다.
   - `closeEvent()` 수신 시, `self.context.is_quitting`이 `True`가 아니라면 `event.ignore()`를 호출하여 창 소멸을 막고 `self.hide()`를 수행하여 작업 표시줄 및 화면에서 창을 숨깁니다.
   - 시스템 트레이의 "종료" 메뉴(`SystemTrayManager.exit_app()`) 호출 시에는 `self.context.is_quitting = True`를 먼저 할당하고 `QApplication.quit()`를 트리거하여 프로세스가 실제 완전 종료되도록 연결합니다.

8. **트레이 아이콘 변경 및 동적 녹음 점 표시**
   - `SystemTrayManager`의 기본 트레이 아이콘을 컴퓨터 기본 아이콘에서 `app_icon.png`로 교체합니다.
   - 회의 중일 때(`_on_meeting_started`) 트레이 아이콘을 변경할 때, `QPainter`를 이용하여 `app_icon.png` 픽스맵 이미지의 우측 하단 구석에 작은 빨간색 점(녹음 및 동작 중 상태)을 동적으로 덧그려 `active_icon`을 생성하고 적용합니다. 회의가 끝나면 원래 `app_icon.png`로 복구하여 직관적인 상태 모니터링을 지원합니다.

#### 개발 범위

| 항목 | 대상 파일 | 작업 내용 |
|:---|:---|:---|
| **18-1** 오프라인 라이브러리 번들 추가 | `prismflow/agents/flow/resources/svg-pan-zoom.min.js` [NEW] | jsdelivr CDN에서 `svg-pan-zoom@3.6.1` 공식 배포 minified 버전을 다운로드하여 리소스 폴더에 번들 저장하고, 릴리즈 추적(Git)에 등록합니다. |
| **18-2** 줌 툴바 UI 및 API 배선 | `prismflow/agents/flow/mermaid_html.py` | HTML 템플릿에 `__SVG_PAN_ZOOM_JS_URL__` 스크립트 태그 추가. absolute 포지셔닝의 Glassmorphic 줌 툴바(➕, ➖, 🎯, 🔄) 스타일 및 HTML 엘리먼트 추가. 각 버튼 클릭 이벤트 리스너에서 `svg-pan-zoom` 인스턴스의 API를 호출하는 JS 배선 완료. |
| **18-3** 줌/팬 상태 보존 로직 | `prismflow/agents/flow/mermaid_html.py` | `updateDiagram()` 실행 시 기존 인스턴스 소멸 전 줌/팬 값을 백업 변수에 기록하고, 신규 렌더 완료 후 이를 재주입하여 부드러운 전이를 보장하는 복원 스크립트 작성. |
| **18-4** SVG 레이아웃 스타일 충돌 리팩토링 | `prismflow/agents/flow/mermaid_html.py` | `#diagram-container`의 `overflow`를 `hidden`으로 변경, `#diagram-container svg`의 인라인 크기 강제 스타일(width/max-width/height/max-height)을 제거하여 라이브러리가 크기 조정을 주도하도록 스타일 충돌 해소. |
| **18-5** 프리미엄 앱 로고 생성 및 배치 | `prismflow/resources/app_icon.png` [NEW] | `generate_image`를 통해 네온 그라데이션 프리즘 로고를 생성하고 `prismflow/resources/app_icon.png`에 저장. |
| **18-6** 작업 표시줄 창 노출 및 아이콘 연동 | `prismflow/ui_common/overlay.py` | `setWindowFlags()`에서 `Qt.Tool` 플래그 제거, `setWindowIcon()`을 통한 `app_icon.png` 경로 지정. |
| **18-7** 창 닫기 시 트레이 최소화 가드 | `prismflow/core/context.py`, `prismflow/ui_common/overlay.py`, `prismflow/ui_common/tray.py` | `MeetingContext`에 `is_quitting` 추가, `overlay.py` `closeEvent`에서 `is_quitting` 판별에 따라 ignore & hide 처리 분기, `tray.py` `exit_app`에서 `is_quitting = True` 설정. |
| **18-8** 트레이 아이콘 및 동적 녹음 점 표시 | `prismflow/ui_common/tray.py` | `SystemTrayManager` 아이콘을 `app_icon.png`로 변경. 회의 진행 중 시그널 수신 시 `QPainter`를 이용하여 우측 하단에 빨간 원을 덧그려 동적으로 `active_icon`을 세팅. |
| **18-9** 회귀 및 검증 | `tests/test_flow.py` | `test_flow.py`에서 `svg-pan-zoom.min.js` 번들 리소스 파일의 존재 확인 및 HTML 템플릿 내 경로 매핑 치환 로직 유효성을 검증하는 테스트 추가. 전체 `pytest tests/` 통과 보장. |

#### 구현 순서(권장)
18-1(리소스 추가) & 18-5(아이콘 생성) → 18-4(CSS 충돌 해소) → 18-2(줌 툴바 UI) → 18-3(줌/팬 상태 보존) → 18-6(작업표시줄 노출) → 18-7(닫기 숨김 및 종료 배선) → 18-8(트레이 아이콘 및 동적 녹음 점) → 18-9(회귀 검증).

#### 비-목표(Non-goal)
*   사용자의 회의 전체 창 돋보기가 아님: 오직 Flow(Mermaid) 웹 캔버스 영역 내에서의 SVG 줌/팬 및 돋보기 툴바 기능만 다룹니다.
*   Mermaid 노드 자체의 텍스트 편집 기능은 지원하지 않습니다.

#### ReAct 검증
*   단위/회귀: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q` (신규 리소스/템플릿 테스트 포함 100% 통과).
*   수동 E2E:
    - 앱 구동 시 작업 표시줄에 PrismFlow 아이콘(`app_icon.png`)이 정상 표시되는지 확인.
    - 다이어그램 영역에서 휠 줌 및 드래그 팬이 부드럽게 작동하고, 우측 하단 Glassmorphic 돋보기 툴바의 버튼(➕/➖/🎯/🔄)이 잘 기능하는지 확인.
    - 발화 업데이트 갱신(8초/15초) 시 줌/팬 뷰 좌표 구도가 풀리지 않고 잘 유지되는지 검증.
    - 메인 콘솔의 우상단 닫기(X) 버튼이나 Alt+F4를 누를 때, 프로그램이 죽지 않고 작업 표시줄과 화면에서 사라지며 트레이에만 남는지 확인.
    - 시스템 트레이 메뉴의 "회의 맵 표시"나 "AI 채팅 표시"를 클릭할 때 창이 다시 작업 표시줄과 화면에 정상적으로 복원되는지 확인.
    - 회의가 시작될 때 트레이 아이콘의 우측 하단에 빨간 녹음 중 점이 나타나고, 회의가 종료되면 빨간 점이 사라지는지 확인.
    - 시스템 트레이에서 "종료" 메뉴를 선택했을 때 프로그램이 정상적으로 완전히 꺼지는지(프로세스 종료) 검증..
    *   `tests/test_flow.py`에 증분 업데이트 프롬프트 크기가 단축되었는지 및 최근 활성 노드 Context 파싱이 올바르게 수행되는지 검증하는 테스트 케이스를 생성합니다.
*   **벤치마크 테스트**:
    *   최적화 적용 전과 후의 1회 발화당 화자 식별 소요 시간(ms) 및 Flow Agent 호출 1회당 전송된 입력 토큰 수를 측정하여 50% 성능 향상을 숫자로 증명합니다.


### 9-4. Chat Agent CLI 커넥션 에러 디버깅 및 Q&A 성능 최적화
*   **에러 디버깅 및 원인 분석**:
    *   기존 Chat Agent는 3분 주기로 신규 전사록을 백그라운드에서 세션에 누적하는 `IngestWorker`와 사용자가 필요시 기동하는 `ChatQNAWorker`가 단일 Claude CLI 세션(`chat-session-{id}`)을 공유했습니다.
    *   `threading.Lock`으로 Python 단의 동기화는 이루어졌으나, CLI의 비동기 백그라운드 실행 중 타임아웃, 프로세스 좀비화, 혹은 CLI 세션 파일(Anthropic CLI 세션 저장소) 수준의 물리적 동시 락 경합이 발생하여 순시 커넥션 실패(에러 코드 1)가 빈번히 보고되었습니다.
    *   또한 백그라운드 주입 스레드가 동작하는 동안 사용자가 질문을 던질 경우, 락 획득을 위해 최소 수 초에서 수십 초간 대기해야 해 사용자 반응성이 크게 저하되었습니다.
*   **최적화 설계**:
    *   **백그라운드 주기적 주입 폐지 (Ingestion-free One-shot Q&A)**:
        *   3분 간격의 무거운 백그라운드 주입 스레드(`IngestWorker`)를 완전히 폐지합니다. 이로 인해 불필요한 백그라운드 CLI 프로세스 기동 횟수가 90% 이상 차감되며 PC 자원(CPU) 및 세션 락 오류 가능성이 원천 제거됩니다.
    *   **슬라이딩 RAG 컨텍스트 및 원샷 호출**:
        *   사용자가 질문할 때에만 최근 10~15분 분량의 전사록(최대 100~150개 발화) 및 현재 회의의 요약 정보(Mermaid 다이어그램 구조)를 즉석에서 융합해 단일 유저 프롬프트로 주입합니다.
        *   질문 시 매번 단발성 쿼리 형태로 호출하거나 고유한 UUID를 기반으로 락 경합이 없는 단일 세션을 생성하여 병렬 잠금 간섭을 원천 차단합니다.
    *   **지수 백오프(Exponential Backoff) 재시도 메커니즘**:
        *   `cli_controller.py`의 CLI 호출 실행기(`execute_command` 및 `execute_command_stream`) 내부에 API 순시 실패 또는 커넥션 끊김 감지 시 최대 3회 재시도(지연: 1초, 2초, 4초) 로직을 통합하여 네트워크 회복 탄력성을 강화합니다.
*   **정량적 목표**:
    *   불필요한 백그라운드 프로세스 기동량 90% 이상 절감 및 세션 잠금 대기 시간 0으로 수렴. Q&A 질문 시 순시 커넥션 에러 발생율을 0%에 수렴하게 제어합니다.

---

## 10. 상세 구현 설계서: Phase 10 (에이전트 상태 대시보드 & 오버레이 UX) — ✅ 완료(2026-06-21)

### 10-1. 에이전트 상태 집계 허브 (`core/agent_status.py`)
*   **설계**: 5개 에이전트(STT·Flow·Chat·i2t·Report)의 4단계 상태(IDLE/OK/WORKING/ERROR)를 한 곳에서 보관하고, 변경 시에만 `status_changed(key, state, detail)` 신호로 **푸시**(폴링 0)하는 `AgentStatusHub(QObject)`를 둔다. 동일 (상태, 상세) 중복은 방출하지 않는다.
*   **목표**: 에이전트와 UI를 느슨하게 결합(decouple)하여 오버헤드 0 + 테스트 용이성 확보.

### 10-2. 상태 패널 / 녹음 인디케이터 (`ui_common/status_panel.py`, `ui_common/indicators.py`)
*   **설계**: 색점 + 이름 + 상세 뱃지로 각 에이전트 상태를 표시(`AgentStatusPanel`). `RecordingIndicator`는 `● 녹음 중` 빨간 점멸을 베이스 오버레이에 탑재해 두 반투명창 모두에 노출.

### 10-3. FlowUI 4:1:1 분할 + 코디네이터 신호 배선
*   **설계**: FlowUI 세로를 Mermaid(4) : 확정 전사 기록(1) : 상태 패널(1)로 재구성. 신규 신호(`FlowAgent.analysis_started/analysis_failed`, `ChatAgent.question_received`)를 추가하고, 코디네이터가 모든 에이전트 상태를 허브로 중계.

### 10-4. (안정화) 싱글톤 시그널 누수 = 세그폴트 근본 해결
*   **문제**: `AppCoordinator`/`ChatAgent`가 싱글톤 `MeetingContext` 시그널을 `__init__`에서 구독하지만 `cleanup()`에서 끊지 않아, 소멸된 '좀비' 객체가 다음 회의 신호에 반응해 STT(PyAudio)/Flow 스레드를 중복 생성 → access violation.
*   **해결**: 각 `cleanup()`에서 컨텍스트 시그널을 명시적으로 disconnect + conftest가 매 테스트마다 시그널 슬롯을 비워 백스톱. **불변식**: "새 컨텍스트-시그널 구독자를 추가하면 반드시 cleanup에서 끊는다."

---

## 11. 상세 구현 설계서: Phase 11 (실제 실행 UX 하드닝 · 도구화 · 공개) — ✅ 완료(2026-06-21)

> 사용자가 실제 앱(`main.py`)을 구동하며 캡처와 함께 던진 피드백을, 검증 → 계획 → 실행 → **실측 증명**의 루프로 단계별 커밋. (커밋 단위 Phase A~F)

### 11-A. 오버레이 UX 정비
*   녹음 인디케이터를 좌상단 → 우상단 컨트롤 묶음(최소화 버튼 옆)으로 이동. **'항상 위(StaysOnTop)' 해제**. **투명도 슬라이더**(20~100%) 추가. FlowUI 상태 패널 최대 높이 제한으로 흐름도가 세로 확대분을 흡수.
*   **투명도 버그 수정**: `paintEvent` 배경 alpha 180→255로 변경 → 슬라이더를 끝까지 올리면 완전 불투명(비침 0%). windowOpacity가 투명도의 단일 소스.

### 11-B. Flow 실시간성 (`FlowAgent._should_trigger`)
*   30초 고정 틱을 순수함수 3-way 트리거로 교체 — 최초 즉시 / 주제 전환(발화 ≥3 누적) 시 8초 바닥만 지나면 즉시 / 정기 15초. 주제 전환 지연 ~30초 → ~8초.

### 11-C. CLI 디버그 로그 창 (`core/cli_activity.py`, `ui_common/cli_log_window.py`)
*   백그라운드 에이전트가 Claude CLI에 주고받는 프롬프트/응답을 색 뱃지로 실시간 표시(개발용). 요청은 호출 즉시(`record_request`), 응답은 완료 시(`record_response`) 분리 방출.

### 11-D/E. 회의 Q&A 도구 통합 + 창 이름/레이아웃
*   모드 토글 분리안을 폐기하고 **단일 회의 Q&A 흐름으로 통합**: 회의 맥락 주입 + 웹 검색·작업 폴더 파일 도구(읽기/쓰기/수정/이동)를 함께 사용, 작업 폴더는 📁 버튼으로 지정(DB `settings.workspace_dir`).
*   창 이름 명기: `PrismFlow Agent`(흐름도, 좌상단 떠있는 라벨)·`PrismFlow Chat Agent`. 흐름도 블록이 세로 ~90%, 상태는 한 줄.
*   **세션 'already in use' 수정**: 세션을 오염시키던 프로브 제거 → `cli_controller._created_sessions`로 결정(최초 `--session-id`, 이후 `--resume`) + 충돌 시 폴백.

### 11-F. 남은 항목 + 공개
*   **i2t 화면 용어집 STT 교정**(`core/glossary.py`): PPT 슬라이드 텍스트(COM) → `screen_glossary` 테이블 → 같은 문자 체계·유사도 0.8↑ 보수적 근접 보정(과교정 방지).
*   **회의종료 프리즈 수정**: `FlowAgent.stop(wait_ms)` 바운드 대기 + 코디네이터 백그라운드 배수(drain). **앱 종료 즉시화**: `cli_controller.terminate_all()`로 in-flight 서브프로세스 사살.
*   **폰트 경고 필터**(`main._install_qt_message_filter`).
*   **공개**: MIT LICENSE + README(한/영) + GitHub `simturong/PrismFlow` 전체 공개. (조기 커밋된 `.venv` 히스토리는 `git filter-branch`로 제거 후 푸시.)


---

## 10. 상세 구현 설계서: Phase 12 (프로젝트 구조 최적화 및 불필요 문서 정리)

### 12-1. 불필요한 Handoff 문서 및 레거시 폴더/파일 일괄 영구 삭제
*   **목적**: 프로젝트 내 불필요하거나 중복되는 인계(Handoff) 파일 및 임시 폴더를 일괄 정리하여 소스 트리 및 프로젝트 제어권을 확보합니다.
*   **대상 파일 및 폴더**:
    *   `docs/` 디렉토리 내: `handoff_2026-06-21_phase10.md`, `handoff_2026-06-21_phase11.md`, `phase9_benchmark_report.md` (중복 보고서)
    *   `artifacts/` 폴더 전체 (인계 전용 레거시 폴더)
*   **처리 방식**: 모든 대상 파일과 폴더를 영구 삭제하여 소스 트리를 완전히 정제합니다.

### 12-2. AI 에이전트 Handoff 문서 생성 차단 및 커스텀 룰 단일 파일 통합
*   **배경**: AI 에이전트(Antigravity 등)가 세션 정리 스킬(`Handoff`)을 통해 인계 문서 생성을 자동 시도하지 못하도록 제한하고, 분산되어 있던 프로젝트 수칙을 루트의 `agent.md`로 일원화합니다.
*   **수칙 반영 및 구조 단일화**:
    *   기존 `.agents/AGENTS.md` 파일과 `.agents/` 디렉토리를 완전히 영구 삭제합니다.
    *   기존 `.agents/AGENTS.md`에 있던 구현계획서 협의/상세화 의무 및 작업 상태판 관리 규칙 등의 프로젝트 커스텀 룰을 루트의 `agent.md`에 유실 없이 병합하여 통합 관리합니다.
    *   에이전트가 향후 세션 전환이나 마감 시 `Handoff` 스킬 등을 통해 인계 파일(`handoff_*.md`)을 생성하거나 관리하지 않도록 `agent.md`에 명시하고, 또한 임의로 `.agents/` 폴더나 `AGENTS.md`를 생성하는 것을 전면 금지하는 강력한 가이드를 주입합니다.
    *   에이전트는 오직 `docs/implementation_plan.md`, `docs/task.md`, `docs/history.md` 및 루트의 `agent.md`만을 단계별 정본 및 지침서로 활용합니다.

### 12-3. 검증 계획
*   **구조 정리 검증**: 대상 Handoff 파일들과 `.agents/` 디렉토리가 모두 완전하게 삭제되었으며 `artifacts/` 폴더가 비어 있고, 루트의 `agent.md`에 규칙이 안전하게 통합되었는지 확인합니다.
*   **회귀 테스트 검증**: 정리 작업 도중 기존 소스 코드에 부작용이 없음을 검증하기 위해 PyTest 회귀 테스트를 실행합니다.
    *   검증 명령어: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`


---

## 11. 상세 구현 설계서: Phase 13 (세션별 출력 폴더 구조화, UI 하드닝 및 회의 제어 기능 보강)

### 13-1. 세션별 단일 폴더 출력 구조화
*   **배경 및 문제점**:
    *   기존에는 녹음 파일(`Recordings/`), 전사 파일(`Transcripts/`), 최종 회의록(`Reports/`)이 서로 다른 하위 디렉토리에 분산 저장되어, 단일 회의 세션의 결과물들을 하나의 폴더에서 직관적으로 관리하기 어려웠습니다.
*   **구조 최적화**:
    *   설정된 출력 폴더(`output_dir`) 하위에 회의 시작 시 고유한 세션 ID 폴더(`output_dir/{session_id}/`)를 동적 생성합니다.
    *   **단일 세션 내 3대 파일 구성**:
        1.  실시간 녹음 파일: `output_dir/{session_id}/meeting_{session_id}.wav`
        2.  실시간 전사록 파일: `output_dir/{session_id}/transcript_{session_id}.txt`
        3.  최종 회의록 리포트: `output_dir/{session_id}/report_{session_id}.md`
    *   이로 인해 하나의 회의에 대한 모든 원본 및 산출물 파일이 하나의 폴더에 모이도록 개편합니다.

### 13-2. AppConfig 및 SQLite settings 배선
*   **환경 설정 키 추가**:
    *   `AppConfig`에 `output_dir` (기본값: 프로젝트 폴더 내 `output/`) 변수를 추가합니다.
    *   SQLite `settings` 테이블의 `output_dir` 키가 존재할 경우, 기동 시 이 값으로 `AppConfig.output_dir`을 동적 오버라이드합니다.
*   **세션 폴더 생성 자동화**:
    *   `MeetingContext`에서 세션 시작(`start_session`) 시 `output_dir/{session_id}/` 경로를 `os.makedirs(..., exist_ok=True)`를 통해 미리 안전하게 확보하고 다른 에이전트가 이 경로를 읽어 파일을 적재하도록 리팩토링합니다.

### 13-3. SettingsDialog UI 출력 경로 브라우저 추가
*   **UI 구성**:
    *   트레이 우클릭 "설정" 클릭 시 호출되는 `SettingsDialog` 하단에 **출력 폴더 설정 레이아웃**을 신설합니다.
    *   **QLineEdit**: 현재 설정된 `output_dir` 절대 경로를 표시 (읽기 전용 또는 직접 입력).
    *   **QPushButton (찾기)**: `QFileDialog.getExistingDirectory()`를 연동하여 사용자가 GUI를 통해 원하는 출력 루트 디렉토리를 지정할 수 있도록 돕습니다.
*   **설정 저장 및 즉시 반영**:
    *   "저장" 버튼 클릭 시, 선택된 새 경로를 DB `settings` 테이블에 `output_dir` 키로 영구 저장하고 `AppConfig`에 즉시 동적 반영합니다.

### 13-4. 오버레이 창 테두리(Border) 렌더링 추가
*   **디자인 요구사항**:
    *   현재 `TranslucentOverlay` 창의 경계 구분이 다소 불명확하여, 기존 프로그램(Chat UI 요소)과 정합되는 깔끔한 은은한 테두리를 추가합니다.
*   **구현 설계**:
    *   `prismflow/ui_common/overlay.py`의 `paintEvent`를 수정하여 `QPainter`를 기동할 때 외곽 테두리를 함께 그리도록 설계합니다.
    *   테두리 스타일: 굵기 `1px`, 색상 `QColor(255, 255, 255, 30)` (약 12% 투명도의 은은한 화이트). `paintEvent` 렌더링 시 테두리가 프레임 바깥으로 미세하게 잘려 나가지 않도록 `self.rect().adjusted(1, 1, -1, -1)` 영역에 둥근 모서리 사각형(`drawRoundedRect`)을 적용합니다.

### 13-5. 실시간 전사(Interim) 수신 및 자막창 높이 2배 확대
*   **전사 기록창 확대**:
    *   `flow_ui.py` 내의 `self.transcript_view` (QTextBrowser) 최대 높이를 기존 `40px`에서 `85px` (약 2.1배)로 확대하여 시인성을 높이고 줄바꿈된 발화록을 안정적으로 볼 수 있게 합니다.
*   **실시간 전사(Interim) 피드 배선**:
    *   `MeetingContext`에 임시/중간 전사 시그널 `partial_transcript_updated = Signal(str, str)` (speaker, text)를 신설합니다.
    *   `stt_agent.py` (`RealTimeEngineWorker`)의 `_run_vad_segmented_loop` 내에서 발화 진행 중(`in_speech == True`)일 때, 약 0.5초 분량(예: `0.5 * sr` 샘플)의 오디오 청크가 누적될 때마다 백그라운드 스레드에서 가볍게 Whisper 전사(`_process_interim_inference(audio)`)를 단독 수행하여 중간 텍스트를 실시간으로 추출하고 이를 신설된 시그널로 방출합니다. (임시 텍스트이므로 DB나 context의 확정 리스트에는 저장하지 않습니다.)
    *   `FlowUI`는 이 중간 전사 신호를 구독하여 하단 전사 뷰에 실시간으로 작성 중인 문구(예: `[말하는 중...] {텍스트}`)를 표출하고, 최종 VAD endpoint 감지로 발화가 확정되면 이 임시 자막을 지우고 확정된 줄(`add_transcript`)로 교체합니다.

### 13-6. 회의 일시중지(중지) 및 정지(종료) 기능 연동
*   **회의 제어 상태 추가**:
    *   `MeetingContext`에 `is_meeting_paused` 상태 변수와 `meeting_paused = Signal(bool)` 시그널을 추가합니다.
*   **오버레이 UI 일시중지 및 정지 버튼 신설**:
    *   `FlowUI` 및 `ChatUI` 우상단 컨트롤 바(최소화 버튼 바로 왼쪽)에 **회의 일시중지/재개 토글 버튼(`||` / `▶` 기호)**과 **회의 정지(종료) 버튼(`■` 기호)**을 신설합니다.
    *   **일시중지 버튼**: 클릭 시 `MeetingContext.toggle_pause()`가 실행되어 제어 상태가 동기화되며, 버튼의 외관이 `||` (중지) 또는 `▶` (재개)로 동적 토글됩니다. 또한 `status_hub`를 통해 `"stt"` 상태를 `OK(회의중)` / `IDLE(일시중지됨)`로 연동 표출합니다.
    *   **정지 버튼**: 클릭 시 현재 진행 중인 회의 세션을 최종 종료하고 보고서 생성을 즉시 트리거하는 `AppCoordinator`의 `stop_meeting()` 흐름(또는 트레이 메뉴의 회의 종료와 동일한 핸들러)을 호출합니다. 이로써 사용자가 시스템 트레이를 거치지 않고도 오버레이 상에서 직관적으로 회의를 닫고 최종 마크다운 리포트를 띄울 수 있습니다.
    *   회의가 일시중지 상태인 경우, `stt_agent.py`의 실시간 오디오 루프는 유입되는 마이크 오디오 청크를 폐기하고 추론 및 파일 기록 동작을 일시 대기합니다.
    *   트레이 메뉴(`tray.py`)에도 "회의 일시중지" / "회의 재개" 메뉴를 추가하여 연동합니다.

### 13-7. Mermaid 한도 초과 판정 버그 해결 및 화자(Speaker) 표시 배제
*   **CLI 사용량 한도 초과(Session Limited) 판정 오판 해결**:
    *   **원인**: 기존에는 에러 메시지에 `"reset"`이 들어가면 `_session_limited = True`로 오판하는 로직이 있어, 네트워크 상태로 인한 단순 `connection reset` 발생 시에도 사용량 한도 초과 상태로 간주되어 로컬 대체 모드로 고착되었습니다.
    *   **해결책**:
        1. `cli_controller.py` 내의 세션 리밋 판정 키워드를 `"session limit"`, `"rate limit"` 등으로 엄격하게 좁혀 단순 네트워크 `reset`으로 인한 오판을 방어합니다.
        2. 회의 시작(`start_session` 및 코디네이터의 `_on_meeting_started`) 시 `self.cli_controller.set_session_limited(False)`를 명시적으로 호출해 세션 리밋 상태를 완벽히 매번 초기화합니다.
*   **다이어그램 화자 표시 배제**:
    *   `flow_agent.py` 내 프롬프트에서 *"화자 정보를 노드 텍스트에 간략히 표기해 주세요 (Speaker_XX)"*라는 규칙을 완전히 제거하고, *"화자 식별자(Speaker_XX)는 노드 및 다이어그램에 포함하지 말고, 오직 논의 흐름과 핵심 키워드로만 노드를 기술하세요"*로 튜닝합니다.
    *   로컬 대체 모드(`_fallback_generate_mermaid`)에서도 `Speaker_00` 등 화자 자체를 노드로 생성하는 대신, 최근 전사 텍스트의 요약 문장을 바로 노드로 변환하고 화자 정보는 펜으로 연결하지 않도록 룰베이스 생성 구조를 개편합니다.

### 13-8. Mermaid 뷰 상단 실시간 대화 핵심 뉴스 자막 표출
*   **실시간 요약 헤드라인(News Ticker) 신설**:
    *   `FlowUI`의 Mermaid 차트 영역 바로 위(상단)에 **현재 진행 대화 요약 레이블(News Headline Label)**을 가로로 신설합니다.
*   **헤드라인 생성 루프**:
    *   `flow_agent.py`가 30초 분석 루프를 돌릴 때, Mermaid 코드 외에 추가로 **"현재 30초 대화의 핵심 요약 한 줄(뉴스 자막용)"**도 함께 획득하도록 Haiku 프롬프트를 튜닝합니다. (출력 양식: `요약 한 줄`과 `Mermaid 코드`를 `===` 구분자로 획득).
    *   획득한 핵심 요약 문장을 시그널을 통해 `FlowUI` 상단 헤드라인 레이블에 뉴스 자막 형태로 연동 표출합니다.

### 13-9. 검증 계획
*   **단위/통합 테스트 리팩토링**:
    *   기존 `tests/test_stt.py`, `tests/test_report.py`, `tests/test_ui.py`에서 개별 경로를 참조하던 검증 로직을 `output_dir/{session_id}` 단일 경로 기준으로 매핑 및 수정합니다.
    *   일시중지 상태에서 오디오 추론이 동작하지 않는지 테스트 케이스를 구축합니다.
*   **회귀 테스트 검증**:
    *   검증 명령어: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`


---

## 12. 상세 구현 설계서: Phase 14 (오버레이 엔진 모드 표시, UI 여백 최적화 및 STT 정확도 향상)

### 14-1. 흐름도 블록 영역 꽉 채우기 (HTML/CSS 여백 최적화)
*   **목적**: Mermaid 다이어그램이 표출되는 영역 주변에 과도하게 남아돌던 빈 여백을 없애고, 오버레이 창 내부를 꽉 채워 시인성을 극대화합니다.
*   **구현 설계**:
    *   `prismflow/agents/flow/mermaid_html.py` 내의 CSS 스타일시트를 수정합니다:
        *   `body`: `padding: 15px;` -> `padding: 2px;` 로 줄여 웹뷰 경계 여백 제거.
        *   `#diagram-container`: 
            *   `width: 95%;` -> `width: 100%;` 로 확장.
            *   `height: 90%;` -> `height: 100%;` 로 확장.
            *   `padding: 24px;` -> `padding: 10px;` 로 안쪽 여백을 줄여 그림 면적 극대화.
            *   `border-radius: 16px;` -> `border-radius: 8px;` 로 조절하여 하단 전사기록창의 border-radius와 통일.

### 14-2. 상단 핵심 요약 뉴스 자막바 글씨 크기 확대
*   **목적**: 회의 주제를 한눈에 볼 수 있도록 상단 속보식 뉴스 헤드라인의 시인성을 한단계 끌어올립니다.
*   **구현 설계**:
    *   `prismflow/agents/flow/flow_ui.py` 의 `self.headline_label` 스타일시트를 수정합니다:
        *   `font-size: 11px;` -> `font-size: 13px;` 로 글자 크기 격상.
        *   글자가 커짐에 따라 세로로 잘리지 않도록 `setFixedHeight(24)` -> `setFixedHeight(30)` 로 세로폭 조정.

### 14-3. 좌상단 타이틀 옆에 엔진 모드 (Claude / Local) 동적 표시
*   **목적**: 현재 생성된 흐름도가 원격 클라우드 AI(Claude)에 의한 것인지, 장애 시 동작한 로컬 대체 룰베이스(Local)에 의한 것인지 명시해 오판을 차단합니다.
*   **구현 설계**:
    *   `flow_ui.py` 에 `update_engine_mode(self, mode: str)` 메소드를 추가합니다.
        *   `self.title_label.setText(f"PrismFlow Agent ({mode})")` 로 텍스트를 갱신하고 `self.title_label.adjustSize()` 를 호출하여 가로폭을 재계산합니다.
    *   `main.py` 의 `AppCoordinator` 에서 `flow_agent.diagram_updated` 시그널이 발생할 때 호출될 슬롯에서 `self.cli_controller.is_session_limited()` 상태에 따라 `Claude` 또는 `Local` 문자열을 판정하여 `flow_ui.update_engine_mode(mode)`를 전달하도록 배선합니다.
    *   또한 대시보드 상태 뱃지 업데이트 시 `AgentState.OK` 옆에 "Claude" 혹은 "Local"을 상세 정보로 함께 갱신하도록 연계합니다.

### 14-4. STT 정확도 향상 기획 (Medium/Large 모델 지원 검토)
*   **분석 및 해결방안**:
    *   현재 탑재된 `whisper-small-int8-ov` (244MB) 모델은 로컬 연산 속도는 매우 빠르나, 한국어 실음성 전사 정확도가 다소 떨어집니다.
    *   이를 극복하기 위해 다음 Phase에서 **더 큰 모델의 OpenVINO int8/fp16 양자화 번들** 지원을 확장합니다:
        *   `whisper-medium-int8-ov` (약 760MB, 대폭 향상된 한국어 이해도)
        *   `whisper-large-v3-int8-ov` (약 1.5GB, 상용 수준 한국어 전사 정확도)
    *   Intel Core Ultra 7 258V (Arc GPU 가속 가용) 환경은 VRAM 및 연산 능력이 충분하므로, 설정 화면(`SettingsDialog`)에서 Medium 또는 Large 모델 선택 시 모델 경로에 맞춰 로딩할 수 있는 실엔진 매핑 로직을 확보하고, 필요 시 모델 자동 셋업(Hugging Face 가중치 감지/안내) 파이프라인을 보강합니다.

### 14-5. 검증 계획
*   **수동 검증**:
    *   `run.bat` 기동 후 화면에서 Mermaid 차트 영역이 여백 없이 오버레이 창 내부를 꽉 채우는지, 뉴스 자막 글씨가 크게 잘 보이는지, 좌상단 타이틀에 `(Claude)` 또는 `(Local)`이 동적으로 나타나는지 검사합니다.
*   **회귀 테스트 검증**:
    *   새로 추가된 UI 콤포넌트 규격에 맞춰 pytest 회귀 테스트를 통과시킵니다.
    *   검증 명령어: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`

---

### Phase 15: STT 상위 모델(medium/large-v3) 실배선 및 셋업 도구

> Phase 14-4의 기획(medium/large-v3 지원)을 실배선으로 전환한다. 사전 점검 결과
> **모델 크기→OV 디렉토리 매핑(`AppConfig.whisper_dir_name`)·설정 UI 콤보(tiny~large-v3)·
> STT 로드(`_load_openvino_models`)·미설치 상태 라벨은 이미 완비**되어 있었다. 따라서
> 실제 공백인 ①상위 모델을 받을 수단 ②미설치 선택 시 실행 가능한 안내만 채운다.

#### 핵심 발견 (출처 정합)
*   기존 `whisper-small-int8-ov` 번들의 README가 가리키듯, small은 optimum 로컬 변환이 아니라
    **HuggingFace `OpenVINO` org가 사전 빌드한 int8-ov 모델**을 그대로 받은 것이다.
*   동일 org가 `OpenVINO/whisper-medium-int8-ov`, `OpenVINO/whisper-large-v3-int8-ov`를
    제공하므로, optimum/nncf 로컬 변환 없이 `snapshot_download`만으로 small과 동일한
    출처·레이아웃을 보장할 수 있다. (이미 설치된 `huggingface_hub`만 의존)

#### 개발 범위
| 대상 파일 | 작업 내용 |
|:---|:---|
| `scripts/setup_whisper_model.py` [NEW] | 모델 크기(tiny/base/small/medium/large-v3) → `OpenVINO/whisper-{size}-int8-ov` repo를 `snapshot_download`으로 `prismflow/resources/models/whisper-{size}-int8-ov`에 배치. `--list`(설치 상태), `--force`(재다운로드), 멱등 skip, 순수 헬퍼(`repo_id_for`/`dir_name_for`/`target_dir_for`/`is_installed`) 분리로 테스트 용이 |
| `prismflow/agents/stt/stt_agent.py` | `_load_openvino_models`의 모델 미존재 `FileNotFoundError`가 디렉토리명에서 크기를 역산해 `python scripts/setup_whisper_model.py {size}` 설치 명령 + small 폴백을 안내 |
| `prismflow/ui_common/settings_ui.py` | 모델 상태 라벨의 "✗ 미설치" 문구에 동일 설치 명령을 노출 |
| `tests/test_setup_whisper.py` [NEW] | 셋업 스크립트 순수 헬퍼 검증(네트워크 미사용): 디렉토리 매핑이 `AppConfig.whisper_dir_name` 단일 정본과 일치, repo id 포맷, UI 콤보 항목 전체 지원, 미지원 크기 거부, 미설치 판정 |

#### 비-목표(Non-goal)
*   대용량 가중치를 git에 커밋하지 않는다(`prismflow/resources/models/`는 `.gitignore` 처리).
    배포 시에는 셋업 스크립트 또는 `build_release.py` 번들 단계에서 가중치를 확보한다.

#### ReAct 검증
```bash
.venv\Scripts\python.exe scripts/setup_whisper_model.py medium
.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q
```

---

### Phase 16: 통합 회의 콘솔 UI 재구성 및 STT 성능·정확도 향상

> **배경**: Phase 15(medium 실배선) 직후 사용자가 실제 회의로 E2E를 돌려 6개 개선점을 제기했다.
> 두 갈래 — ①UX 통합·가독성(Flow/Chat 창 분리·작은 폰트·비직관 회의제어·혼란스러운 CLI 디버그 분류),
> ②STT 성능(전사 느림·정확도 아쉬움). 정량 지표를 세우고 끌어올린다.
> **결정(사용자 확인 2026-06-21)**: ⓐ STT는 **균형 — medium + GPU 최적화**(정확도↑, 반응성은 GPU/튜닝으로 회복,
> 벤치마크로 전후 정량화). ⓑ 6개 항목을 **단일 Phase 16**으로 묶는다.
> **현황 메모**: DB가 테스트로 `whisper_model_size=medium`, `stt_mock_mode=false` 상태(medium이 small보다 느린 것이 "느림" 체감에 일부 기여).

#### 현행 구조 요약 (착수 전 탐색 결과)
*   `FlowUI`(=PrismFlow Agent, `flow_ui.py`)와 `ChatUI`(=Chat Agent, `chat_ui.py`)는 **각각 별도 최상위 창**이며 둘 다 `TranslucentOverlay`(`overlay.py`) 상속 → 드래그·호버페이드·우상단 컨트롤바(최소화/닫기 + 숨김 `btn_pause`/`btn_stop`)·녹음 인디케이터 공유. **회의 "시작" 버튼은 창에 없고 트레이 메뉴에만 존재**.
*   `main.py` `AppCoordinator`가 두 창을 생성·개별 배치하고 모든 시그널을 배선. `tray.set_ui_handlers(flow_ui, chat_ui, cli_log_window)`.
*   `mermaid_html.py`: `themeVariables`에 폰트 크기 미지정(기본 ~16px), `updateDiagram()`이 `innerHTML` 즉시 교체(전환 애니메이션 없음).
*   `flow_agent.py`: `_should_trigger` 3-way(최초 즉시/버스트=주제전환 8초 바닥/정기 30초), 프롬프트 규칙4에 주제전환 시 subgraph 그룹화 지시 **이미 존재**. 헤드라인은 `summary_updated`로 방출.
*   `stt_agent.py`: VAD 엔드포인트 1.0초 무음, 15초 강제분절, interim 전사 존재. `_detect_device()` GPU→CPU.
*   CLI 디버그(`cli_log_window.py`+`cli_activity.py`): 라벨이 **세션 접두사**로 결정(`agent-session`→"Agent"=도구증강 Q&A, 그 외→"CLI"=미분류 폴백). **i2t(화면감지)는 Claude CLI 미사용 로컬 모듈이라 CLI 로그가 없음** → 사용자가 디버그 창에서 못 찾은 이유.

#### 개발 범위
| 항목 | 대상 파일 | 작업 내용 |
|:---|:---|:---|
| **16-1** 단일 콘솔 통합 + 채팅 토글 | `flow_ui.py`, `chat_ui.py`, `main.py`, `tray.py` | **조정된 외과적 구현(Karpathy ③)**: 당초 신규 `MeetingConsole` 클래스를 두려 했으나, 그러면 FlowUI base 변경 + `test_status`(녹음·레이아웃) 광범위 파손이 불가피했다. 대신 **FlowUI를 그대로 단일 콘솔의 호스트**로 유지(TranslucentOverlay 크롬·녹음·회의 시그널·`set_recording` 보존)하고, **ChatUI만 base를 `TranslucentOverlay`→`QWidget`(임베드 패널)** 로 전환한다. FlowUI는 `chat_panel` 옵션을 받아 `QHBoxLayout`[좌 Flow 콘텐츠(stretch) · 얇은 토글 핸들 `›`/`‹` · 우 Chat 패널(고정폭 420)]로 재배치하고 `toggle_chat_panel`/`set_chat_visible` 제공(접힘 판정은 `isHidden()` 기준 → 창 표시 전에도 테스트 가능). `main.py`는 `chat_agent`→`ChatUI`(패널)→`FlowUI(chat_panel=...)` 순으로 생성, `self.flow_ui`/`self.chat_ui`는 그대로 두어 기존 시그널 배선 보존, 콘솔 1개 배치·`set_recording` 단일화, `tray.set_ui_handlers(flow_ui, flow_ui, ...)`. 공개 메서드 시그니처 전부 보존. |
| **16-2** 헤드라인 중앙·2배폰트·핵심어 강조 | `flow_ui.py`(통합 후 Flow 패널), `core/glossary.py`(조회 재사용) | 헤드라인 자막바: `AlignCenter`, font 13→26px, 높이 30→~56px, 워드랩. `update_headline(text)`를 richtext로 변환해 **회의 용어집/교정사전 용어 + 숫자·날짜 토큰**을 `<span style="color:#ffd54a">`로 래핑(결정적 규칙 기반, LLM 비의존). 매칭 없으면 평문. |
| **16-3** STT 성능 지표 + 반응성·정확도(균형) | `scripts/stt_benchmark.py` [NEW], `tests/test_stt_benchmark.py` [NEW], `stt_agent.py`, `config.py`(필요 시) | 측정 하네스: 지표 ① RTF(오디오초/추론초) ② 엔드포인트→`transcript_updated` 지연 ③ 정확도 프록시(고정 한국어 WAV의 기준 텍스트 대비 CER/WER). small vs medium · CPU vs GPU 대조표(opt-in `STT_LIVE`). 측정 기반 튜닝: GPU 우선 강제 확인, VAD 엔드포인트·interim 주기·15초 강제분절·`vad_threshold` 재조정(**값은 측정 후 확정, 계획에 고정값 미기재**). 정확도: medium 기본 + 교정사전·환각 블랙리스트 경로 유지/강화. **목표: small 베이스라인 대비 CER 10%↓ 또는 동일 정확도서 지연 10%↓ 중 측정으로 달성 가능한 축을 명시(상충 사실 정직 기록).** |
| **16-4** 회의 시작 버튼 → 일시정지/정지 모핑 | `overlay.py`(콘솔 컨트롤바), `tray.py`/`main.py` 정합 | `btn_start`(▶ Segoe MDL2) 추가 — 회의 비활성 시 표시, 클릭 시 `context.start_meeting()`(트레이 시작과 동일 경로 재사용). `meeting_started`→start 숨김+pause/stop 표시, `meeting_ended`→역전. 트레이 회의 시작/종료는 유지(이중 진입점). |
| **16-5** Mermaid 다이나믹·2배폰트·주제전환 갱신 | `mermaid_html.py`, `flow_agent.py` | `themeVariables.fontSize` ~2배(예 `24px`), `updateDiagram()`에 opacity/transform 페이드 전환(컨테이너 `transition`+신규 SVG fade-in). 주제전환: 프롬프트 규칙4를 "**대주제 전환 시 새 subgraph로 명확히 분기**"로 강화, 필요 시 `burst_threshold`/`min_interval_sec` 미세조정(체감 속도). |
| **16-6** CLI 디버그 분류 정리 + i2t 표기 | `cli_activity.py`, `cli_log_window.py`, `tests/test_cli_activity.py` | `agent_label_for_session`: `agent-session`→"Q&A(도구)"로 명칭 변경(의미 명시), "CLI" 폴백은 주석/툴팁 보강. 필터 콤보를 `전체/Flow/Chat/Q&A(도구)/Report` 위주로 재정렬 + 상단 짧은 **범례**. **i2t는 로컬(화면감지)이라 CLI 로그가 없음**을 범례 한 줄로 안내하고, i2t 상태는 상태패널(`status_panel`)의 i2t 뱃지로 본다는 점 명기. |
| **16-7** 회귀·문서 | `tests/`, `docs/` | UI 리팩토링으로 깨지는 `test_ui`/`test_chat`/`test_cli_activity` 갱신, 전체 `pytest tests/` 무결. `docs/phase16_stt_benchmark.md`(전/후 표)·history·task 동기화. |

#### 구현 순서(권장)
16-6(저위험·독립) → 16-2·16-5(렌더/스타일·독립) → 16-4(컨트롤바) → 16-1(최대 리팩토링; 앞 변경을 패널로 흡수) → 16-3(측정·튜닝 반복) → 16-7(회귀·문서).

#### 비-목표(Non-goal)
*   신규 번역 기능 없음(사용자의 "번역성"은 **전사 정확도**로 해석).
*   large-v3 기본 채택 안 함(설정에서 선택 가능, 배선은 Phase 15 완료분 재사용).
*   "10% 향상"의 양축(정확도·반응성) 동시 보장은 medium↔속도 상충으로 보장 불가 → 측정으로 달성 가능한 축을 정해 수치로 정직히 보고(과약속 금지).

#### ReAct 검증
*   단위/회귀: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q` (신규 벤치 포함 전부 통과).
*   수동 E2E(클린 재기동): 단일 콘솔에 좌 Flow/우 Chat → `>`/`<` 토글 → 헤드라인 중앙·대형·핵심어 색 → 창 ▶시작으로 회의 시작 → 일시정지/정지 모핑 → 한국어 발화 반응성 → 주제 전환 시 Mermaid 새 subgraph 전환(큰 폰트·페이드) → Chat 질의응답 → 정지 시 보고서 생성.
*   STT 정량: `scripts/stt_benchmark.py` 대조표 → `docs/phase16_stt_benchmark.md`에 전/후·10% 목표 달성 여부 기록.
*   관측 한계: 앱은 uv venv 트램폴린이라 stdout 캡처 불가 → DB 전사/세션 출력물(WAV/TXT/MD)·보고서로 검증(Phase 15 E2E 방식).

---

### Phase 17: 회의 제어 UX 재설계 · Mermaid 사용성/자유도 · 실시간 전사 개선

> **배경**: Phase 16 사용자 E2E 후 후속 피드백(2026-06-21). 단일 콘솔/헤드라인/CLI 분류/엔진모드는 정상 동작했으나,
> ①회의 제어 버튼 동작이 직관과 다르고 ②Mermaid가 글자 잘림·세로 나열식·좌우 여백 과다·subgraph 미출현으로 가독성이 나쁘며
> ③실시간 전사가 늦고(확정 지연) interim이 앞 문장을 잃고 ④채팅 토글 핸들 아이콘/위치/기본 여백이 거슬린다는 지적.
> **모델 결론(2026-06-21 사용자 지시)**: 기본 **medium 확정 — 빡세게 목표 잡고 튜닝**한다. (Phase 16-3 실측에서 medium은 확정 지연·반복 환각 위험이 있었으나, 정확도 잠재력을 살리는 방향으로 ⓐ`collapse_repetitions` 반복 환각 억제 ⓑinterim 망각 해소 ⓒendpoint 단축으로 medium의 약점을 공격적으로 보정한다.)

#### 현행 한계 (E2E 관찰 근거)
*   **회의 제어**: Phase 16-4에서 ▶시작 버튼이 시작 시 pause/stop으로 "전환"되도록 했으나, 사용자는 **▶↔⏸ 토글(재생/일시정지)** + **별도 ⏹ 정지(좌측)** 모델을 원함. 현재 3버튼 구성이 직관과 어긋남.
*   **Mermaid**: Haiku가 `graph TD` 선형 체인(A→B→C…)만 생성 → 화면이 세로로 길고 좌우 여백이 큼. 노드 박스가 폰트(28px)보다 작아 한국어가 잘림(`htmlLabels`/패딩 부재). 프롬프트가 Upsert(append) 위주라 stale 노드가 계속 쌓이고 subgraph가 사실상 안 나옴.
*   **실시간 전사**: Phase 16-3의 interim 4초 윈도우가 **라이브 자막에서 발화 앞부분을 잃게 함**(사용자 "수정 앞 문장을 까먹는다"). 또한 endpoint 1.0초 + 긴 발화로 **확정 전사가 늦게** 뜸.
*   **채팅 토글**: 우측 중앙의 `›`/`‹` 핸들 아이콘이 투박하고, 기본(펼침) 상태에서 핸들 주변 여백이 거슬림. 사용자는 핸들을 **상단 컨트롤바(녹음중 옆)로 이동**하고 아이콘 교체를 원함.

#### 개발 범위
| 항목 | 대상 파일 | 작업 내용 |
|:---|:---|:---|
| **17-1** 회의 제어 재설계(상태기계) | `overlay.py`, `tray.py`/`main.py` 정합 | 컨트롤바를 **⏹ 정지(좌) + ▶/⏸ 재생-일시정지 토글(우)** 2버튼으로 재정리. 상태기계: (비활성)→▶클릭=회의 시작→⏸ 표시 / ⏸클릭=일시중지→▶ 표시 / ▶클릭=재개→⏸ / ⏹클릭=종료→(비활성, ▶). 정지는 회의 중에만 활성. `context.start_meeting`/`toggle_pause`/`end_meeting` 재사용, 기존 btn_start/btn_pause/btn_stop을 이 모델로 통합. |
| **17-2** Mermaid 사용성·자유도 | `mermaid_html.py`, `flow_agent.py` | (a) **글자 잘림 해소**: `flowchart`에 `htmlLabels:true`+노드 패딩 확대+`white-space` 래핑, 폰트는 가독 범위(예 20~22px)로 재튜닝(28px가 박스를 넘쳤음). (b) **여백 활용**: `useMaxWidth:true`+컨테이너 꽉 채움, 선형 체인이 세로로만 길지 않도록 **방향/그룹핑을 모델이 자유 선택**(TD/LR 혼용·subgraph 열 배치 허용). (c) **맥락 기반 동적 구성**: Flow 프롬프트를 append-Upsert 강제에서 **"사용성 우선 자유 재구성"**으로 전환 — 대주제별 subgraph 그룹핑 의무화, **불필요·종료된 화제 노드는 제거 허용**, 최신 흐름이 한눈에 들어오도록 압축(노드 수 상한·핵심만). 자유도는 높이되 출력 형식(요약===mermaid)·화자배제 규칙은 유지. |
| **17-3** STT 기본 medium(빡센 튜닝) + 실시간 전사 개선 | `config.py`(또는 DB), `stt_agent.py` | 기본 모델 **medium** 확정(DB `whisper_model_size=medium`)하고 medium의 약점을 공격적으로 보정. **interim 망각 해소**: 라이브 자막을 "확정 문장 누적 + 진행 중 발화만 interim"으로 바꿔 발화 앞부분이 사라지지 않게(16-3의 4초 윈도우가 앞을 자르던 문제 보정 — 누적 표시/문장 commit 방식). **확정 지연 단축**: endpoint(1.0초)·min_utt·강제분절을 medium 기준으로 재튜닝(medium은 추론이 small보다 무거우므로 interim 빈도/윈도우와 endpoint의 균형을 실측으로 잡음). **환각 억제**: `collapse_repetitions` 유지·강화(medium 반복 루프 대응). medium RTF(GPU 0.123)는 실시간 8배라 처리량은 충분 — 체감 지연은 interim/endpoint 구조 개선으로 잡는다. |
| **17-4** 채팅 토글 핸들 이동·아이콘·여백 | `flow_ui.py`, `overlay.py` | 토글 핸들을 우측 중앙에서 제거하고 **상단 컨트롤바(녹음중 옆)** 에 채팅 표시/숨김 토글 버튼으로 이동, 아이콘 교체(말풍선/패널 아이콘 등). 기본 상태에서 핸들 컬럼이 차지하던 **여백 제거**(접힘 시 Flow가 자연스럽게 전폭). |
| **17-5** 회귀·문서 | `tests/`, `docs/` | 컨트롤 상태기계·토글 위치 변경에 맞춰 `test_status`/`test_flow` 갱신, 전체 `pytest` 무결. history/task/plan 동기화. |

#### 구현 순서(권장)
17-4(토글 이동, 저위험) → 17-1(제어 상태기계) → 17-2(Mermaid, 프롬프트+CSS 반복) → 17-3(STT 실시간 개선) → 17-5(회귀·문서).

#### 비-목표 / 트레이드오프
*   Mermaid "자유도"는 출력 계약(요약 `===` mermaid, 코드펜스 금지, 화자 배제)과 오프라인 폴백 룰은 유지하는 선에서의 자유다(파서 안정성 보전).
*   기본 모델은 medium(사용자 지시). small/large는 설정에서 선택 유지.
*   "확정 지연 단축"은 endpoint를 너무 줄이면 문장 중간 끊김이 늘어나는 상충이 있어, 체감과 분절 안정성의 균형점을 실측으로 잡는다(과약속 금지).

#### ReAct 검증
*   단위/회귀: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`.
*   수동 E2E: ⏹+▶/⏸ 토글 동작 → Mermaid 글자 안 잘림·여백 활용·subgraph/그룹 출현·stale 노드 정리 → 한국어 발화 시 확정이 빠르고 앞 문장 유지되는지 → 토글이 상단바에서 동작·기본 여백 없음.

---

### Phase 18: Mermaid 흐름도 실시간 줌, 팬 및 유리(Glassmorphic) 돋보기 컨트롤 툴바 구현

> **배경**: 실시간 회의 중 누적되는 전사록을 기반으로 Mermaid 다이어그램(Flow)이 점차 확장되거나 상세해짐에 따라, 전체 화면에 그래프가 가득 차면서 글씨가 축소되거나 일부 노드를 읽기 어려운 UX 피드백이 발생했습니다.
> 이를 근본적으로 해결하기 위해, 사용자가 웹 캔버스 영역 내에서 **마우스 휠 줌(Zoom In/Out)**, **마우스 좌클릭 드래그 팬(Pan/화면 이동)**을 수행할 수 있게 하고, 동시에 직관적이고 세련된 **유리(Glassmorphic) 스타일 돋보기/줌 툴바 UI**를 우측 하단에 제공하여 원클릭으로 화면 맞춤(Fit), 줌 리셋(1:1)을 조작할 수 있도록 합니다.

#### 핵심 과제 및 설계 사양

1. **오프라인 라이브러리 탑재**
   - 인터넷 연결 없이 작동해야 하는 배포 규격(Phase 8)에 맞추어 `svg-pan-zoom.min.js` (~20KB) 라이브러리를 로컬 리소스 디렉토리 `prismflow/agents/flow/resources/`에 번들로 배치하고 Git 추적 대상에 포함합니다.
   - `mermaid_html.py`의 `get_mermaid_html()`에서 `__SVG_PAN_ZOOM_JS_URL__` 플레이스홀더를 통해 로컬 URL을 동적으로 주입합니다.

2. **SVG 레이아웃 CSS 충돌 제거**
   - 기존의 `#diagram-container svg`에 지정된 `width: 100% !important; height: auto !important; max-width: 100% !important;` 스타일은 `svg-pan-zoom`이 계산하는 인라인 transform 및 viewBox 제어 로직과 강하게 충돌하여 화면이 찌그러지거나 줌/팬이 오작동하게 만듭니다.
   - 따라서 해당 강제 크기 규격 CSS를 제거하고, `svg-pan-zoom`이 viewBox 속성을 가진 SVG를 자유롭게 크기 변환(transform)할 수 있도록 구조를 리팩토링합니다.
   - `#diagram-container`는 `overflow: hidden`으로 설정하여 브라우저 기본 스크롤바를 숨기고 줌/팬 캔버스 영역으로 전환합니다.

3. **다크 Glassmorphism 줌 컨트롤 툴바 UI**
   - HTML/CSS를 통해 웹뷰 우측 하단(상태 패널의 레이아웃 영역을 침범하지 않는 위치)에 `position: absolute; bottom: 16px; right: 16px; z-index: 100;` 형태로 반투명 유리 컨트롤 바를 띄웁니다.
   - **디자인 토큰**: `background: rgba(30, 30, 35, 0.65); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 4px; display: flex; gap: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);`
   - **버튼 구성**:
     - ➕ 확대 (Zoom In) -> `panZoomInstance.zoomIn()`
     - ➖ 축소 (Zoom Out) -> `panZoomInstance.zoomOut()`
     - 🎯 중앙 맞춤 (Fit & Center) -> `panZoomInstance.fit(); panZoomInstance.center();`
     - 🔄 원래 비율 (Reset Zoom 1:1) -> `panZoomInstance.reset();`
   - 버튼 호버(hover) 시 은은한 배경 전환(`rgba(255,255,255,0.08)`) 및 청록색 강조(`color: #5eead4`) 효과를 적용하여 Premium UI/UX를 완성합니다.

4. **다이어그램 갱신 시 상태 보존 (State Preservation) 알고리즘**
   - 8초/15초 주기로 다이어그램 코드가 갱신될 때마다 전체 SVG가 재렌더링되는데, 이때 줌 레벨과 화면의 중심 위치가 매번 초기화되면 사용성이 극단적으로 저하됩니다.
   - 이를 방지하기 위해 `updateDiagram(mermaidCode)`이 실행될 때 다음 4단계 복원 로직을 순수 JavaScript로 구현합니다.
     - **백업**: 새 코드를 받으면 기존 `panZoomInstance`가 존재하는 경우 `lastZoom = panZoomInstance.getZoom(); lastPan = panZoomInstance.getPan();`으로 상태를 저장하고 `panZoomInstance.destroy()`로 메모리를 정리합니다.
     - **렌더링**: `mermaid.run()`을 수행해 DOM에 새 SVG 렌더링합니다.
     - **재구성**: 렌더링된 새 SVG 요소를 바탕으로 `svgPanZoom`을 다시 호출하여 인스턴스를 새롭게 생성합니다.
     - **복원**: `lastZoom`과 `lastPan`이 백업되어 있다면 이를 즉시 신규 인스턴에 `panZoomInstance.zoom(lastZoom)` 및 `panZoomInstance.pan(lastPan)`으로 복구합니다. (최초 실행 시에는 복원 없이 `fit: true, center: true`로 중앙에 배치합니다).

#### 개발 범위

| 항목 | 대상 파일 | 작업 내용 |
|:---|:---|:---|
| **18-1** 오프라인 라이브러리 번들 추가 | `prismflow/agents/flow/resources/svg-pan-zoom.min.js` [NEW] | jsdelivr CDN에서 `svg-pan-zoom@3.6.1` 공식 배포 minified 버전을 다운로드하여 리소스 폴더에 번들 저장하고, 릴리즈 추적(Git)에 등록합니다. |
| **18-2** 줌 툴바 UI 및 API 배선 | `prismflow/agents/flow/mermaid_html.py` | HTML 템플릿에 `__SVG_PAN_ZOOM_JS_URL__` 스크립트 태그 추가. absolute 포지셔닝의 Glassmorphic 줌 툴바(➕, ➖, 🎯, 🔄) 스타일 및 HTML 엘리먼트 추가. 각 버튼 클릭 이벤트 리스너에서 `svg-pan-zoom` 인스턴스의 API를 호출하는 JS 배선 완료. |
| **18-3** 줌/팬 상태 보존 로직 | `prismflow/agents/flow/mermaid_html.py` | `updateDiagram()` 실행 시 기존 인스턴스 소멸 전 줌/팬 값을 백업 변수에 기록하고, 신규 렌더 완료 후 이를 재주입하여 부드러운 전이를 보장하는 복원 스크립트 작성. |
| **18-4** SVG 레이아웃 스타일 충돌 리팩토링 | `prismflow/agents/flow/mermaid_html.py` | `#diagram-container`의 `overflow`를 `hidden`으로 변경, `#diagram-container svg`의 인라인 크기 강제 스타일(width/max-width/height/max-height)을 제거하여 라이브러리가 크기 조정을 주도하도록 스타일 충돌 해소. |
| **18-5** 회귀 및 검증 | `tests/test_flow.py` | `test_flow.py`에서 `svg-pan-zoom.min.js` 번들 리소스 파일의 존재 확인 및 HTML 템플릿 내 경로 매핑 치환 로직 유효성을 검증하는 테스트 추가. 전체 `pytest tests/` 통과 보장. |

#### 구현 순서(권장)
18-1(리소스 추가) → 18-4(CSS 충돌 해소) → 18-2(줌 툴바 및 기본 줌/팬 초기화) → 18-3(상태 보존 알고리즘 구현) → 18-5(테스트 추가 및 회귀 검증).

#### 비-목표(Non-goal)
*   사용자의 회의 전체 창 돋보기가 아님: 오직 Flow(Mermaid) 웹 캔버스 영역 내에서의 SVG 줌/팬 및 돋보기 툴바 기능만 다룹니다.
*   Mermaid 노드 자체의 텍스트 편집 기능은 지원하지 않습니다.

#### ReAct 검증
*   단위/회귀: `.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q` (신규 리소스/템플릿 테스트 포함 100% 통과).
*   수동 E2E:
    - 앱 구동 후 회의 시작 -> 다이어그램 렌더링 확인.
    - 다이어그램 영역에서 마우스 좌클릭 드래그로 상하좌우 부드럽게 이동하는지(Pan) 검증.
    - 다이어그램 영역에서 마우스 휠 스크롤 시 마우스 포인터 위치를 기준으로 부드럽게 확대/축소(Zoom)되는지 검증.
    - 우측 하단의 Glassmorphic 돋보기 툴바의 ➕/➖/🎯/🔄 각 버튼 클릭 시 정해진 동작(줌인, 줌아웃, Fit&Center, 1:1 Reset)이 정상 작동하는지 확인.
    - 새로운 발화로 인해 다이어그램이 갱신(8초/15초)될 때, 사용자가 임의로 이동/확대해둔 캔버스의 구도(줌/팬 좌표)가 초기화되지 않고 일관되게 보존되는지 육안 확인.




---

### Phase 19: Mermaid 박스 크기 최적화, 긴 발화 강제 분절(Force Commit) STT 튜닝 및 줌 툴바 UI 간소화

> **배경**:
> 1. Mermaid 흐름도의 박스 가로폭이 극단적으로 좁아 한국어 단어가 잘리거나 말줄임표(...)로 생략되어 가독성이 떨어지는 문제를 해결합니다.
> 2. 회의 진행 중 사용자가 쉬지 않고 긴 말을 이어갈 때, 전사가 확정되지 않고 실시간 자막창의 임시 전사(Interim) 앞부분이 짤리거나 Whisper가 이전 결과를 왜곡 수정하는 문제를 해결합니다.
> 3. 돋보기 줌 툴바의 4개 버튼 중 중복적인 `1:1 리셋` 버튼을 제거하고, `화면맞춤(fit)` 아이콘을 🎯(과녁)에서 사각형(ㅁ) 기호로 변경하여 직관적인 룩앤필을 확보합니다.

#### 핵심 과제 및 설계 사양

1. **Mermaid 박스 가로폭 최적화 및 단어 단위 줄바꿈**
   - `mermaid_html.py` 내의 `mermaid.initialize` 설정 중 `flowchart: { ... }` 내의 `wrappingWidth` 속성값을 기존 `220`에서 `500`으로 넉넉하게 확장합니다.
   - CSS 스타일 중 `.mermaid .nodeLabel` 등에 `word-break: keep-all !important;` 및 `white-space: normal !important;` 스타일을 강제하여, 영어/한국어 단어가 중간에 임의로 잘리지 않고 단어 묶음 단위로 자연스럽게 늘어나도록 합니다.
   
2. **STT 강제 분절(Force Commit) 튜닝**
   - `stt_agent.py` 내의 `_run_vad_segmented_loop` 함수에서 백프레셔로 작동하는 최대 발화 제한 샘플 수 `max_utt_samples` 값을 기존 `20.0 * sr` (20초)에서 **`7.0 * sr` (7초)** 수준으로 단축 조정합니다.
   - 또한 임시 전사 최대 윈도우 상한을 의미하는 `interim_window_samples` 값 또한 이에 대응하여 `7.0 * sr` (7초)로 조절합니다.
   - 이렇게 하면 사용자가 쉬지 않고 계속 폭주 발화를 하더라도 최대 7초 단위로 강제 `finalize()`가 수행되어 전사가 안전하게 확정(Commit) 및 DB 적재되고 자막창의 누적 확정 영역으로 넘어갑니다. 이는 10초 이상 음성이 쌓여 Whisper가 앞 문장을 덮어쓰고 생략하는 현상을 근본적으로 차단합니다.

3. **돋보기 줌 툴바 UI 정비**
   - `mermaid_html.py`의 HTML 구조 및 JS 바인딩에서 `1:1 리셋 (btn-zoom-reset)` 버튼을 완전히 제거합니다. (➕, ➖, 화면맞춤 3버튼 체제로 간소화)
   - `화면맞춤 (btn-zoom-fit)` 버튼의 내장 글리프 기호인 `🎯`를 사각형 기호인 `&#9723;` (white medium square ◻)로 대체하여 사용자가 요청한 'ㅁ' 형태의 세련된 아이콘을 제공합니다.

#### 개발 범위

| 항목 | 대상 파일 | 작업 내용 |
|:---|:---|:---|
| **19-1** Mermaid 가로폭 최적화 | `prismflow/agents/flow/mermaid_html.py` | `wrappingWidth`를 220에서 500으로 변경. CSS에 `word-break: keep-all !important;` 및 `white-space: normal !important;` 스타일 강제화. |
| **19-2** STT 강제 분절 단축 배선 | `prismflow/agents/stt/stt_agent.py` | `max_utt_samples` 및 `interim_window_samples` 크기를 20.0초/10.0초에서 **7.0초**로 단축 조정하여 누적 왜곡 및 앞문장 짤림 방어. |
| **19-3** 돋보기 툴바 간소화 및 기호 변경 | `prismflow/agents/flow/mermaid_html.py` | HTML 및 JS에서 `btn-zoom-reset` 삭제, `btn-zoom-fit` 내 기호를 `&#9723;`로 교체하여 'ㅁ' 형태 아이콘 구현. |
| **19-4** 회귀 및 검증 | `tests/test_flow.py`, `tests/test_stt.py` | 수정된 VAD 타임아웃 설정 및 줌 툴바 HTML/CSS 구성 요소 정합성을 확인하는 단위 테스트 보완. 전체 테스트 통과 검증. |

#### 구현 순서(권장)
19-1 (Mermaid 최적화) -> 19-3 (줌 툴바 정비) -> 19-2 (STT 7초 분절 구현) -> 19-4 (단위 테스트 보강 및 검증)

#### ReAct 검증
*   단위/회귀: `.venv\Scripts\python.exe -m pytest tests/ -v` (모든 테스트 무결 통과).
*   수동 E2E 테스트:
    - 앱 구동 후 회의 시작 및 한국어 발화.
    - 긴 문장을 말할 때 최대 7초 주기로 끊어져서 자막창에 고정(Commit)되고 앞 문장이 짤리거나 흔들리지 않는지 육안 검증.
    - Mermaid 흐름도 렌더링 시 노드 박스 내부의 단어가 임의로 잘리지 않고 박스 폭이 자연스럽게 넓어지는지 확인.
    - 돋보기 툴바에서 1:1 버튼이 사라지고, 과녁 대신 'ㅁ' 모양 사각형 ◻ 버튼이 동작하여 화면 맞춤 및 Center 기능을 조작하는지 검증.
