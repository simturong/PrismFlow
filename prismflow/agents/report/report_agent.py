import os
import sys
import datetime
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.config import AppConfig

logger = logging.getLogger(__name__)

# 최종 회의록은 추론 품질이 가장 높은 Opus 4.8 모델로 단발 생성합니다.
REPORT_MODEL = "claude-opus-4-8"
# Opus 모델 특성상 긴 회의록은 추론 시간이 길 수 있어 타임아웃을 넉넉히 둡니다.
REPORT_TIMEOUT_SEC = 120
# claude CLI를 코딩 에이전트가 아닌 "전문 회의 기록관"으로 동작시키기 위한 시스템 프롬프트.
REPORT_SYSTEM_PROMPT = (
    "당신은 전문 회의 기록관 및 비즈니스 분석가입니다. 제공된 회의 컨텍스트를 정밀 분석하여 "
    "임원진 보고용 고품질 Markdown 회의록만 출력하십시오. 도구·파일 작업 없이 순수 Markdown 텍스트만 반환하십시오."
)


def _format_transcripts(transcripts: list) -> str:
    """발화 목록을 `[화자] 텍스트` 형태의 단일 문자열로 직렬화합니다."""
    if not transcripts:
        return "(전사된 발화 내용이 없습니다.)"
    lines = []
    for tr in transcripts:
        speaker = tr.get("speaker", "Unknown")
        text = tr.get("text", "")
        lines.append(f"[{speaker}] {text}")
    return "\n".join(lines)


def _format_chat_logs(chat_logs: list) -> str:
    """채팅 Q&A 목록을 `Q: ... / A: ...` 형태의 단일 문자열로 직렬화합니다."""
    if not chat_logs:
        return "(회의 중 질의응답 내역이 없습니다.)"
    blocks = []
    for log in chat_logs:
        query = log.get("query", "")
        response = log.get("response", "")
        blocks.append(f"Q: {query}\nA: {response}")
    return "\n\n".join(blocks)


def build_report_prompt(session: Optional[dict], transcripts: list, chat_logs: list, mermaid_code: str) -> str:
    """수집된 모든 회의 컨텍스트를 융합하여 Claude Opus 보고서 프롬프트를 구성합니다."""
    session = session or {}
    session_id = session.get("session_id", "")
    title = session.get("title", "새로운 회의")
    start_time = session.get("start_time", "")
    end_time = session.get("end_time", "")

    mermaid_block = mermaid_code.strip() if mermaid_code else "(생성된 흐름도가 없습니다.)"

    return f"""[시스템 역할]
당신은 PrismFlow 프로젝트의 전문 회의 기록관 및 비즈니스 분석가입니다. 제공된 회의 컨텍스트(STT 발화문, 채팅 히스토리, Mermaid 흐름도)를 정밀 분석하여 임원진 보고용 고품질 Markdown 회의록을 작성하십시오.

[회의 기본 정보]
- 세션 ID: {session_id}
- 회의 제목: {title}
- 일시: {start_time} ~ {end_time}

[최종 Mermaid 흐름도]
{mermaid_block}

[회의 중 질의응답 (Chat Logs)]
{_format_chat_logs(chat_logs)}

[전체 STT 전사록]
{_format_transcripts(transcripts)}

[작성 규칙 및 구조 가이드라인]
1. 회의 요약: 회의의 목적, 주요 의제, 핵심 결론 및 합의 내용을 3-4문장으로 명확히 정리하십시오.
2. 아젠다별 쟁점: 각 세부 아젠다별로 의견이 엇갈렸던 쟁점 사항, 대립된 의견의 흐름, 그리고 최종적으로 합의된 솔루션을 구체적으로 작성하십시오.
3. 최종 Mermaid 소스: 회의 중 도출된 최종 Mermaid 코드를 코드 블록(```mermaid) 안에 그대로 온전히 포함시키십시오.
4. Todo 리스트: 회의에서 결정된 향후 작업 항목(Action Item), 담당자, 그리고 언급된 마감 기한을 명확한 리스트 포맷으로 추출하십시오.
5. 서론, 결론, 혹은 "알겠습니다. 작성해 드리겠습니다"와 같은 AI의 불필요한 메타 설명 문구는 제외하고, 오직 순수한 Markdown 내용만 반환하십시오."""


class ReportWorker(QThread):
    """백그라운드에서 최종 회의록을 컴파일하여 파일 저장 및 DB 동기화까지 수행하는 스레드.

    회의 종료 직후 무거운 Opus 추론과 디스크 I/O를 메인 UI 스레드에서 분리하여,
    종료 시점의 UI 멈춤(Freeze) 현상을 원천 방지합니다.
    """
    report_generated = Signal(str)   # 저장된 보고서 파일 경로
    error = Signal(str)              # 오류 메시지

    def __init__(self, cli_controller: ClaudeCLIController, db_manager, config: AppConfig,
                 session_id: str, mermaid_code: str, session_dir: Optional[str] = None):
        super().__init__()
        self.cli_controller = cli_controller
        self.db_manager = db_manager
        self.config = config
        self.session_id = session_id
        self.mermaid_code = mermaid_code
        self.session_dir = session_dir

    def run(self):
        try:
            # 1. SQLite DB에서 회의 메타데이터, 전체 발화록, 채팅 Q&A 이력을 수집합니다.
            session = self.db_manager.get_session(self.session_id)
            transcripts = self.db_manager.get_transcripts(self.session_id)
            chat_logs = self.db_manager.get_chat_logs(self.session_id)

            # 2. 모든 자료를 Mermaid 흐름도와 융합하여 보고서 프롬프트를 구성합니다.
            prompt = build_report_prompt(session, transcripts, chat_logs, self.mermaid_code)

            # 3. Claude Opus 혹은 로컬 Fallback을 통해 최종 Markdown 회의록을 생성합니다.
            if self.cli_controller.is_session_limited():
                logger.warning("Claude CLI is session limited. Generating local fallback report...")
                report_content = self._fallback_generate_report(session, transcripts, chat_logs)
            else:
                try:
                    report_content = self.cli_controller.execute_command(
                        prompt=prompt,
                        session_id=f"report-session-{self.session_id}",
                        model=REPORT_MODEL,
                        timeout=REPORT_TIMEOUT_SEC,
                        system_prompt=REPORT_SYSTEM_PROMPT,
                    )
                except Exception as e:
                    err_str = str(e)
                    if self.cli_controller._looks_like_session_limit(err_str):
                        logger.warning("Detected session limit during report generation. Falling back to local report...")
                        self.cli_controller.set_session_limited(True)
                        report_content = self._fallback_generate_report(session, transcripts, chat_logs)
                    else:
                        raise e

            if not report_content or not report_content.strip():
                raise RuntimeError("보고서 생성 결과가 비어 있습니다.")

            # 4. 날짜별 폴더에 UTF-8 마크다운 파일로 저장합니다.
            filepath = self._save_report(report_content)

            # 5. SQLite meeting_sessions.summary 컬럼에 본문을 영구 저장합니다.
            self._persist_summary(session, report_content)

            # 6. Windows 기본 연결 프로그램으로 보고서를 자동 실행합니다.
            self._open_report(filepath)

            self.report_generated.emit(str(filepath))
        except Exception as e:
            logger.error(f"ReportWorker execution failed: {str(e)}")
            self.error.emit(str(e))

    def _fallback_generate_report(self, session: Optional[dict], transcripts: list, chat_logs: list) -> str:
        """클라우드 사용량 제한 시 로컬 데이터만으로 구성된 정적 마크다운 회의 요약 보고서를 작성합니다."""
        session = session or {}
        title = session.get("title", "새로운 회의")
        start_time = session.get("start_time", "")
        end_time = session.get("end_time", "")
        
        # 화자 목록 및 간단 통계
        speakers = sorted(list(set([tr.get("speaker", "Unknown") for tr in transcripts])))
        
        # 전사록 포맷팅
        transcript_str = _format_transcripts(transcripts)
        
        # 채팅 로그 포맷팅
        chat_str = _format_chat_logs(chat_logs)
        
        mermaid_block = self.mermaid_code.strip() if self.mermaid_code else "(생성된 흐름도가 없습니다.)"
        
        return f"""# ⚠️ 회의록 (로컬 백업 대체 모드)

*본 보고서는 Claude CLI 사용량 한도 초과 상태로 인해 로컬 회의 데이터(STT 및 Q&A 이력)만을 바탕으로 자동 생성된 정적 회의록입니다.*

## 📅 1. 회의 기본 정보
- **회의 제목**: {title}
- **세션 식별자**: {self.session_id}
- **회의 일시**: {start_time} ~ {end_time}
- **참석 화자**: {", ".join(speakers)}

## 📊 2. 회의 논리 흐름도 (Mermaid)
```mermaid
{mermaid_block}
```

## 👥 3. 전체 회의 대화록 (STT 전사)
{transcript_str}

## 💬 4. 회의 중 Q&A 내역 (채팅 로그)
{chat_str}

---
*PrismFlow Local Fallback Report Engine v1.0. Claude 사용량 한도 해제 이후(기본 1:10am 이후) 재기동하시면 Opus에 의한 인공지능 요약 및 분석 회의록을 생성할 수 있습니다.*"""

    def _save_report(self, content: str) -> Path:
        """세션 디렉토리가 있으면 `session_dir/report_{session_id}.md`로 저장하고, 없으면 `docs_save_dir/YYYY-MM-DD/` 경로에 UTF-8로 기록합니다."""
        if self.session_dir:
            filepath = Path(self.session_dir) / f"report_{self.session_id}.md"
        else:
            today = datetime.date.today().strftime("%Y-%m-%d")
            report_dir = Path(self.config.docs_save_dir) / today
            report_dir.mkdir(parents=True, exist_ok=True)
            filepath = report_dir / f"report_{self.session_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Report saved to: {filepath}")
        return filepath

    def _persist_summary(self, session: Optional[dict], content: str):
        """meeting_sessions.summary에 보고서 본문을 저장하되 원본 종료 시각은 보존합니다."""
        if session and session.get("end_time"):
            end_time = session["end_time"]
        else:
            end_time = datetime.datetime.now().isoformat()
        self.db_manager.end_session(self.session_id, end_time=end_time, summary=content)

    def _open_report(self, filepath: Path):
        """Windows 환경에서만 os.startfile로 보고서를 자동 실행합니다 (타 플랫폼 예외 방어)."""
        if sys.platform == "win32" and hasattr(os, "startfile"):
            try:
                os.startfile(str(filepath))
            except Exception as e:
                logger.warning(f"Failed to auto-open report file: {str(e)}")


class ReportAgent(QObject):
    """회의 종료 신호를 구독하여 최종 회의록 컴파일 워커를 가동하는 에이전트."""
    report_generated = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, context: Optional[MeetingContext] = None,
                 cli_controller: Optional[ClaudeCLIController] = None):
        super().__init__()
        self.context = context or MeetingContext()
        self.cli_controller = cli_controller or ClaudeCLIController()
        self.active_workers = []

        # 회의 종료 시그널에 보고서 생성 핸들러를 바인딩합니다.
        self.context.signals.meeting_ended.connect(self._on_meeting_ended)

    def _on_meeting_ended(self, session_id: str):
        logger.info(f"Meeting {session_id} ended. Compiling final report (Opus)...")

        # 메인 스레드 시점에 최종 Mermaid 코드를 캡처하여 reset() 레이스를 방지합니다.
        mermaid_code = self.context.current_mermaid_code
        db_manager = self.context.db_manager
        config = getattr(self.cli_controller, "config", None) or AppConfig.load_default()
        session_dir = self.context.current_session_dir

        worker = ReportWorker(self.cli_controller, db_manager, config, session_id, mermaid_code, session_dir=session_dir)
        worker.report_generated.connect(self._on_report_generated)
        worker.error.connect(self._on_error)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()
        self.active_workers.append(worker)

    def _on_report_generated(self, filepath: str):
        logger.info(f"Final report generated: {filepath}")
        self.report_generated.emit(filepath)

    def _on_error(self, msg: str):
        logger.error(f"Report generation error: {msg}")
        self.error_occurred.emit(msg)

    def _cleanup_worker(self, worker: ReportWorker):
        if worker in self.active_workers:
            self.active_workers.remove(worker)

    def cleanup(self):
        """기동 중인 보고서 생성 워커들을 안전하게 종료 대기하고 시그널을 해제합니다.

        진행 중인 워커는 bounded wait로 합류를 시도하되, 시간 내 끝나지 않으면 참조를 유지한 채 둡니다.
        (실행 중인 QThread의 파이썬 참조를 제거하면 GC가 'Destroyed while thread is still running' 크래시를
        유발할 수 있으므로, 미완료 워커는 clear 대상에서 제외합니다. 정상 완료 시 finished 시그널로 자가 제거됩니다.)
        """
        logger.info("Cleaning up ReportAgent resources...")
        try:
            self.context.signals.meeting_ended.disconnect(self._on_meeting_ended)
        except Exception:
            pass
        still_running = []
        for worker in list(self.active_workers):
            try:
                if worker.isRunning() and not worker.wait(3000):
                    logger.warning(f"Report worker still running after wait; keeping reference to avoid unsafe teardown: {worker}")
                    still_running.append(worker)
            except Exception as e:
                logger.warning(f"Error during report worker cleanup: {e}")
        # 종료된 워커만 정리하고, 아직 실행 중인 워커는 참조를 유지(GC-중-실행 크래시 방지)
        self.active_workers = still_running
