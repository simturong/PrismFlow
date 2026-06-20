import subprocess
import logging
from typing import Optional
from prismflow.core.config import AppConfig

logger = logging.getLogger(__name__)

class ClaudeCLIController:
    """로컬 Claude CLI와 비차단 방식으로 연동하는 컨트롤러 클래스.
    
    대화식 Popen 세션 대신, 입출력 데드락을 원천 차단하기 위해
    -p (print) 모드를 사용하며, Windows TTY 대기를 방지하기 위해
    stdin을 DEVNULL로 리다이렉션합니다.
    """
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load_default()
        
    def execute_command(self, prompt: str, session_id: str, model: Optional[str] = None, timeout: int = 30) -> str:
        """Claude CLI를 실행하여 프롬프트에 대한 응답을 받아옵니다.
        
        Args:
            prompt (str): Claude에게 전송할 프롬프트
            session_id (str): 대화 세션을 공유하기 위한 UUID 형식의 식별자
            model (str, optional): 사용할 Claude 모델 (예: claude-3-5-haiku)
            timeout (int): 최대 실행 타임아웃 시간 (초)
            
        Returns:
            str: Claude CLI가 반환한 응답 텍스트
            
        Raises:
            RuntimeError: CLI 실행 오류가 발생했거나 반환 코드가 0이 아닌 경우
            TimeoutError: 실행 시간 초과 시
        """
        # 1단계: 기존 세션이 있는지 확인하고 재개하기 위해 --resume로 시도합니다.
        cmd = [self.config.claude_cli_cmd, "-p", prompt, "--resume", session_id]
        if model:
            cmd.extend(["--model", model])
            
        logger.debug(f"Executing Claude CLI (Resume): {' '.join(cmd)}")
        
        try:
            import os
            use_shell = os.name == 'nt'
            
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=timeout,
                shell=use_shell
            )
            
            # 만약 해당 세션 ID를 찾을 수 없는 경우 (최초 호출) --session-id로 폴백하여 세션을 생성합니다.
            if result.returncode != 0 and "No conversation found with session ID" in result.stderr:
                logger.info(f"Session {session_id} not found. Initializing new session with --session-id.")
                cmd = [self.config.claude_cli_cmd, "-p", prompt, "--session-id", session_id]
                if model:
                    cmd.extend(["--model", model])
                
                logger.debug(f"Executing Claude CLI (New Session): {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=timeout,
                    shell=use_shell
                )
            
            if result.returncode != 0:
                err_msg = result.stderr.strip()
                logger.error(f"Claude CLI execution failed (Code {result.returncode}): {err_msg}")
                raise RuntimeError(f"Claude CLI execution failed: {err_msg}")
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Claude CLI execution timed out after {timeout} seconds.")
            raise TimeoutError(f"Claude CLI execution timed out after {timeout} seconds.") from e
        except Exception as e:
            logger.error(f"Failed to run Claude CLI: {str(e)}")
            raise RuntimeError(f"Failed to run Claude CLI: {str(e)}") from e

    def execute_command_stream(self, prompt: str, session_id: str, model: Optional[str] = None):
        """Claude CLI를 실행하여 스트리밍 출력을 generator로 반환합니다.
        
        Args:
            prompt (str): Claude에게 전송할 프롬프트
            session_id (str): 대화 세션을 공유하기 위한 UUID 형식의 식별자
            model (str, optional): 사용할 Claude 모델
            
        Yields:
            str: 실시간 출력 라인
        """
        import os
        use_shell = os.name == 'nt'
        
        # 세션 존재 여부 확인을 위해 가볍게 확인
        session_exists = False
        check_cmd = [self.config.claude_cli_cmd, "-p", "Session check", "--resume", session_id]
        if model:
            check_cmd.extend(["--model", model])
            
        try:
            res = subprocess.run(
                check_cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5,
                shell=use_shell
            )
            if res.returncode == 0:
                session_exists = True
            elif "No conversation found" not in res.stderr:
                session_exists = True
        except Exception:
            session_exists = True
            
        if session_exists:
            cmd = [self.config.claude_cli_cmd, "-p", prompt, "--resume", session_id]
        else:
            cmd = [self.config.claude_cli_cmd, "-p", prompt, "--session-id", session_id]
            
        if model:
            cmd.extend(["--model", model])
            
        logger.debug(f"Executing Claude CLI Stream: {' '.join(cmd)}")
        
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                shell=use_shell
            )
            
            for line in iter(proc.stdout.readline, ''):
                yield line
                
            proc.stdout.close()
            proc.wait()
            
            if proc.returncode != 0:
                err = proc.stderr.read().strip()
                proc.stderr.close()
                if err:
                    raise RuntimeError(f"Claude CLI Stream failed: {err}")
            proc.stderr.close()
        except Exception as e:
            logger.error(f"Failed to run Claude CLI Stream: {str(e)}")
            raise RuntimeError(f"Failed to run Claude CLI Stream: {str(e)}") from e

