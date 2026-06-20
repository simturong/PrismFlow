# PrismFlow 이어받기 핸드오프 (2026-06-21 세션 2, Phase 11 = 앱 실행 UX 수정)

## 현재 상태 (한 줄)
`master`, 마지막 커밋 **5d4e96b**. 테스트 **75 passed / 1 skipped**, 전체 스위트 **3회 연속 무결**(세그폴트 0), 실제 앱 구동 스모크 rc=0. 작업 트리 클린.

## 이번 세션 커밋 (Phase A~D)
- `5c1477e` Phase A 오버레이 UX: 녹음표시 우상단 이동, 항상위 해제, 투명도 슬라이더, 흐름도 성장 리사이즈
- `4e64918` Phase B Flow 실시간성: 버스트 트리거(15초 정기 + 8초 주제전환 바닥)
- `8b4ccb3` Phase C CLI 디버그 로그 창 (백그라운드 에이전트 ↔ claude 주고받기)
- `5d4e96b` Phase D Assistant 회의정보 스트립 + 범용 도구 모드 토글

## 사용자 요청(P1~P8) 처리 결과 — 전부 완료
1. **P1 녹음중 위치**: 좌상단 → 우상단 컨트롤 묶음(최소화 버튼 왼쪽)으로 이동.
2. **P2 항상 위 해제**: `TranslucentOverlay`에서 `WindowStaysOnTopHint` 제거 → 두 오버레이 모두 다른 창에 z-order 양보.
3. **P3 투명도 슬라이더**: 녹음표시 옆 20~100% 슬라이더. 기본(rest) 투명도 설정, hover 시 항상 더 또렷.
4. **P4 흐름도 4/6 성장**: `status_panel.setMaximumHeight(112)` → 세로 확대 시 Mermaid가 공간 흡수.
5. **P5 흐름도 실시간성**: `FlowAgent._should_trigger` 순수함수 — 최초 즉시 / 주제전환(발화 3개↑) 8초 바닥 즉시 / 정기 15초. 저장 위치 = `MeetingContext.current_mermaid_code`(라이브) + DB `flow_history`(스냅샷).
6. **P6 CLI 디버그 창**: `core/cli_activity.py`(허브) + `ui_common/cli_log_window.py`. 트레이 "CLI 디버그 로그 (개발용)". Flow/Chat/Report/Agent 색 뱃지 + 필터.
7. **P7 회의정보**: PrismFlow Assistant 상단에 회의정보 스트립(세션·발화 수·화자 수·상태). 코디네이터가 갱신.
8. **P8 범용 도구 모드**: Assistant에 모드 토글(회의 Q&A ↔ 범용 작업). 범용 = 웹 검색 + 작업폴더 파일 도구. (사용자 결정: 새 창 X, 기존 창에 모드 추가 / 작업폴더 샌드박스.)

## ⚠️ 반드시 알아야 할 함정 (이전 + 신규)
1. **싱글톤 시그널 누수 = 세그폴트**(이전과 동일). **신규 주의**: 회의정보 스트립은 ChatUI가 컨텍스트 시그널을 직접 구독하지 *않고*, AppCoordinator의 기존 핸들러가 `chat_ui.set_meeting_info(...)`로 밀어준다. 이 구조를 유지할 것(ChatUI에 새 컨텍스트 구독을 추가하면 좀비-세그폴트 위험 재발).
2. **P8 샌드박스는 소프트 샌드박스**: `cwd` + `--add-dir` + `--allowedTools` 화이트리스트로 작업폴더에 묶지만 OS 차원 격리는 아님(Bash 절대경로는 탈출 가능). 개인 데스크톱 보조용으로 수용. 권한 확장 시 재검토.
3. **CLI 활동 로그는 best-effort**: `cli_controller._log_activity`는 모든 예외를 삼킨다(실행 방해 금지). 단위 테스트 의존성 없이 lazy import.
4. QThread `wait()` 규칙, conftest DB 격리 — 이전과 동일.

## 남은 과제 (사용자 선택 — "원하는 것 지정 가능")
- **(설계 결정 필요)** 회의 종료 시 `FlowAgent.stop()`/STT `stop()`의 무한 `wait()`가 CLI 호출 중이면 메인 UI 최대 ~30초 프리즈(크래시 아님). 제대로 고치려면 subprocess 중단 가능화 + 참조 안전 라이프사이클 → 설계 합의 권장.
- i2t "교정 DB 연동" 해석 확정(현재는 화면 맥락 전달 방식).
- ChatUI에 축약 에이전트 상태 노출 여부 결정.
- Phase 10 오버레이 시각 추가 미세조정(폰트/뱃지 간격) — 필요 시.

## 검증/실행 명령
- 전체 테스트: `E:\Tak\Gemini\PrismFlow\.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`
- 앱 실행: `E:\Tak\Gemini\PrismFlow\.venv\Scripts\python.exe main.py`
- 범용 모드 작업폴더: `~/Documents/PrismFlow/Workspace`

## 작업 방식 (사용자 선호)
검증 → 검증결과 → 계획 → 실행의 `/loop`, 상용화 수준 품질 바, 성능은 벤치마크/실측으로 증명, 증상이 아닌 근본 원인 수정, 완료 단계는 `master`에 커밋.
