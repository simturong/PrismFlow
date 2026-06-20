import pytest
import uuid
from prismflow.core.config import AppConfig
from prismflow.core.cli_controller import ClaudeCLIController

def test_cli_controller_init():
    """컨트롤러 기본 초기화 테스트"""
    controller = ClaudeCLIController()
    assert controller.config is not None
    assert controller.config.claude_cli_cmd == "claude"

def test_cli_controller_execute_success():
    """실제 Claude CLI 호출 성공 테스트"""
    # 실제 환경의 claude CLI를 사용하기 위해 기본 설정 로드
    config = AppConfig.load_default()
    controller = ClaudeCLIController(config)
    
    # 세션 ID 생성
    session_id = str(uuid.uuid4())
    
    try:
        response = controller.execute_command("Hello, please reply with exactly the word 'PASS'", session_id=session_id)
        assert "PASS" in response
    except RuntimeError as e:
        # 만약 로컬에 Claude Code 로그인이 안 되어 있거나 실행이 안 되는 특수 상황이면 스킵
        pytest.skip(f"Claude CLI execution failed: {str(e)}")

def test_cli_controller_session_persistence():
    """세션 유지를 통해 과거 대화 맥락이 유지되는지 테스트"""
    config = AppConfig.load_default()
    controller = ClaudeCLIController(config)
    
    session_id = str(uuid.uuid4())
    
    # 1차 호출: 이름 알려주기
    controller.execute_command("My name is Antigravity. Remember this name.", session_id=session_id)
    
    # 2차 호출: 이름 질문하기
    response = controller.execute_command("What is my name? Reply with just the name.", session_id=session_id)
    
    assert "Antigravity" in response

def test_cli_controller_invalid_command():
    """존재하지 않는 명령어를 호출했을 때 예외 발생 테스트"""
    config = AppConfig(claude_cli_cmd="invalid_non_existent_command_12345")
    controller = ClaudeCLIController(config)
    
    session_id = str(uuid.uuid4())
    
    with pytest.raises(RuntimeError):
        controller.execute_command("Hello", session_id=session_id)

def test_cli_controller_timeout():
    """타임아웃 발생 시 TimeoutError 발생 테스트"""
    config = AppConfig.load_default()
    controller = ClaudeCLIController(config)
    
    session_id = str(uuid.uuid4())
    
    # 타임아웃을 극단적으로 짧은 1ms로 주어 예외가 발생하는지 검증
    with pytest.raises(TimeoutError):
        controller.execute_command("Hello", session_id=session_id, timeout=1)
