import threading
import time
import logging
from typing import Optional
from PySide6.QtCore import QObject, QTimer, QThread, Signal
from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController

logger = logging.getLogger(__name__)

# claude CLI를 코딩 에이전트가 아닌 "회의 어시스턴트"로 동작시키기 위한 시스템 프롬프트.
# (프로젝트 CLAUDE.md/메모리는 cli_controller의 격리 실행으로 차단되며, 이 프롬프트로 페르소나를 고정)
CHAT_SYSTEM_PROMPT = (
    "당신은 PrismFlow 회의 어시스턴트입니다. 회의 발화 맥락에만 근거하여 사용자 질문에 "
    "한국어로 간결하고 정확하게 답하십시오. 코드 작업·파일 수정·도구 사용을 하지 말고 "
    "텍스트로만 답하며, 회의에 없는 내용은 추측하지 마십시오."
)

class IngestWorker(QThread):
    """백그라운드에서 전사록을 Claude CLI 세션에 비동기 주입하는 스레드"""
    finished = Signal(int)
    error = Signal(str)
    
    def __init__(self, cli_controller: ClaudeCLIController, prompt: str, session_id: str, last_idx: int, cli_lock: threading.Lock):
        super().__init__()
        self.cli_controller = cli_controller
        self.prompt = prompt
        self.session_id = session_id
        self.last_idx = last_idx
        self.cli_lock = cli_lock
        
    def run(self):
        try:
            with self.cli_lock:
                self.cli_controller.execute_command(
                    prompt=self.prompt,
                    session_id=f"chat-session-{self.session_id}",
                    model="claude-haiku-4-5",
                    system_prompt=CHAT_SYSTEM_PROMPT
                )
            self.finished.emit(self.last_idx)
        except Exception as e:
            logger.error(f"IngestWorker execution failed: {str(e)}")
            self.error.emit(str(e))


class ChatQNAWorker(QThread):
    """비동기 방식으로 Claude CLI를 실행하여 답변을 스트리밍하는 스레드"""
    token_delivered = Signal(str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, cli_controller: ClaudeCLIController, prompt: str, session_id: str, cli_lock: threading.Lock):
        super().__init__()
        self.cli_controller = cli_controller
        self.prompt = prompt
        self.session_id = session_id
        self.cli_lock = cli_lock
        self.final_response = ""
        
    def run(self):
        try:
            with self.cli_lock:
                generator = self.cli_controller.execute_command_stream(
                    prompt=self.prompt,
                    session_id=f"chat-session-{self.session_id}",
                    model="claude-haiku-4-5",
                    system_prompt=CHAT_SYSTEM_PROMPT
                )
                for line in generator:
                    self.final_response += line
                    self.token_delivered.emit(line)
            self.finished.emit(self.final_response)
        except Exception as e:
            logger.error(f"ChatQNAWorker execution failed: {str(e)}")
            self.error.emit(str(e))


class ChatAgent(QObject):
    """Chat Agent로 3분 주기 백그라운드 전사록 주입 및 실시간 텍스트 Q&A 스트리밍을 담당합니다."""
    token_delivered = Signal(str)
    finished = Signal(str)
    error_occurred = Signal(str)
    ingest_finished = Signal(int)
    session_initialized = Signal()
    
    def __init__(self, context: Optional[MeetingContext] = None, cli_controller: Optional[ClaudeCLIController] = None, ingest_interval_ms: int = 180000):
        super().__init__()
        self.context = context or MeetingContext()
        self.cli_controller = cli_controller or ClaudeCLIController()
        self.ingest_interval_ms = ingest_interval_ms
        
        self.session_id = None
        self.last_ingested_idx = -1
        self.cli_lock = threading.Lock()
        self.active_workers = []
        
        # 백그라운드 주입용 타이머
        self.ingest_timer = QTimer(self)
        self.ingest_timer.setInterval(self.ingest_interval_ms)
        self.ingest_timer.timeout.connect(self.ingest_transcripts_background)
        
        # 컨텍스트 신호 연결
        self.context.signals.meeting_started.connect(self.on_meeting_started)
        self.context.signals.meeting_ended.connect(self.on_meeting_ended)
        
        if self.context.is_meeting_active:
            self.on_meeting_started(self.context.current_session_id)
        
    def on_meeting_started(self, session_id: str):
        self.session_id = session_id
        self.last_ingested_idx = -1
        
        # 최초 세션 확보용 실행
        initial_prompt = "회의 챗 세션을 시작합니다."
        worker = IngestWorker(self.cli_controller, initial_prompt, self.session_id, -1, self.cli_lock)
        worker.finished.connect(self._on_initial_ingest_success)
        worker.start()
        self.active_workers.append(worker)
        
        self.ingest_timer.start()
        
    def _on_initial_ingest_success(self, last_idx):
        logger.info(f"Initialized chat session: chat-session-{self.session_id}")
        self.session_initialized.emit()

        
    def on_meeting_ended(self, session_id: str):
        self.ingest_timer.stop()
        # 종료 전 미주입 대화 백그라운드 최종 주입
        self.ingest_transcripts_background()
        
    def ingest_transcripts_background(self):
        if not self.session_id:
            return
            
        transcripts = self.context.transcripts
        if not transcripts:
            return
            
        max_idx = len(transcripts) - 1
        if max_idx <= self.last_ingested_idx:
            return
            
        new_transcripts_list = []
        for idx in range(self.last_ingested_idx + 1, len(transcripts)):
            tr = transcripts[idx]
            new_transcripts_list.append(f"[{tr['speaker']}]: {tr['text']}")
            
        new_transcripts = "\n".join(new_transcripts_list)
        prompt = f"[시스템: 다음은 회의 중 추가된 신규 대화 내용입니다. 기억해 두세요.]\n{new_transcripts}"
        
        logger.debug(f"Ingesting new transcripts to session chat-session-{self.session_id}. Indexes {self.last_ingested_idx + 1} to {max_idx}")
        
        worker = IngestWorker(self.cli_controller, prompt, self.session_id, max_idx, self.cli_lock)
        worker.finished.connect(self.on_ingest_success)
        worker.error.connect(self.on_ingest_error)
        worker.start()
        self.active_workers.append(worker)
        
    def on_ingest_success(self, last_idx):
        if last_idx > self.last_ingested_idx:
            self.last_ingested_idx = last_idx
            self.ingest_finished.emit(last_idx)
            logger.info(f"Successfully ingested transcripts up to index {last_idx}")
            
    def on_ingest_error(self, err_msg):
        self.error_occurred.emit(f"Background Ingestion Error: {err_msg}")
        
    def ask_question(self, user_query: str):
        if not self.session_id:
            self.session_id = "default_session"
            
        transcripts = self.context.transcripts
        max_idx = len(transcripts) - 1
        
        # 주입되지 않은 잔여 발화
        unsubmitted_list = []
        for idx in range(self.last_ingested_idx + 1, len(transcripts)):
            tr = transcripts[idx]
            unsubmitted_list.append(f"[{tr['speaker']}]: {tr['text']}")
            
        unsubmitted_transcripts = "\n".join(unsubmitted_list)
        
        if unsubmitted_transcripts:
            prompt = f"[최근 대화 추가]\n{unsubmitted_transcripts}\n\n[질문]\n{user_query}"
        else:
            prompt = f"[질문]\n{user_query}"
            
        logger.info(f"Sending Q&A request to session chat-session-{self.session_id}")
        
        worker = ChatQNAWorker(self.cli_controller, prompt, self.session_id, self.cli_lock)
        worker.token_delivered.connect(self.token_delivered.emit)
        
        def handle_success(final_response):
            if max_idx > self.last_ingested_idx:
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
            
        worker.finished.connect(handle_success)
        worker.error.connect(self.error_occurred.emit)
        worker.start()
        self.active_workers.append(worker)

    def cleanup(self):
        """기동 중인 타이머를 멈추고 활성화된 비동기 스레드(Worker)들을 안전하게 종료합니다."""
        logger.info("Cleaning up ChatAgent resources...")
        self.ingest_timer.stop()
        
        # 스레드 종료 및 대기
        for worker in list(self.active_workers):
            if worker.isRunning():
                logger.info(f"Terminating active worker thread: {worker}")
                worker.terminate()
                worker.wait()
        self.active_workers.clear()

