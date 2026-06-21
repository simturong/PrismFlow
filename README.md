# PrismFlow — AI 회의 어시스턴트

> **English summary** — PrismFlow is an offline-first Windows meeting assistant that lives in the system tray. It transcribes speech in real time (OpenVINO Whisper + pyannote speaker diarization), visualizes the meeting as a live Mermaid flowchart, answers context-aware questions, and auto-generates a structured meeting report — all driven by the **local Claude CLI** as a subprocess, with no cloud backend of its own. Built with PySide6 translucent overlays. Korean-language UI. See the sections below for details.

PrismFlow는 **시스템 트레이에 상주하는 오프라인 우선 AI 회의 어시스턴트**입니다. 회의 음성을 실시간으로 전사하고, 대화의 흐름을 실시간 흐름도로 시각화하며, 맥락 기반 Q&A에 답하고, 회의가 끝나면 구조화된 회의록을 자동 생성합니다. 모든 지능은 **로컬 Claude CLI**(서브프로세스)가 담당하며, 자체 클라우드 서버 없이 동작합니다.

---

## ✨ 주요 기능

| 에이전트 | 역할 | 모델 |
| :--- | :--- | :--- |
| **STT** | 실시간 음성 전사 + 화자분리(전역 일관 매칭) | OpenVINO Whisper + pyannote 4.x |
| **Flow** | 대화를 실시간 Mermaid 흐름도(블록도)로 시각화 | Claude Haiku |
| **Chat** | 회의 맥락 기반 Q&A + 웹 검색·작업 폴더 파일 도구 | Claude Haiku |
| **Report** | 회의 종료 시 구조화된 Markdown 회의록 자동 생성 | Claude Opus |
| **i2t (화면감지)** | PPT 슬라이드/화면 전환 감지 → 맥락 + STT 교정 용어집 | win32com + Pillow |

추가 특징:
- **반투명 글래스 오버레이** 2종 — `PrismFlow Agent`(흐름도·전사·에이전트 상태), `PrismFlow Chat Agent`(회의 Q&A). 드래그 이동·크기조절·투명도 슬라이더·호버 페이드.
- **에이전트 상태 대시보드** — 5개 엔진의 동작 상태를 신호 기반(폴링 0)으로 실시간 표시.
- **화면 용어집 STT 교정** — 발표 슬라이드의 정확한 표기를 읽어 음성인식 근접 오인식을 보수적으로 자동 교정.
- **CLI 디버그 로그 창** — 백그라운드 에이전트가 Claude CLI와 주고받는 프롬프트/응답을 실시간 관찰(개발용).
- **오프라인 우선** — STT/화자분리 모델을 로컬 번들로 로드(`HF_HUB_OFFLINE`), Claude CLI도 로컬 실행.

---

## 🏗️ 아키텍처

기능 단위 **수직 슬라이스(Vertical Slice)** 구조로, 각 에이전트의 UI·스레드·로직을 한 폴더에 격리합니다.

```
prismflow/
├── core/                  # 공용 코어
│   ├── context.py         # MeetingContext 싱글톤(스레드 세이프 상태 + Qt 시그널)
│   ├── db.py              # SQLite 매니저(세션/전사/채팅/화면로그/흐름이력/용어집)
│   ├── cli_controller.py  # 로컬 Claude CLI 비차단 래퍼(세션 관리·도구·강제중단)
│   ├── cli_activity.py    # CLI 주고받기 활동 로그 허브(디버그 창용)
│   ├── agent_status.py    # 5-에이전트 상태 집계 허브
│   ├── glossary.py        # 화면 용어집 추출 + STT 근접 보정
│   ├── screen_detector.py # i2t: PPT 슬라이드/화면 전환 감지
│   └── config.py          # AppConfig(경로·STT·모델 설정, DB 오버라이드)
├── agents/
│   ├── stt/   flow/   chat/   report/   # 에이전트별 워커 + UI
└── ui_common/             # overlay, indicators, status_panel, tray, settings, cli_log_window
main.py                    # AppCoordinator: 회의 라이프사이클 오케스트레이션
```

---

## 🚀 설치 및 실행 (Windows)

> **요구사항**: Windows 10/11, Python 3.11, 로그인된 **Claude CLI**(`claude`), (선택) 화자분리용 `HF_TOKEN`.

```bat
:: 1) 가상환경 + 의존성
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

:: 2) 실행 (둘 중 하나)
run.bat
:: 또는
.venv\Scripts\python.exe main.py
```

- STT 모델 가중치(`prismflow/resources/models/`)는 용량 문제로 저장소에 포함되지 않습니다. 최초 1회 다운로드되거나 배포 빌드에 번들됩니다.
- 화자분리(pyannote)는 게이트 모델 약관 동의 + `HF_TOKEN`이 필요합니다. **토큰이 없으면 단일 화자로 graceful 동작**합니다.
- 실행하면 트레이 아이콘이 뜹니다. 우클릭 메뉴에서 **회의 시작/종료**, 창 표시, CLI 디버그 로그, 설정에 접근합니다.

---

## 🧪 테스트

```bat
.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q
```

- 성능 목표(50%+ 절감)는 `tests/test_benchmark.py`가 `assert`로 회귀를 차단합니다.
- STT 실엔진 라이브 테스트는 `STT_LIVE=1` 옵트인입니다.

---

## 📦 배포 (포터블/인스톨러)

```bat
:: 인터넷 없는 PC에서도 도는 자기완결형 포터블 빌드
python build_release.py
:: Inno Setup 단일 설치 파일
python build_release.py --installer   :: 또는 ISCC.exe setup.iss
```

---

## 🔒 개인정보 / 동작 방식

- 음성·전사·회의록은 **로컬 SQLite와 `Documents/PrismFlow/`** 에만 저장됩니다.
- AI 처리는 **로컬에 설치된 Claude CLI**가 수행합니다(PrismFlow 자체 서버 없음). 채팅의 범용 작업 도구(웹 검색·파일 읽기/쓰기/이동)는 사용자가 지정한 **작업 폴더로 샌드박스**됩니다.

---

## 📜 라이선스

[MIT License](LICENSE) © 2026 PrismFlow Project

---

## 🗺️ 개발 역사

상세한 개발 여정·의사결정·시행착오는 [`docs/history.md`](docs/history.md)에 위키 형식으로 기록되어 있습니다.
