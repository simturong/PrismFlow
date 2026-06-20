# Handoff: PrismFlow E2E Hardening & Phase 7 Transition (2026-06-20)

## 1. 진행 상황 (Progress)
*   **Claude CLI Code 1 에러 근본 진단**: E2E E2E 구동 시 발생한 `Claude CLI execution failed (Code 1)` 장애의 원인이 Claude CLI 사용량 한도 초과(`You've hit your session limit`)임을 실제 CLI 인자 직접 실행을 통해 검출 완료하였습니다.
*   **Phase 7 / Phase 8 로드맵 스왑 및 재설계**:
    *   오프라인 패키징 및 배포 단계를 **Phase 8**로 순연하고, **Phase 7**을 **E2E 통합 하네스 구축 및 예외 하드닝(E2E 특집)**으로 전면 개편하였습니다.
    *   [docs/implementation_plan.md](file:///E:/Tak/Gemini/PrismFlow/docs/implementation_plan.md) 및 [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md) 정본을 즉시 수정 및 동기화하였습니다.
*   **보강된 Phase 7 세부 기술 설계 명세**:
    *   **WAV/TXT 영구 보존**: 전체 마이크 입력을 백그라운드에서 실시간으로 `.wav` 원본 음성 파일로 아카이빙하고, 전사 완료 시 실시간 `.txt` 전사록 파일에 추가 기입하도록 설계.
    *   **Flow Agent Delta 업데이트**: 30초마다 전체 전사록을 보내지 않고 `--resume <UUID>` 세션을 유지하여 **추가 발화만 증분 전달**하도록 설계 (레이턴시 및 입력 토큰 감소).
    *   **이미지/맥락 중요도 규칙**: 첨부 이미지 존재 시 핵심 노드로 중요도를 부여하고, 대화의 주제 전환 감지 시 Mermaid 다이어그램을 신규 교체하는 규칙 프롬프트 명문화.
    *   **I2T 에이전트 (Image-to-Text Agent) 신설**: 화면 발표 자료/이미지가 캡처되면 비동기 백그라운드에서 Claude 멀티모달 CLI를 통해 핵심 의제와 키워드를 추출하여 DB `screen_context`에 보관 및 Flow 프롬프트 배경 정보로 주입.
    *   **로컬 자가 개선 루프**: 사용자가 수정한 텍스트 및 화자 정보에 기반해 STT 출력 전 실시간 패턴을 치환 정정하는 `correction_dictionary`(사용자 정의 교정 사전) 및 화자 프로필 캐시 매핑 실질화.
*   **TOC 목차 추가**: 탐색 편의성을 위해 구현 계획서 상단에 GFM 앵커 링크 목차(Index)를 성공적으로 삽입하였습니다.

## 2. 실패한 접근 방식 & 교훈 (Trial & Error)
*   *이전 접근*: Claude CLI의 에러가 비차단 파이프나 매개변수 UUID 충돌 때문이라고 단순 추측하여 파라미터 격리에 치중했으나, 실제 Exit Code 1은 누적 사용 한도 초과(`session limit`) 경고 메시지 때문이었음을 터미널 수동 실행을 통해 직접 검출하였습니다.
*   *교훈*: 섣부른 추정 대신, 실패한 subprocess 인자와 출력 스트림(stderr)을 즉시 덤프해 보거나 수동 샌드박스에서 재현해 확인하는 것이 가장 빠르고 유일한 팩트 체크 수단입니다.

## 3. 현재 직면한 문제 (Blockers)
*   **Claude CLI 사용량 제한**: 현재 CLI 세션 사용량이 초과되어 리셋 시점까지 실서버 API 호출은 에러 코드 1이 발생합니다.
*   **영향 및 해결책**: E2E 시나리오를 정상 테스트하기 위해, 세션 리밋 상황에서도 로컬 룰베이스나 정적 Markdown으로 흐름을 이어가며 UI가 죽지 않는 **Fallback 모드**를 설계했으며, 다음 세션에서 7-2, 7-3 단계를 구현하면서 이를 우선적으로 극복할 예정입니다.

## 4. 다음 세션 구체적 목표 (Next Goals)
1.  **[7-1] E2E 통합 테스트 하네스 (`tests/e2e_harness.py`) 구축**: VAD 감지 모크 및 가상 오디오 공급, Claude CLI 장애 강제 주입을 통해 전체 10초 주기의 E2E 테스트 시뮬레이션 환경 마련.
2.  **[7-2] 세션 리밋 상황 식별 및 UI 연동**: Claude CLI 실패 시 stderr를 분석해 `session limit`을 식별하고 사용자 UI(QMessageBox, 상태바)에 알림.
3.  **[7-3] CLI 로컬 Fallback(대체) 모드 구현**: API 먹통 상황 시 룰베이스 Mermaid 렌더링, 가상 답변, 정적 MD 리포트를 작성해 안전하게 오프라인 백업이 작동하도록 구현.
4.  **[7-4 ~ 7-7] WAV/TXT 실시간 기록, Delta Flow 업데이트, I2T Agent 신설 및 교정 사전 연동** 개발 순차적 진행.

---

## 5. 다음 세션 이어받기 프롬프트 (Handoff Prompt)
```text
[PrismFlow E2E 특집 Phase 7 계속 진행]
이전 세션에서 Claude CLI의 Code 1 에러가 사용량 한도 초과(session limit · resets 1:10am)에 의한 것임을 진단하고, 로드맵을 스왑하여 Phase 7을 E2E 검증, 예외 하드닝 및 CLI Fallback 모드 특집 단계로 전면 개편하였습니다.

현재 정본 문서인 [docs/implementation_plan.md](file:///E:/Tak/Gemini/PrismFlow/docs/implementation_plan.md) 및 [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md)에 TOC 목차와 Phase 7의 상세 기술 명세(Delta Flow 업데이트 규칙, 독립 I2T 에이전트, 실시간 WAV/TXT 저장, 사용자 교정 사전 기반 자가 개선 루프 등)를 모두 반영하고 아티팩트 동기화까지 마쳤습니다.

다음 세션에서는 [docs/task.md](file:///E:/Tak/Gemini/PrismFlow/docs/task.md)의 Phase 7 체크리스트 순서에 맞추어 작업을 시작하십시오:
1. `tests/e2e_harness.py` 파일을 생성하여, 가상의 오디오 프레임 공급 및 Claude CLI의 session limit 실패(Exit Code 1) 장애 주입 상태에서 E2E 회의 흐름을 10초 주기로 반복 검출하는 E2E 시나리오 테스트 하네스 개발을 개시하십시오.
2. `pytest tests/ -vv`로 전체 회귀 테스트가 계속 녹색을 유지하도록 보장하십시오.
```
