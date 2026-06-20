# PrismFlow 이어받기 핸드오프 (2026-06-21, Phase 9~10 완료 시점)

## 현재 상태 (한 줄)
`master` 브랜치, 마지막 커밋 **6cbed5f**. 테스트 **67 passed / 1 skipped**, 전체 스위트 **3회 연속 무결**(세그폴트 0). 작업 트리 클린.

## 최근 커밋
- `6cbed5f` Phase 10: 에이전트 상태 대시보드 + 녹음 인디케이터 + FlowUI 4:1:1 + 좀비 코디네이터 세그폴트 근본 해결
- `62db121` ReportAgent.cleanup GC-중-실행 QThread 크래시 하드닝
- `62bd5a6` Phase 9-3 벤치마크 + 정합/격리/세그폴트 1차 해결

## 무엇이 완료됐나
**Phase 9 (성능 50%+ & 상용화 안정화)** — 모두 [x]
- 9-1 STT: Diarization 파이프라인 핫패스 제거(발화당 무거운 추론 2→1회), 임베딩 단독 코사인 매칭.
- 9-2 Flow: 발화록 슬라이딩 윈도우(전체→최근 15개). 입력 프롬프트 71.4%↓, 추정 토큰 74.8%↓.
- 9-3 벤치마크: `tests/test_benchmark.py`가 50% 목표를 assert로 회귀 차단. 상세 `docs/phase9_benchmark_report.md`.
- 9-4 Chat: 백그라운드 Ingest 폐지(60분 회의 기동 20→0회), 지수 백오프 재시도.
- 안정화: cli_controller 재시도 계약 정비, DB WAL+busy_timeout, conftest autouse DB 격리.

**Phase 10 (오버레이 UX)** — 모두 [x]
- `core/agent_status.py` AgentStatusHub (신호 기반, 폴링 0) — 5개 에이전트 IDLE/OK/WORKING/ERROR 집계.
- `ui_common/status_panel.py` 색점+상세 뱃지 패널. `ui_common/indicators.py` `● 녹음 중` 점멸(두 오버레이 모두).
- FlowUI 세로 4:1:1 = Mermaid : 확정 전사 기록(누적, 최근 50) : 상태 패널.
- 신규 신호: FlowAgent.analysis_started/analysis_failed, ChatAgent.question_received. main.py 코디네이터가 전부 허브로 중계.

## ⚠️ 반드시 알아야 할 아키텍처 함정 (다음 세션 필독)
1. **싱글톤 시그널 누수 = 세그폴트의 진짜 원인.** `AppCoordinator`/`ChatAgent`는 `MeetingContext`(싱글톤) 시그널을 `__init__`에서 구독한다. `cleanup()`에서 **반드시 disconnect** 해야 한다. 안 하면 좀비 객체가 다음 회의에 반응해 STT(PyAudio)/Flow 스레드를 중복 생성 → access violation. **새 컨텍스트-시그널 구독자를 추가하면 cleanup에서 disconnect할 것.** conftest는 매 테스트마다 시그널 슬롯을 비워 백스톱한다.
2. **QThread 정리**: `terminate()` 대신 `wait(timeout)` 우선. 실행 중인 QThread의 파이썬 참조를 drop하면 'Destroyed while thread is still running' 크래시.
3. **테스트 DB 격리**: `tests/conftest.py`의 autouse `isolate_meeting_context`가 싱글톤 DB/문서경로를 임시로 교체한다. 없으면 화자 프로필 누수로 STT 목 테스트 플래키 + 실제 사용자 DB 오염.

## 남은 과제 / 다음 방향 (우선순위 제안)
1. **실제 실행 미세조정**: `.venv\Scripts\python.exe main.py` 실행 후 폰트/높이/색/뱃지 간격 등 시각 튜닝. (현재는 구조=테스트, 모양=목업으로만 검증됨.)
2. **i2t 해석 확정**: 화면감지기(i2t)의 "교정 DB에 정보 제공" 요구를 현재는 *화면 맥락을 컨텍스트에 전달*로 표시(`PPT pN`/`화면전환`). 교정 사전 직접 연동을 원하면 그 방향 구현.
3. **ChatUI 상태 요약**: 상태 패널은 FlowUI에만 있음. ChatUI에도 축약 상태를 노출할지 결정.
4. **(알려진 UX 결함)** `FlowAgent.stop()`/STT `stop()`이 CLI 호출 중이면 `wait()` 무한 대기 → 회의 종료 시 메인 UI 최대 30초 프리즈. *크래시 아님*. 제대로 고치려면 subprocess 중단 가능화 + 참조 안전 라이프사이클 설계 필요(설계 합의 권장).
5. **(사소)** `ChatAgent.__init__`의 `ingest_interval_ms`는 죽은 호환용 인자.

## 검증/실행 명령
- 전체 테스트: `E:\Tak\Gemini\PrismFlow\.venv\Scripts\python.exe -m pytest tests/ -p no:cacheprovider -q`
- 벤치마크(수치 출력): `... -m pytest tests/test_benchmark.py -v -s`
- 앱 실행: `E:\Tak\Gemini\PrismFlow\.venv\Scripts\python.exe main.py`

## 작업 방식 (사용자 선호)
검증 → 검증결과 → 계획 → 실행의 `/loop` 방식, 상용화 수준 품질 바, 성능 주장은 벤치마크로 증명, 증상이 아닌 근본 원인 수정, 완료된 검증 단계는 `master`에 커밋.
