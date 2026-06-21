"""Claude CLI 입출력 활동 로그 허브 (개발 디버깅용).

각 에이전트(Flow·Chat·Report)는 백그라운드에서 서로 다른 CLI 세션으로 claude를 호출한다.
이 허브는 그 호출의 프롬프트/응답을 한 곳에 모아 신호로 방출하여, 디버그 창(CliLogWindow)이
"지금 어떤 에이전트가 CLI에 무엇을 주고받는지"를 실시간으로 보여줄 수 있게 한다.

설계 메모:
- ClaudeCLIController는 워커 스레드(QThread)에서 실행되므로, 여기서 방출하는 신호는 GUI 스레드의
  슬롯에 큐 연결(자동)로 안전하게 전달된다.
- 기록은 best-effort다. 허브가 없거나 예외가 나도 CLI 실행 자체를 절대 방해하면 안 된다(호출부에서 try/except).
- 메모리 상한을 두어(_MAX_ENTRIES) 장시간 회의에서도 누적 비용을 제한한다.
"""
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# 보관할 최대 엔트리 수 (메모리/렌더 비용 상한)
_MAX_ENTRIES = 300


def agent_label_for_session(session_id) -> str:
    """원본(정규화 이전) 세션명 접두사로 호출 주체 에이전트를 식별한다."""
    s = str(session_id or "")
    if s.startswith("flow-session"):
        return "Flow"
    if s.startswith("chat-session"):
        return "Chat"
    if s.startswith("report-session"):
        return "Report"
    if s.startswith("agent-session"):
        return "Agent"  # 범용(도구 사용) 어시스턴트 모드
    return "CLI"


class CliActivityLog(QObject):
    """CLI 호출 1건(요청+응답 또는 오류)을 기록하고 구독자에게 방출하는 허브."""

    # 엔트리 dict: {agent, session, model, kind('ok'|'error'), prompt, response}
    entry_added = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []

    def _push(self, session_id, model, kind: str, prompt: str, response: str):
        import datetime
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "agent": agent_label_for_session(session_id),
            "session": str(session_id or ""),
            "model": str(model or "-"),
            "kind": kind,
            "prompt": prompt or "",
            "response": response or "",
        }
        self._entries.append(entry)
        if len(self._entries) > _MAX_ENTRIES:
            # 가장 오래된 항목부터 버려 상한을 유지한다.
            self._entries = self._entries[-_MAX_ENTRIES:]
        self.entry_added.emit(entry)

    def record_request(self, session_id, model, prompt: str):
        """요청(입력)을 호출 즉시 기록한다 → 응답이 오기 전에도 디버그 창에 실시간으로 보인다."""
        self._push(session_id, model, "request", prompt, "")

    def record_response(self, session_id, model, response: str, kind: str = "ok"):
        """응답(출력) 또는 오류를 완료 시점에 기록한다. kind는 'ok' 또는 'error'."""
        self._push(session_id, model, "error" if kind == "error" else "response", "", response)

    def record(self, session_id, model, prompt: str, response: str, kind: str = "ok"):
        """완료된 CLI 교환 1건(요청+응답)을 한 엔트리로 기록한다(하위호환)."""
        self._push(session_id, model, kind if kind in ("ok", "error") else "ok", prompt, response)

    def entries(self) -> list:
        """현재까지 보관된 엔트리 사본을 반환한다(창 초기 로드용)."""
        return list(self._entries)

    def clear(self):
        self._entries.clear()


# 프로세스 전역 단일 인스턴스 (생산자=CLI 컨트롤러, 소비자=디버그 창이 공유)
_INSTANCE = None


def get_cli_activity_log() -> CliActivityLog:
    """전역 CliActivityLog 싱글톤을 반환한다(없으면 생성)."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = CliActivityLog()
    return _INSTANCE
