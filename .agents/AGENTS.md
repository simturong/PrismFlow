# PrismFlow Project Custom Rules

## 1. 구현 계획서(SSOT) 관리 및 합의 프로세스 규칙
- **정본(Single Source of Truth) 정의**: 프로젝트의 상세 구현 설계서인 `implementation_plan.md`는 프로젝트 디렉토리 내 [docs/implementation_plan.md](file:///E:/Tak/Gemini/PrismFlow/docs/implementation_plan.md)가 유일한 정본(SSOT)입니다.
- **다이렉트 협의 의무**: 기획 및 설계 단계에서 사용자와 확정 논의를 거칠 때는 **아티팩트 폴더에 임시 드래프트 계획서를 따로 작성하지 않고, 곧바로 프로젝트 내의 [docs/implementation_plan.md](file:///E:/Tak/Gemini/PrismFlow/docs/implementation_plan.md)를 직접 실시간으로 편집/수정해가며 사용자와 싱크를 조율**합니다.
- **승인 요청 전 상세화 의무**: 사용자의 최종 승인(Proceed)을 구하기 위해 대기하기 전, 구현에 사용될 모든 세부 기술 설계 명세(비차단 입출력 버퍼링, COM API 연동, 30초 Debounce 캡처 로직 등)가 프로젝트 내 `docs/implementation_plan.md`에 파편화 없이 구체적이고 꼼꼼하게 기술 완료되어 있어야 합니다. 상세 사양이 생략된 뼈대 계획만으로 성급하게 승인을 요구하는 행위는 엄격히 금지됩니다.

## 2. 작업 상태판(task.md) 관리 규칙
- Phase 진입 및 완료 시 [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md)와 아티팩트 `task.md`를 상시 업데이트하여 진행 현황을 실시간 보고해야 합니다.
