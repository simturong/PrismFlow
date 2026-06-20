import sys
import os
import time
import uuid
import pytest
import logging
from PySide6.QtWidgets import QApplication
from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.db import DatabaseManager
from main import AppCoordinator

logger = logging.getLogger("E2EHarness")
logging.basicConfig(level=logging.INFO)

class E2EHarness:
    """E2E 회의 시나리오를 시뮬레이션하고 에러 주입 상황을 검증하는 테스트 하네스."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.context = MeetingContext()
        self.context.reset()
        # 테스트용 DB로 초기화
        self.context._config = self.config
        self.context.db_manager = DatabaseManager(self.config.db_path)
        
    def run_simulation(self, session_limit: bool = False) -> dict:
        """10초 E2E 흐름 시뮬레이션을 실행하고 결과 메타데이터를 반환합니다."""
        logger.info(f"Starting E2E simulation (session_limit={session_limit})...")
        
        # 1. Claude CLI 모킹
        original_execute = ClaudeCLIController.execute_command
        original_stream = ClaudeCLIController.execute_command_stream
        
        def mock_execute_command(controller_self, prompt, session_id, model=None, timeout=30, system_prompt=None):
            if session_limit:
                raise RuntimeError("Claude CLI execution failed: You've hit your session limit. Please try again after 1:10am.")
            
            # 모델 혹은 시스템 프롬프트에 따른 Mocking 응답 분기 (겹침 문제 방지)
            if model == "claude-opus-4-8":
                return "# Mock E2E Report\n\n## 요약\n- 가상 회의가 잘 진행됨.\n\n## 최종 Mermaid\n```mermaid\ngraph TD\n    A[시작] --> B(회의 중)\n```"
            elif system_prompt and "mermaid" in system_prompt.lower():
                return "graph TD\n    A[시작] --> B(회의 중)\n    B --> C{결론}"
            else:
                return "This is a mocked response from Claude CLI."
                
        def mock_execute_command_stream(controller_self, prompt, session_id, model=None, system_prompt=None):
            if session_limit:
                raise RuntimeError("Claude CLI execution failed: You've hit your session limit. Please try again after 1:10am.")
            
            yield "Mocked "
            yield "streaming "
            yield "response "
            yield "from "
            yield "Haiku."

        ClaudeCLIController.execute_command = mock_execute_command
        ClaudeCLIController.execute_command_stream = mock_execute_command_stream
        
        # os.startfile 모킹하여 브라우저/편집기 자동 팝업 차단
        original_startfile = getattr(os, "startfile", None)
        os.startfile = lambda path: logger.info(f"[Mocked startfile] Opened: {path}")

        # 2. AppCoordinator 로드 및 설정 주입
        original_load_default = AppConfig.load_default
        AppConfig.load_default = lambda: self.config
        
        # STT 가속화 설정
        self.config.stt_mock_interval = 1.0
        self.config.stt_mock_mode = True
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        coordinator = AppCoordinator(app)
        
        # 3. 회의 가동
        session_id = f"e2e_session_{int(time.time())}"
        self.context.start_meeting(session_id, title="E2E 테스트 하네스 회의")
        
        # Flow Agent 갱신 주기 2.0초로 단축
        if coordinator.flow_agent:
            coordinator.flow_agent.check_interval_sec = 2.0
            
        # 10초 가속 루프
        start_time = time.time()
        chat_sent = False
        
        try:
            while time.time() - start_time < 10.0:
                app.processEvents()
                time.sleep(0.1)
                
                # 5초 시점에 Chat Agent Q&A 질문 발송
                elapsed = time.time() - start_time
                if elapsed >= 5.0 and not chat_sent:
                    logger.info("Injecting Chat Q&A query...")
                    coordinator.chat_agent.ask_question("회의 중 가장 중요한 쟁점은 무엇인가요?")
                    chat_sent = True
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
            
        # 8초 시점에 회의 종료 트리거 (이미 10초 경과)
        logger.info("Ending meeting session...")
        self.context.end_meeting()
        
        # Report Agent 비동기 스레드 작업 완료 대기
        report_wait_start = time.time()
        while time.time() - report_wait_start < 3.0:
            app.processEvents()
            time.sleep(0.1)
            
        # 4. 결과 데이터 수집
        result_data = {
            "session_id": session_id,
            "transcripts_count": len(self.context.transcripts),
            "final_mermaid": self.context.current_mermaid_code,
            "chat_logs": self.context.db_manager.get_chat_logs(session_id),
            "meeting_session": self.context.db_manager.get_session(session_id),
        }
        
        # 5. 자원 회수 및 복원
        coordinator.cleanup()
        ClaudeCLIController.execute_command = original_execute
        ClaudeCLIController.execute_command_stream = original_stream
        AppConfig.load_default = original_load_default
        if original_startfile:
            os.startfile = original_startfile
        else:
            delattr(os, "startfile")
            
        return result_data


# === PyTest Test Cases ===

def test_e2e_harness_normal(q_app, tmp_path):
    """정상 시나리오 E2E 흐름 검증"""
    db_file = tmp_path / "normal_e2e.db"
    docs_dir = tmp_path / "normal_reports"
    
    config = AppConfig(
        db_path=str(db_file),
        docs_save_dir=str(docs_dir),
        claude_cli_cmd="mock_claude",
        stt_mock_mode=True,
    )
    
    harness = E2EHarness(config)
    results = harness.run_simulation(session_limit=False)
    
    assert results["transcripts_count"] > 0
    assert "graph TD" in results["final_mermaid"]
    assert results["meeting_session"] is not None
    # 정상적으로 요약 보고서가 DB에 업데이트 되었는지 확인
    assert results["meeting_session"]["summary"] is not None
    assert "Mock E2E Report" in results["meeting_session"]["summary"]


def test_e2e_harness_session_limit(q_app, tmp_path):
    """Claude CLI 사용량 한도 초과(session limit) 예외 주입 시나리오 검증"""
    db_file = tmp_path / "limit_e2e.db"
    docs_dir = tmp_path / "limit_reports"
    
    config = AppConfig(
        db_path=str(db_file),
        docs_save_dir=str(docs_dir),
        claude_cli_cmd="mock_claude",
        stt_mock_mode=True,
    )
    
    harness = E2EHarness(config)
    results = harness.run_simulation(session_limit=True)
    
    # 1. 예외가 발생하더라도 전사록은 로컬 DB에 안정적으로 기록되어야 함
    assert results["transcripts_count"] > 0
    # 2. 세션 리밋 상태이므로 로컬 Fallback Mermaid 다이어그램이 생성되어야 함
    assert "LocalFallback" in results["final_mermaid"]
    # 3. 회의 세션 자체는 정상 종료 처리되었어야 함 (end_time이 설정됨)
    assert results["meeting_session"] is not None
    assert results["meeting_session"]["end_time"] is not None


if __name__ == "__main__":
    # 독립 실행 시 임시 디렉토리 생성 후 검증 수행
    import tempfile
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_file = tmp_path / "standalone_e2e.db"
        docs_dir = tmp_path / "standalone_reports"
        
        config = AppConfig(
            db_path=str(db_file),
            docs_save_dir=str(docs_dir),
            claude_cli_cmd="mock_claude",
            stt_mock_mode=True,
        )
        
        # GUI 기동
        app = QApplication(sys.argv)
        
        print("\n--- Running Normal Simulation ---")
        harness_normal = E2EHarness(config)
        res_normal = harness_normal.run_simulation(session_limit=False)
        print("Transcripts count:", res_normal["transcripts_count"])
        print("Mermaid diagram:\n", res_normal["final_mermaid"])
        print("Summary saved in DB:", bool(res_normal["meeting_session"].get("summary")))
        
        print("\n--- Running Session Limit Simulation ---")
        harness_limit = E2EHarness(config)
        res_limit = harness_limit.run_simulation(session_limit=True)
        print("Transcripts count:", res_limit["transcripts_count"])
        print("Mermaid diagram:", repr(res_limit["final_mermaid"]))
        print("Meeting ended timestamp:", res_limit["meeting_session"].get("end_time"))
        
        print("\nStandalone simulation finished successfully.")
