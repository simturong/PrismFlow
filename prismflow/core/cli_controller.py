import subprocess
import logging
import uuid
import tempfile
import shutil
from typing import Optional, List
from prismflow.core.config import AppConfig

logger = logging.getLogger(__name__)

# 에이전트(Flow/Chat/Report)는 코딩 에이전트가 아니라 "회의 비서"이므로,
# claude CLI를 프로젝트 컨텍스트와 완전히 분리된 가볍고 깨끗한 상태로 구동한다.
# - --strict-mcp-config: --mcp-config 미지정과 함께 사용 시 모든 MCP 서버 로드를 차단(경량/고속 기동)
# - --setting-sources user: 프로젝트 설정/CLAUDE.md/메모리 로딩을 배제(클린; "Antigravity" 등 누수 차단)
# (--exclude-dynamic-system-prompt-sections는 --system-prompt와 함께일 때만 유효하므로
#  _build_extra_args에서 system_prompt가 있을 때만 부가한다.)
_CLEAN_CLI_ARGS = [
    "--strict-mcp-config",
    "--setting-sources", "user",
]

class ClaudeCLIController:
    """로컬 Claude CLI와 비차단 방식으로 연동하는 컨트롤러 클래스.

    대화식 Popen 세션 대신, 입출력 데드락을 원천 차단하기 위해 -p (print) 모드를 사용합니다.
    **프롬프트는 명령줄 인자가 아니라 STDIN으로 전달**합니다. Windows에서 `shell=True`로
    다중줄(전사록) 프롬프트를 인자로 넘기면 `cmd.exe`가 줄바꿈에서 명령을 잘라 맥락이
    유실되므로, `shell=False` + STDIN 입력으로 이 문제를 원천 차단합니다.
    """
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load_default()
        # 프로젝트 디렉토리의 CLAUDE.md/agent.md/메모리를 읽지 않도록 중립 작업 디렉토리에서 CLI를 실행한다.
        self._cli_cwd = tempfile.gettempdir()
        # shell=False로 실행하기 위해 실제 실행 파일 경로(Windows의 claude.CMD 등)를 해석한다.
        # 해석 실패 시 원본 명령을 그대로 사용(존재하지 않으면 subprocess가 예외 → RuntimeError로 변환).
        self._cli_exe = shutil.which(self.config.claude_cli_cmd) or self.config.claude_cli_cmd
        self._session_limited = False

    def _build_extra_args(self, model: Optional[str], system_prompt: Optional[str]) -> List[str]:
        """클린·경량 격리 실행을 위한 공통 인자(+모델/시스템 프롬프트)를 조립합니다."""
        args = list(_CLEAN_CLI_ARGS)
        if model:
            args += ["--model", model]
        if system_prompt:
            # 동적 섹션 제거는 --system-prompt와 병용해야 유효하다.
            args += ["--system-prompt", system_prompt, "--exclude-dynamic-system-prompt-sections"]
        return args

    def _run_once(self, tail_args: List[str], prompt: str, timeout: int) -> subprocess.CompletedProcess:
        """`claude -p <tail_args>`를 shell 없이 1회 실행하고, 프롬프트는 STDIN으로 전달합니다."""
        cmd = [self._cli_exe, "-p"] + tail_args
        logger.debug(f"Executing Claude CLI: {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            input=prompt,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout,
            shell=False,
            cwd=self._cli_cwd,
        )

    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        """claude CLI는 `--resume`/`--session-id`에 유효한 UUID를 요구합니다.

        에이전트가 사용하는 의미 기반 세션명(예: `chat-session-20260620_190019`)은
        UUID가 아니므로 거부됩니다. 이를 결정적(deterministic) UUID(uuid5)로 변환해
        동일 입력이 항상 동일 UUID로 매핑되도록 함으로써, 회의 동안 같은 세션을
        안정적으로 재개(resume)할 수 있게 합니다. 이미 유효한 UUID면 그대로 사용합니다.
        """
        try:
            uuid.UUID(str(session_id))
            return str(session_id)
        except (ValueError, TypeError, AttributeError):
            return str(uuid.uuid5(uuid.NAMESPACE_URL, str(session_id)))

    def execute_command(self, prompt: str, session_id: str, model: Optional[str] = None,
                        timeout: int = 30, system_prompt: Optional[str] = None) -> str:
        """Claude CLI를 실행하여 프롬프트에 대한 응답을 받아옵니다.

        Args:
            prompt (str): Claude에게 전송할 프롬프트
            session_id (str): 대화 세션을 공유하기 위한 UUID 형식의 식별자
            model (str, optional): 사용할 Claude 모델 (예: claude-haiku-4-5)
            timeout (int): 최대 실행 타임아웃 시간 (초)
            system_prompt (str, optional): 기본(코딩 에이전트) 시스템 프롬프트를 대체할 에이전트 페르소나

        Returns:
            str: Claude CLI가 반환한 응답 텍스트

        Raises:
            RuntimeError: CLI 실행 오류가 발생했거나 반환 코드가 0이 아닌 경우
            TimeoutError: 실행 시간 초과 시
        """
        # claude CLI는 유효 UUID만 세션 ID로 허용하므로 의미 기반 세션명을 결정적 UUID로 정규화합니다.
        session_id = self._normalize_session_id(session_id)
        extra_args = self._build_extra_args(model, system_prompt)

        try:
            # 1단계: 기존 세션이 있는지 확인하고 재개하기 위해 --resume로 시도합니다.
            result = self._run_once(["--resume", session_id] + extra_args, prompt, timeout)

            # 만약 해당 세션 ID를 찾을 수 없는 경우 (최초 호출) --session-id로 폴백하여 세션을 생성합니다.
            if result.returncode != 0 and "No conversation found with session ID" in result.stderr:
                logger.info(f"Session {session_id} not found. Initializing new session with --session-id.")
                result = self._run_once(["--session-id", session_id] + extra_args, prompt, timeout)

            if result.returncode != 0:
                err_msg = result.stderr.strip()
                logger.error(f"Claude CLI execution failed (Code {result.returncode}): {err_msg}")
                if "session limit" in err_msg.lower() or "limit" in err_msg.lower() or "reset" in err_msg.lower():
                    self._session_limited = True
                raise RuntimeError(f"Claude CLI execution failed: {err_msg}")
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Claude CLI execution timed out after {timeout} seconds.")
            raise TimeoutError(f"Claude CLI execution timed out after {timeout} seconds.") from e
        except Exception as e:
            err_str = str(e)
            if "session limit" in err_str.lower() or "limit" in err_str.lower() or "reset" in err_str.lower():
                self._session_limited = True
            logger.error(f"Failed to run Claude CLI: {err_str}")
            raise RuntimeError(f"Failed to run Claude CLI: {err_str}") from e

    def execute_command_stream(self, prompt: str, session_id: str, model: Optional[str] = None,
                               system_prompt: Optional[str] = None):
        """Claude CLI를 실행하여 스트리밍 출력을 generator로 반환합니다.

        Args:
            prompt (str): Claude에게 전송할 프롬프트
            session_id (str): 대화 세션을 공유하기 위한 UUID 형식의 식별자
            model (str, optional): 사용할 Claude 모델
            system_prompt (str, optional): 기본(코딩 에이전트) 시스템 프롬프트를 대체할 에이전트 페르소나

        Yields:
            str: 실시간 출력 라인
        """
        # claude CLI는 유효 UUID만 세션 ID로 허용하므로 의미 기반 세션명을 결정적 UUID로 정규화합니다.
        session_id = self._normalize_session_id(session_id)
        extra_args = self._build_extra_args(model, system_prompt)

        # 세션 존재 여부 확인을 위해 가볍게 확인 (프로브이므로 시스템 프롬프트 없이 경량 인자만 적용)
        session_exists = False
        probe_tail = ["--resume", session_id] + list(_CLEAN_CLI_ARGS)
        if model:
            probe_tail += ["--model", model]

        try:
            res = self._run_once(probe_tail, "Session check", timeout=5)
            if res.returncode == 0:
                session_exists = True
            elif "No conversation found" not in res.stderr:
                session_exists = True
        except Exception:
            session_exists = True

        if session_exists:
            tail = ["--resume", session_id] + extra_args
        else:
            tail = ["--session-id", session_id] + extra_args

        cmd = [self._cli_exe, "-p"] + tail
        logger.debug(f"Executing Claude CLI Stream: {' '.join(cmd)}")

        try:
            # 프롬프트는 명령줄 인자가 아니라 STDIN으로 전달한다(Windows 다중줄 인자 훼손 방지).
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                shell=False,
                cwd=self._cli_cwd
            )
            proc.stdin.write(prompt)
            proc.stdin.close()

            for line in iter(proc.stdout.readline, ''):
                yield line
                
            proc.stdout.close()
            proc.wait()
            
            if proc.returncode != 0:
                err = proc.stderr.read().strip()
                proc.stderr.close()
                if err:
                    if "session limit" in err.lower() or "limit" in err.lower() or "reset" in err.lower():
                        self._session_limited = True
                    raise RuntimeError(f"Claude CLI Stream failed: {err}")
            proc.stderr.close()
        except Exception as e:
            err_str = str(e)
            if "session limit" in err_str.lower() or "limit" in err_str.lower() or "reset" in err_str.lower():
                self._session_limited = True
            logger.error(f"Failed to run Claude CLI Stream: {err_str}")
            raise RuntimeError(f"Failed to run Claude CLI Stream: {err_str}") from e

    def is_session_limited(self) -> bool:
        """현재 Claude CLI가 사용량 한도 초과 상태인지 여부를 반환합니다."""
        return self._session_limited

    def set_session_limited(self, val: bool):
        """Claude CLI의 사용량 한도 초과 상태를 직접 설정합니다."""
        self._session_limited = val

