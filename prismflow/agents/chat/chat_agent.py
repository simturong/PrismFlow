import threading
import time
import logging
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal
from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.config import AppConfig

logger = logging.getLogger(__name__)

# claude CLI를 코딩 에이전트가 아닌 "회의 어시스턴트"로 동작시키기 위한 시스템 프롬프트.
# (프로젝트 CLAUDE.md/메모리는 cli_controller의 격리 실행으로 차단되며, 이 프롬프트로 페르소나를 고정)
CHAT_SYSTEM_PROMPT = (
    "당신은 PrismFlow 회의 어시스턴트입니다. 회의 발화 맥락에만 근거하여 사용자 질문에 "
    "한국어로 간결하고 정확하게 답하십시오. 코드 작업·파일 수정·도구 사용을 하지 말고 "
    "텍스트로만 답하며, 회의에 없는 내용은 추측하지 마십시오."
)

# 범용(도구 사용) 어시스턴트 모드의 페르소나. 웹 검색과 작업 폴더 내 파일 도구 사용을 허용한다.
AGENT_SYSTEM_PROMPT = (
    "당신은 PrismFlow의 범용 데스크톱 작업 어시스턴트입니다. 한국어로 답하며, 필요하면 "
    "웹 검색(WebSearch)과 작업 폴더 내 파일 도구(읽기/쓰기/수정/이동)를 사용해 사용자의 일을 직접 수행하십시오. "
    "파일 작업은 반드시 지정된 작업 폴더(작업 디렉토리) 안에서만 수행하고, 그 밖의 경로는 건드리지 마십시오. "
    "작업을 마치면 무엇을 했는지 간결히 보고하십시오."
)

# 범용 모드에서 사전 승인할 도구 화이트리스트 (최소 권한). 파일 이동/복사는 작업 폴더 기준 상대 경로로 수행됨.
AGENT_ALLOWED_TOOLS = [
    "WebSearch", "Read", "Write", "Edit", "Glob", "Grep",
    "Bash(mv:*)", "Bash(cp:*)", "Bash(mkdir:*)", "Bash(ls:*)",
]
# 범용 모드 모델: 도구 활용(웹·파일)이 잦으므로 Haiku보다 도구 추론이 강한 Sonnet을 사용.
AGENT_MODEL = "claude-sonnet-4-6"
CHAT_MODEL = "claude-haiku-4-5"

# Chat Agent 동작 모드
MODE_MEETING = "meeting"   # 회의 발화 기반 Q&A (도구 금지, 기본)
MODE_AGENT = "agent"       # 범용 작업 (웹 검색 + 작업 폴더 내 파일 도구)


class ChatQNAWorker(QThread):
    """비동기 방식으로 Claude CLI를 실행하여 답변을 스트리밍하는 스레드.

    회의 Q&A 모드(기본)는 도구 없이 순수 텍스트로 답하고, 범용 모드는 도구 화이트리스트와
    작업 폴더 샌드박스를 받아 웹 검색·파일 작업을 수행한다.
    """
    token_delivered = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, cli_controller: ClaudeCLIController, prompt: str, session_id: str, cli_lock: threading.Lock,
                 system_prompt: str = CHAT_SYSTEM_PROMPT, model: str = CHAT_MODEL, session_prefix: str = "chat-session",
                 allowed_tools=None, work_dir: Optional[str] = None, permission_mode: Optional[str] = None):
        super().__init__()
        self.cli_controller = cli_controller
        self.prompt = prompt
        self.session_id = session_id
        self.cli_lock = cli_lock
        self.system_prompt = system_prompt
        self.model = model
        self.session_prefix = session_prefix
        self.allowed_tools = allowed_tools
        self.work_dir = work_dir
        self.permission_mode = permission_mode
        self.final_response = ""

    def run(self):
        try:
            with self.cli_lock:
                # 회의 Q&A 모드에서는 도구 인자를 일절 전달하지 않아 기존 호출 시그니처를 100% 유지한다.
                kwargs = {"model": self.model, "system_prompt": self.system_prompt}
                if self.allowed_tools:
                    kwargs["allowed_tools"] = self.allowed_tools
                    kwargs["work_dir"] = self.work_dir
                    if self.permission_mode:
                        kwargs["permission_mode"] = self.permission_mode
                generator = self.cli_controller.execute_command_stream(
                    prompt=self.prompt,
                    session_id=f"{self.session_prefix}-{self.session_id}",
                    **kwargs
                )
                for line in generator:
                    self.final_response += line
                    self.token_delivered.emit(line)
            self.finished.emit(self.final_response)
        except Exception as e:
            logger.error(f"ChatQNAWorker execution failed: {str(e)}")
            self.error.emit(str(e))


class ChatAgent(QObject):
    """Ingestion-free One-shot Q&A 방식으로 실시간 텍스트 Q&A 스트리밍을 담당하는 Chat Agent.

    (Phase 9-4) 3분 주기 백그라운드 전사록 주입(IngestWorker)을 영구 폐지하고, 질문 시점에만
    최근 발화 슬라이딩 윈도우와 Mermaid 맥락을 묶어 단발성으로 호출하여 세션 락 경합을 원천 차단합니다.
    """
    token_delivered = Signal(str)
    finished = Signal(str)
    error_occurred = Signal(str)
    ingest_finished = Signal(int)
    session_initialized = Signal()
    # 상태 가시화 신호 (Phase 10): 사용자 질문 수신
    question_received = Signal(str)
    
    def __init__(self, context: Optional[MeetingContext] = None, cli_controller: Optional[ClaudeCLIController] = None, ingest_interval_ms: int = 180000):
        super().__init__()
        self.context = context or MeetingContext()
        self.cli_controller = cli_controller or ClaudeCLIController()
        
        self.session_id = None
        self.last_ingested_idx = -1
        self.cli_lock = threading.Lock()
        self.active_workers = []
        # 동작 모드 (회의 Q&A ↔ 범용 작업). UI 토글로 전환.
        self.mode = MODE_MEETING
        
        # 컨텍스트 신호 연결
        self.context.signals.meeting_started.connect(self.on_meeting_started)
        self.context.signals.meeting_ended.connect(self.on_meeting_ended)
        
        if self.context.is_meeting_active:
            self.on_meeting_started(self.context.current_session_id)
        
    def on_meeting_started(self, session_id: str):
        self.session_id = session_id
        self.last_ingested_idx = -1
        
        # 백그라운드 IngestWorker 초기 기동을 제거하고 즉시 대화 세션 기동 완료 신호 방출
        logger.info(f"Initialized chat session: chat-session-{self.session_id}")
        self.session_initialized.emit()
        
    def on_meeting_ended(self, session_id: str):
        # 백그라운드 주입이 제거되었으므로 미팅 종료 시 추가 작업 없음
        pass

    def set_mode(self, mode: str):
        """동작 모드를 전환한다(MODE_MEETING ↔ MODE_AGENT)."""
        if mode in (MODE_MEETING, MODE_AGENT):
            self.mode = mode

    def workspace_dir(self) -> str:
        """범용 모드 파일 도구의 작업 폴더(샌드박스 경계)를 보장하고 경로를 반환한다."""
        from pathlib import Path
        config = getattr(self.cli_controller, "config", None) or AppConfig.load_default()
        base = Path(config.db_path).parent  # 예: ~/Documents/PrismFlow
        ws = base / "Workspace"
        try:
            ws.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create workspace dir: {e}")
        return str(ws)

    def ask_question(self, user_query: str):
        if not self.session_id:
            self.session_id = "default_session"

        # 상태 가시화: 사용자 질문 수신을 알림 (Chat 뱃지 '질문수신' 표시용)
        self.question_received.emit(user_query)

        # 이미 완료된 Q&A 워커를 정리하여 active_workers 무한 누적을 방지합니다(질문이 반복돼도 상수 유지).
        # 아직 실행 중인 워커만 보존하므로 진행 중 스레드를 조기 회수해 크래시를 유발하지 않습니다.
        self.active_workers = [w for w in self.active_workers if w.isRunning()]

        # 범용(도구 사용) 모드는 회의 맥락 주입 없이, 웹/파일 도구로 사용자 작업을 직접 수행한다.
        if self.mode == MODE_AGENT:
            self._ask_general(user_query)
            return

        transcripts = self.context.transcripts
        max_idx = len(transcripts) - 1
        
        # 1. 세션 리밋 상태이면 즉각 로컬 대체(Fallback) 모드 구동
        if self.cli_controller.is_session_limited():
            logger.warning("Claude CLI is session limited. Generating local fallback chat response...")
            fallback_response = self._fallback_generate_answer(user_query)
            if self.context.db_manager:
                self.context.db_manager.add_chat_log(
                    session_id=self.session_id,
                    query=user_query,
                    response=fallback_response,
                    timestamp=time.time()
                )
            self.finished.emit(fallback_response)
            return

        # 2. 최근 100개 발화록 슬라이딩 RAG 윈도우 추출 (맥락 보존)
        recent_transcripts = transcripts[-100:]
        recent_list = []
        for tr in recent_transcripts:
            recent_list.append(f"[{tr['speaker']}]: {tr['text']}")
            
        recent_transcripts_text = "\n".join(recent_list)
        
        # 3. Flow 요약 맥락 (Mermaid) 및 질문 융합
        current_mermaid = self.context.current_mermaid_code or "없음 (시각화 분석 전)"
        
        prompt = f"""당신은 PrismFlow 회의 Q&A 비서입니다.
제공된 [회의 전체 지도(Mermaid)]와 [최근 주요 대화 내역]을 바탕으로, 사용자 질문에 답변해 주세요.

[회의 전체 지도(Mermaid)]
{current_mermaid}

[최근 주요 대화 내역]
{recent_transcripts_text}

[질문]
{user_query}
"""
            
        logger.info(f"Sending Q&A request to session chat-session-{self.session_id}")
        
        worker = ChatQNAWorker(self.cli_controller, prompt, self.session_id, self.cli_lock)
        worker.token_delivered.connect(self.token_delivered.emit)
        
        def handle_success(final_response):
            # 성공 시 마지막 인덱스 업데이트
            self.last_ingested_idx = max_idx
            self.ingest_finished.emit(max_idx)
                
            if self.context.db_manager:
                self.context.db_manager.add_chat_log(
                    session_id=self.session_id,
                    query=user_query,
                    response=final_response,
                    timestamp=time.time()
                )
            self.finished.emit(final_response)
            
        def handle_error(err_msg):
            if "session limit" in err_msg.lower() or "limit" in err_msg.lower() or "reset" in err_msg.lower():
                logger.warning("Detected session limit during worker execution. Falling back to local response...")
                self.cli_controller.set_session_limited(True)
                fallback_response = self._fallback_generate_answer(user_query)
                if self.context.db_manager:
                    self.context.db_manager.add_chat_log(
                        session_id=self.session_id,
                        query=user_query,
                        response=fallback_response,
                        timestamp=time.time()
                    )
                self.finished.emit(fallback_response)
            else:
                self.error_occurred.emit(err_msg)
            
        worker.finished.connect(handle_success)
        worker.error.connect(handle_error)
        worker.start()
        self.active_workers.append(worker)

    def _ask_general(self, user_query: str):
        """범용 모드: 웹 검색 + 작업 폴더 내 파일 도구로 사용자의 작업을 직접 수행한다.

        회의 발화 맥락을 주입하지 않고, 별도의 'agent-session-*' CLI 세션으로 회의 Q&A 페르소나와
        분리한다. 범용 작업 결과는 회의 Q&A DB 로그에 적재하지 않는다.
        """
        # 사용량 한도 시 도구 호출 자체가 불가하므로 즉시 안내한다.
        if self.cli_controller.is_session_limited():
            self.finished.emit(
                "⚠️ **[범용 작업 모드]** Claude CLI 사용량 한도로 도구 작업을 진행할 수 없습니다. "
                "한도 해제 후 다시 시도해 주세요."
            )
            return

        workspace = self.workspace_dir()
        prompt = (
            f"[작업 폴더]\n{workspace}\n"
            "위 폴더를 작업 디렉토리로 사용하세요. 파일 읽기/쓰기/수정/이동은 반드시 이 폴더 안에서만 수행하세요.\n\n"
            f"[사용자 요청]\n{user_query}"
        )
        logger.info(f"Sending general agent request to session agent-session-{self.session_id} (workspace={workspace})")

        worker = ChatQNAWorker(
            self.cli_controller, prompt, self.session_id, self.cli_lock,
            system_prompt=AGENT_SYSTEM_PROMPT, model=AGENT_MODEL, session_prefix="agent-session",
            allowed_tools=AGENT_ALLOWED_TOOLS, work_dir=workspace, permission_mode="acceptEdits",
        )
        worker.token_delivered.connect(self.token_delivered.emit)
        worker.finished.connect(self.finished.emit)
        worker.error.connect(self.error_occurred.emit)
        worker.start()
        self.active_workers.append(worker)

    def _fallback_generate_answer(self, query: str) -> str:
        """클라우드 사용량 제한 시 로컬 전사록 기반으로 키워드 매칭 검색 및 최근 발화를 요약해 응답합니다."""
        import re
        transcripts = self.context.transcripts
        if not transcripts:
            return "⚠️ **[로컬 대체 모드]** 현재 Claude CLI 사용량 한도 초과 상태이며, 회의에 기록된 발화 데이터가 존재하지 않아 답변해 드릴 수 없습니다."

        # 단순 키워드 매칭 검색
        matched_lines = []
        query_words = [w.strip() for w in re.split(r'\s+', query) if len(w.strip()) > 1]
        
        for tr in transcripts:
            text = tr["text"]
            for qw in query_words:
                if qw.lower() in text.lower():
                    matched_lines.append(f"- **[{tr['speaker']}]**: {text}")
                    break
        
        response = "⚠️ **[로컬 대체 모드] 현재 Claude CLI 사용량 한도에 도달하여 가상 비서 모드로 동작 중입니다.**\n\n"
        
        if matched_lines:
            response += f"질문하신 키워드 ({', '.join(query_words)})와 관련하여 감지된 회의 내용입니다:\n\n"
            response += "\n".join(matched_lines[-7:])  # 최근 7개 매칭 라인 노출
        else:
            response += "회의 내용 중 질문하신 키워드와 직접 매칭되는 부분이 발견되지 않았습니다. 최근 나눈 발화록을 요약하여 전달드립니다:\n\n"
            recent = transcripts[-5:]
            for rt in recent:
                response += f"- **[{rt['speaker']}]**: {rt['text']}\n"
                
        response += "\n\n*실제 클라우드 비서의 정밀 분석은 사용량 제한이 해제된 후(기본 1:10am 이후) 다시 이용하실 수 있습니다.*"
        return response

    def cleanup(self):
        """활성화된 비동기 Q&A 워커(QThread)들을 안전하게 종료 대기합니다.

        (Phase 9-4) 백그라운드 IngestWorker/타이머가 폐지되었으므로 ingest_timer 참조를 제거하고,
        진행 중인 Q&A 워커는 우선 graceful하게 wait()로 합류시킨 뒤 한도 초과 시에만 강제 종료합니다.
        (DB·CLI 접근 중인 워커를 즉시 terminate()하면 SQLite 네이티브 접근 위반을 유발할 수 있어 회피)
        """
        logger.info("Cleaning up ChatAgent resources...")
        # 싱글톤 컨텍스트 구독을 해제하여 소멸 후에도 좀비 ChatAgent가 회의 신호에 반응하지 않도록 합니다.
        for sig, slot in (
            (self.context.signals.meeting_started, self.on_meeting_started),
            (self.context.signals.meeting_ended, self.on_meeting_ended),
        ):
            try:
                sig.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        for worker in list(self.active_workers):
            try:
                if worker.isRunning():
                    logger.info(f"Waiting for active chat worker to finish: {worker}")
                    if not worker.wait(5000):
                        logger.warning(f"Chat worker did not finish in time; terminating as last resort: {worker}")
                        worker.terminate()
                        worker.wait()
            except Exception as e:
                logger.warning(f"Error during chat worker cleanup: {e}")
        self.active_workers.clear()

