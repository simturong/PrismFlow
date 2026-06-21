# PrismFlow Agent Guidebook (agent.md)

이 파일은 AI 개발 에이전트가 PrismFlow 코드를 분석하거나 수정할 때 길을 잃지 않도록 안내하는 **프로젝트 온보딩 및 내비게이션 가이드**입니다.

---

## 🧭 빠른 내비게이션 & 파일 탐색 가이드

개발하거나 소스 코드를 읽을 때 아래의 순서와 안내를 참고하여 접근하십시오.

### 1. 코드 파악을 위한 추천 읽기 순서
1. [agent.md](file:///E:/Tak/Gemini/PrismFlow/agent.md) (본 파일)을 통해 전체 디렉토리 구성과 작업 가이드를 숙지합니다.
2. [main.py](file:///E:/Tak/Gemini/PrismFlow/main.py)를 열어 전체 프로그램의 기동 흐름과 에이전트 스레드 조율 구조를 파악합니다.
3. [prismflow/core/context.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/core/context.py)를 열어 스레드 간 상태를 공유하는 싱글톤 객체 구조를 파악합니다.
4. [prismflow/core/cli_controller.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/core/cli_controller.py)를 통해 백그라운드 Claude CLI 파이프 비차단 통신 구조를 이해합니다.

### 2. 무언가를 수정하고 싶을 때 어디로 가야 하나요?

| 수정하고 싶은 기능 | 열어야 할 파일 / 폴더 | 관련 테스트 파일 |
| :--- | :--- | :--- |
| **시스템 트레이 아이콘 / 마우스 메뉴** | [prismflow/ui_common/tray.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/ui_common/tray.py) | [tests/test_ui.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_ui.py) |
| **투명 오버레이 창의 공통 스타일 (페이드 효과, 드래그)** | [prismflow/ui_common/overlay.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/ui_common/overlay.py) | [tests/test_ui.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_ui.py) |
| **SQLite 데이터베이스 / 테이블 스키마 / DB 쿼리** | [prismflow/core/db.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/core/db.py) | [tests/test_db.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_db.py) |
| **Claude CLI와 직접 파이프 연결 및 통신 방식** | [prismflow/core/cli_controller.py](file:///E:/Tak/Gemini/PrismFlow/prismflow/core/cli_controller.py) | [tests/test_cli.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_cli.py) |
| **실시간 녹음 / 음성 파일 저장 / STT 변환 / Mock 모드 변경** | [prismflow/agents/stt/](file:///E:/Tak/Gemini/PrismFlow/prismflow/agents/stt) | [tests/test_stt.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_stt.py) |
| **Mermaid 흐름도 렌더링 / QWebEngineView / 흐름도 요약 알고리즘** | [prismflow/agents/flow/](file:///E:/Tak/Gemini/PrismFlow/prismflow/agents/flow) | [tests/test_flow.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_flow.py) |
| **사용자 질문 처리 / RAG 컨텍스트 병합 / 채팅 UI 및 답변 스트리밍** | [prismflow/agents/chat/](file:///E:/Tak/Gemini/PrismFlow/prismflow/agents/chat) | [tests/test_chat.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_chat.py) |
| **회의 종료 시 최종 Markdown 보고서 생성 규칙** | [prismflow/agents/report/](file:///E:/Tak/Gemini/PrismFlow/prismflow/agents/report) | [tests/test_report.py](file:///E:/Tak/Gemini/PrismFlow/tests/test_report.py) |

---

## 🗺️ 프로젝트 트리 구조 (AI 최적화 수직 슬라이스)

```text
E:\Tak\Gemini\PrismFlow\
├── agent.md                        # 본 파일 (프로젝트 내비게이션, 코딩 규칙 가이드)
├── main.py                         # 앱 전체 진입점 (QApplication, 트레이 기동, 에이전트 조율)
├── run.bat                         # Windows 원클릭 실행 배치 스크립트
├── requirements.txt                # 프로젝트 가상환경 패키지 의존성 목록
├── build_release.py                # Portable Python 격리 패키지 빌드 자동화 스크립트
├── setup.iss                       # Inno Setup 설치파일 빌드용 스크립트
├── stt_live_test.py                # Whisper GPU/VAD 격리 실측용 라이브 테스트 스크립트
│
├── docs/                           # 산출물 보관 폴더 (정본 SSOT 보관처)
│   ├── implementation_plan.md      # [규칙 0] 각 Phase 착수 전 작성·승인받는 상세 구현 계획서(SSOT)
│   ├── task.md                     # 각 Phase 작업 완료 후 업데이트하는 전체 진행률 및 Task 상태판
│   └── history.md                  # 각 Phase 완료 시 작성하는 개발 시행착오 및 히스토리 위키
│
├── tests/                          # ReAct 검증용 단위/통합 테스트 코드 디렉토리
│   ├── __init__.py
│   ├── conftest.py                 # PyTest 공통 피스처 및 DB/CLI 모크 설정
│   ├── test_core.py                # config / context 싱글톤 및 CLI 오버라이드 검증
│   ├── test_db.py                  # SQLite CRUD 및 세션 로딩 테스트
│   ├── test_cli.py                 # Claude CLI 파이프 비차단 IO 및 에러 핸들링 검증
│   ├── test_stt.py                 # STT 스레드 및 VAD 분절, 실엔진 격리 테스트
│   ├── test_flow.py                # Mermaid 코드 생성, 노드 재사용(Upsert) 유효성 검사
│   ├── test_chat.py                # RAG 프롬프트 병합 및 응답 스트리밍 검증
│   ├── test_report.py              # 최종 회의록 Markdown 생성 및 자동 실행 테스트
│   ├── test_ui.py                  # SettingsDialog 저장/로드 UI 테스트
│   └── test_benchmark.py           # 최적화 50% 성능 목표 회귀 방지 벤치마크 테스트
│
└── prismflow/                      # 메인 패키지 루트
    ├── __init__.py
    │
    ├── core/                       # 중앙 제어 및 데이터 핵심 레이어 (Core)
    │   ├── __init__.py
    │   ├── config.py               # 전역 환경설정
    │   ├── context.py              # Thread-safe 데이터 버스 (싱글톤)
    │   ├── db.py                   # SQLite DB 연동 및 테이블 스키마/CRUD
    │   ├── cli_controller.py       # 로컬 Claude CLI 통신 컨트롤러 (비차단 큐)
    │   ├── agent_status.py         # 5대 에이전트 상태(IDLE/OK/WORKING/ERROR) 집계/배포 허브
    │   ├── cli_activity.py         # Claude CLI 요청/응답 디버그 로그 추적 허브
    │   ├── screen_detector.py      # [i2t 화면감지] PPT 슬라이드 COM 및 범용 MSE 화면 전환 감지
    │   └── glossary.py             # [i2t 용어집교정] 화면 추출 키워드 기반 STT 오인식 교정
    │
    ├── ui_common/                  # UI 공통 레이아웃/리소스
    │   ├── __init__.py
    │   ├── tray.py                 # 시스템 트레이 메뉴 관리
    │   ├── overlay.py              # 드래그/반투명 애니메이션 오버레이 베이스 클래스
    │   ├── settings_ui.py          # 설정 다이얼로그 (Mock 토글, HF 토큰, 가속, 모델 크기)
    │   ├── status_panel.py         # 5대 에이전트 상태 및 교정 DB 현황 실시간 패널
    │   ├── indicators.py           # 녹음 중 빨간 점멸 인디케이터 (오버레이 통합)
    │   └── cli_log_window.py       # CLI 요청/응답 디버그 로그 실시간 표출 창
    │
    ├── resources/                  # 로컬 가중치 모델 등 오프라인 리소스
    │   └── models/
    │       └── whisper-small-int8-ov/  # 로컬 오프라인 실행용 OpenVINO Whisper 번들 모델
    │
    └── agents/                     # [수직 슬라이스 격리 구조 - 토큰 최적화용 에이전트 목록]
        ├── stt/                    # ① STT & 오디오 에러 제어 에이전트
        │   ├── __init__.py
        │   ├── stt_agent.py        # STT 비동기 스레드 (OpenVINO Whisper + pyannote)
        │   └── audio.py            # 마이크/루프백 오디오 캡처 유틸
        │
        ├── flow/                   # ② Flow 시각화 에이전트
        │   ├── __init__.py
        │   ├── flow_agent.py       # 3-way 동적 트리거 Mermaid 다이어그램 생성 스레드
        │   ├── flow_ui.py          # QWebEngineView 기반 반투명 흐름도 오버레이 윈도우
        │   ├── mermaid_html.py     # 로컬 HTML/CSS 템플릿
        │   └── resources/
        │       └── mermaid.min.js  # 로컬 오프라인용 라이브러리
        │
        ├── chat/                   # ③ Chat 어시스턴트 에이전트
        │   ├── __init__.py
        │   ├── chat_agent.py       # RAG 프롬프트 병합 및 Q&A 스레드 (One-shot)
        │   └── chat_ui.py          # 질문 입력 및 대화 히스토리 표출 윈도우
        │
        └── report/                 # ④ Report 최종 회의록 보고서 에이전트
            ├── __init__.py
            └── report_agent.py     # 회의 종료 시 Opus 4.8 회의록 컴파일 및 마크다운 파일 출력 스레드
```

---

## 🛠️ 핵심 코딩 및 에이전트 개발 수칙

> **Karpathy 4원칙** — 모든 코드 작성/수정 시 반드시 준수
> 1. 짐작으로 코딩하지 말 것 — 가정은 사용자에게 먼저 확인
> 2. 최소한의 코드만 작성 — 요구되지 않은 기능 추가·오버엔지니어링 금지
> 3. 외과적 수정 — 문제 부분만 건드리고 무관한 코드를 임의 리팩토링하지 말 것
> 4. 목표가 완벽히 검증될 때까지 확실하게 — 애매하게 넘기지 말 것

### 🚦 [규칙 0] Phase 진행 게이트 (필독·최우선, 다른 모든 규칙에 우선)

새로운 Phase(또는 기존 Phase의 범위 확장)에 **착수하기 전**, 아래 3단계를 **순서대로** 반드시 수행한다.

1. **계획 선작성** — `docs/implementation_plan.md`에 해당 Phase의 상세 구현 설계를 먼저 작성/업데이트한다. (기존 구조 보존·덧붙이기. 절대 덮어쓰기 금지 — [규칙 5] 참조.)
2. **승인 획득** — 그 계획을 사용자에게 제시하고 **명시적 승인(approval)** 을 받는다. **승인 전에는 구현 코드를 작성하지 않는다.**
3. **착수** — 승인된 뒤에만 구현·검증을 시작한다.

**Phase 마감 시**(완료 선언 직전)에도 순서가 있다: ① `docs/history.md` 선행 작성([규칙 6]) → ② `docs/task.md`·`docs/implementation_plan.md` 동기화([규칙 4·5]) → ③ 완료(✅/[x]) 선언.

**범위 구분(애매함 제거)**:
- *새 Phase / 새 기능 / 범위 확장* → 위 게이트를 **반드시** 거친다.
- *이미 승인된 Phase 범위 안의 작은 버그픽스·외과적 수정* → 별도 승인 없이 진행 가능(단, 완료 시 task.md 갱신).

**예외와 그 한계(중요)**: 사용자가 특정 세션에서 명시적으로 "승인 없이 루프로 진행"(예: `/loop`, "허락 없이 진행")을 지시한 경우에 **한해** 2단계(승인)를 생략할 수 있다. **그러나 그 경우에도** `implementation_plan.md`·`task.md`·`history.md`의 단계별 동기화([규칙 4·5·6])는 **면제되지 않는다.** 즉, 승인을 생략하더라도 계획·진행·역사 문서는 Phase마다 반드시 최신으로 유지한다.

---

1. **최소한만 읽고 고치십시오 (Context Splitting)**:
   - 특정 기능(예: Chat)을 수정할 때는 해당 `prismflow/agents/chat/` 폴더 하위 파일들과 공통 인터페이스만 조회하십시오. 다른 기능 폴더는 무분별하게 읽어 컨텍스트 토큰을 낭비하지 마십시오.
2. **ReAct 검증을 즉시 돌리십시오**:
   - 코드를 한 단락 작성하면 바로 터미널에서 관련 테스트 코드([tests/](file:///E:/Tak/Gemini/PrismFlow/tests))를 실행하십시오 (`pytest tests/test_xxx.py`).
   - 테스트 검증을 통과한 뒤에만 사용자에게 보고하고 다음 단계로 진행합니다.
3. **개발 히스토리 위키 작성 (`docs/history.md`)**:
   - **매 Phase 개발 단계가 완료될 때마다** [docs/history.md](file:///E:/Tak/Gemini/PrismFlow/docs/history.md)를 반드시 업데이트해야 합니다.
   - 업데이트 시 발생한 시행착오(Trial & Error), 대안 비교, 블로커 상황 및 교훈(Lesson Learnt)을 **스토리텔링** 형식으로 작성하여 보관하십시오.
4. **실시간 Task 업데이트 (`docs/task.md`)**:
   - **개발 진행 중 및 각 Phase 내 단계별 완료 시마다** [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md)를 즉시 실시간으로 업데이트해야 합니다 (예: 진행 중 `[/]`, 완료 `[x]`).
   - 전체 개발이 끝난 뒤 한꺼번에 업데이트하지 말고, 현재 진행 상황을 외부에서도 즉각 파악할 수 있도록 단계별 진행 즉시 상태를 갱신하십시오.
5. **계획서 점진적 업데이트 (`docs/implementation_plan.md`)**:
   - 구현 계획서를 업데이트할 때 **전체 마일스톤이나 타 Phase 계획을 덮어써서 삭제하지 마십시오**.
   - 반드시 기존 계획 구조를 보존한 채로, 해당 Phase 영역에 세부 기술 설계 및 내용을 점진적으로 덧붙여야 합니다.
   - **Phase 내 계획 수정이 이루어질 경우, 이에 종속성이 있는 다른 구성요소(예: `task.md`, `tests/` 구성, 관련 API 매핑 등)도 반드시 식별하여 동시 업데이트를 보장해야 합니다.**
   - **다이렉트 협의 의무**: 기획 및 설계 단계에서 사용자와 확정 논의를 거칠 때는 아티팩트 폴더에 임시 드래프트 계획서를 따로 작성하지 않고, 곧바로 프로젝트 내의 [docs/implementation_plan.md](file:///E:/Tak/Gemini/PrismFlow/docs/implementation_plan.md)를 직접 실시간으로 편집/수정해가며 사용자와 싱크를 조율합니다.
   - **승인 요청 전 상세화 의무**: 사용자의 최종 승인(Proceed)을 구하기 위해 대기하기 전, 구현에 사용될 모든 세부 기술 설계 명세(비차단 입출력 버퍼링, COM API 연동, 30초 Debounce 캡처 로직 등)가 프로젝트 내 `docs/implementation_plan.md`에 파편화 없이 구체적이고 꼼꼼하게 기술 완료되어 있어야 합니다. 상세 사양이 생략된 뼈대 계획만으로 성급하게 승인을 요구하는 행위는 엄격히 금지됩니다.
6. **문서 동기화 및 마감 엄격 규칙 (Document Sync & Closeout Rules)**:
   - **단일 정본(SSOT) 원칙**: `docs/task.md`와 `docs/implementation_plan.md`가 **유일한 정본**입니다. 별도의 복제본을 만들어 이중 관리하지 **마십시오**.
   - **역사서 선행 마감**: 임의의 개발 Phase를 '완료(✅ 완료 또는 [x])' 처리하여 최종 보고하기 직전, 반드시 [docs/history.md](file:///E:/Tak/Gemini/PrismFlow/docs/history.md)에 해당 Phase 동안의 상세 개발 내역, 시행착오(Trial & Error), 대안 비교, 블로커 극복 과정을 **선행 작성** 완료한 뒤 완료 선언을 해야 합니다. 역사서 작성 누락은 절대 허용되지 않습니다.
   - **계획 변경과 Task 동시 반영**: 구현 도중 설계 및 계획의 추가나 수정이 발생하면, 이에 연동되는 [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md)의 세부 할 일 목록도 즉시 구조적으로 동기화하여 변경해야 합니다.
   - **Handoff 문서 작성 금지**: AI 에이전트는 세션 전환이나 마감 시 `Handoff` 스킬 등을 통해 인계 파일(`handoff_*.md`)을 생성하거나 관리하지 않습니다. 이 지침은 글로벌 스킬의 자동화 로직보다 우선합니다. 진행 상황 및 역사 관리는 오직 `docs/` 내의 3대 문서로만 엄격히 통제합니다.
   - **.agents/ 폴더 및 AGENTS.md 생성 금지**: 프로젝트 내에 커스텀 규칙 폴더(`.agents/`)나 `AGENTS.md` 파일을 임의로 생성하거나 작성하지 마십시오. 모든 커스텀 규칙과 프로젝트 운영 수칙은 오직 루트의 `agent.md` 단일 파일로만 통합 관리합니다.

