# PrismFlow 구현 계획서 (수정본)

PrismFlow는 Windows 시스템 트레이에 상주하며 회의 음성을 실시간으로 감지/녹음하고, 투명 오버레이 창을 통해 회의 흐름도(Mermaid.js) 시각화 및 맥락 기반의 실시간 질의응답(Chat)을 제공하는 애플리케이션입니다.

본 구현 계획서는 **AI 에이전트의 토큰 최적화 및 ReAct(생각-실행-검증) 루프**를 극대화하기 위해 **수직 슬라이스 아키텍처(Vertical Slice Architecture)**와 **명확한 테스트 환경(Tests)**을 포함하도록 설계를 전면 수정했습니다.

---

## 🛠️ 핵심 변경 및 AI 최적화 설계

> [!IMPORTANT]
> **1. 독립 에이전트 기반 수직 슬라이스 아키텍처 (`prismflow/agents/` 도입)**
> - 기존의 기능 계층별 분류(UI, Agent, Utils)를 폐지하고, 독립된 4대 AI 에이전트별(STT, Flow, Chat, Docs)로 디렉토리를 완전히 격리하여 수직 슬라이스화합니다.
> - **효과**: AI가 특정 기능(예: Flow 시각화)을 수정할 때, 다른 모듈의 코드를 읽지 않아도 되므로 **컨텍스트 토큰 소비를 최소화**하고 오작동을 방지합니다.

> [!IMPORTANT]
> **2. 데이터베이스 레이어 명시화 (`prismflow/core/db.py`)**
> - 실시간 컨텍스트 및 과거 대화, 설정 정보를 영구 보관할 로컬 SQLite 데이터베이스를 핵심 코어 레이어에 명시합니다.
> - 회의록 세션 테이블, 트랜스크립트 로그 테이블, 채팅 기록 테이블을 정의하여 관리합니다.

> [!IMPORTANT]
> **3. ReAct(계획-실행-검증) 테스트 환경 구축 (`tests/` 추가)**
> - 각 기능 슬라이스마다 단독 검증 가능한 테스트 코드 세트를 탑재합니다.
> - AI 에이전트가 코드를 작성한 직후 `pytest` 명령을 통해 터미널에서 동작을 직접 검증하고 자가 수정(Self-Correction)할 수 있는 가이드라인을 제공합니다.

---

## 시스템 아키텍처 개요

```mermaid
graph TD
    SystemTray[시스템 트레이 & 메인 컨트롤러] --> |세션 관리| MeetingContext((MeetingContext 싱글톤))
    SystemTray --> |영구 저장| SQLiteDB[(SQLite DB)]
    
    subgraph 수직 슬라이스 에이전트군 (Agents Slices)
        STTSlice[agents/stt/ - STT & Audio]
        FlowSlice[agents/flow/ - Mermaid Flow & WebEngine]
        ChatSlice[agents/chat/ - Q&A Chat UI & RAG]
        DocsSlice[agents/docs/ - Report Docs Generator]
    end
    
    STTSlice -->|발화 데이터 적재| MeetingContext
    MeetingContext -->|데이터 동기화| SQLiteDB
    
    FlowSlice -->|대화 요약/차트 추출| ClaudeCLI_Flow[Claude CLI - Flow 세션]
    ChatSlice -->|Q&A 질문 + RAG 컨텍스트| ClaudeCLI_Chat[Claude CLI - Chat 세션]
    
    DocsSlice -->|회의록 Markdown 컴파일| ClaudeCLI_Docs[Claude CLI - Opus 세션]
```

---

## 전체 디렉토리 구성 (AI 최적화 수직 슬라이스 구조)

```text
E:\Tak\Gemini\PrismFlow\
├── agent.md                        # AI 내비게이션, 코딩 규칙 및 현황판 (AI Context 진입점)
├── main.py                         # 앱 시작 진입점
├── run.bat                         # Windows 원클릭 가상환경 실행 스크립트
│
├── docs/                           # 산출물 보관함
│   ├── implementation_plan.md      # 본 구현 계획서
│   └── task.md                     # ReAct 루프 추적용 Task 상태판
│
├── tests/                          # [신설] ReAct 검증용 테스트 스위트
│   ├── __init__.py
│   ├── conftest.py                 # PyTest 공통 피스처 및 환경 설정
│   ├── test_db.py                  # SQLite CRUD 비즈니스 로직 테스트
│   ├── test_cli.py                 # Claude CLI 파이프 비차단 IO 테스트
│   ├── test_stt.py                 # VAD 및 STT 에뮬레이터 테스트
│   ├── test_flow.py                # Mermaid 코드 생성 및 흐름도 갱신 테스트
│   └── test_chat.py                # Chat RAG 프롬프트 병합 및 응답 테스트
│
└── prismflow/                      # 메인 패키지
    ├── __init__.py
    │
    ├── core/                       # 중앙 제어 및 데이터 핵심 레이어
    │   ├── __init__.py
    │   ├── config.py               # 전역 환경설정
    │   ├── context.py              # Thread-safe 데이터 버스 (싱글톤)
    │   ├── db.py                   # SQLite DB 연동 및 테이블 스키마/CRUD
    │   └── cli_controller.py       # 로컬 Claude CLI 통신 컨트롤러 (비차단 큐)
    │
    ├── ui_common/                  # UI 공통 요소
    │   ├── __init__.py
    │   ├── tray.py                 # 시스템 트레이 아이콘 및 메뉴
    │   └── overlay.py              # 투명 오버레이 기본 윈도우 (드래그, 페이드 효과)
    │
    └── agents/                     # [수직 슬라이스 격리 구조]
        ├── stt/                    # ① STT & 오디오 슬라이스
        │   ├── __init__.py
        │   ├── stt_agent.py        # STT 비동기 스레드 (Mock 기능 포함)
        │   └── audio.py            # 마이크/루프백 오디오 캡처 유틸
        │
        ├── flow/                   # ② Flow 시각화 슬라이스
        │   ├── __init__.py
        │   ├── flow_agent.py       # 30초 주기 다이어그램 생성 스레드
        │   ├── flow_ui.py          # QWebEngineView 기반 투명 오버레이 윈도우
        │   ├── mermaid_html.py     # 로컬 HTML/CSS 템플릿
        │   └── resources/
        │       └── mermaid.min.js  # 로컬 오프라인용 라이브러리
        │
        ├── chat/                   # ③ Chat 어시스턴트 슬라이스
        │   ├── __init__.py
        │   ├── chat_agent.py       # RAG 프롬프트 병합 및 Q&A 스레드
        │   └── chat_ui.py          # 질문 입력 및 대화 히스토리 표출 윈도우
        │
        └── docs/                   # ④ Docs 최종 정리 슬라이스
            ├── __init__.py
            └── docs_agent.py       # 회의 종료 요약 및 마크다운 파일 출력 스레드
```

---

## 단계별 개발 및 ReAct 검증 방법 (Phases & ReAct Loop)

### Phase 1: 시스템 트레이 및 투명 오버레이 기본 GUI 구축
- **개발**: `prismflow/ui_common/` 및 `main.py` 구축.
- **검증**: `tests/test_ui.py`를 실행하여 윈도우 Opacity 애니메이션 속성과 프레임리스 설정이 정상적으로 세팅되는지 PySide6 위젯 속성 검사 수행.

### Phase 2: SQLite DB 구축 및 실시간 STT 에뮬레이터 설계
- **개발**: `prismflow/core/db.py` 생성 및 SQLite DB 스키마 구축. `prismflow/agents/stt/` Mock 기동 구성.
- **검증**: `pytest tests/test_db.py` 및 `pytest tests/test_stt.py`를 실행하여 DB 쓰기/읽기 속도와 Mock 대화가 큐에 스레드 세이프하게 반영되는지 검사.

### Phase 3: Claude CLI 통신 및 Flow Agent Mermaid 시각화
- **개발**: `prismflow/core/cli_controller.py` 비차단 입출력 구현 및 `prismflow/agents/flow/` 구축.
- **검증**: `pytest tests/test_cli.py` 및 `pytest tests/test_flow.py`를 실행하여 로컬 Claude CLI가 데드락 없이 응답하는지와 Mermaid 코드 파싱 유효성 검사.

### Phase 4: Chat Agent 하이브리드 RAG 및 대화창 통합
- **개발**: `prismflow/agents/chat/` 구현 및 컨텍스트 결합 로직 제작.
- **검증**: `pytest tests/test_chat.py` 실행. 모의 질문을 투하해 RAG가 N분 발화와 Mermaid 코드를 정상 추출하여 입력하는지 테스트.

### Phase 5: Docs Agent 보고서 작성 및 원클릭 실행 런처
- **개발**: `prismflow/agents/docs/` 최종 회의록 작성 모듈 및 `run.bat` 구현.
- **검증**: 전체 기능 통합 시뮬레이션을 실행하여 최종 리포트 마크다운 파일이 내문서 경로에 정상 생성되고 실행되는지 최종 확인.
