import subprocess
import logging
import uuid
import tempfile
import shutil
import threading
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
        # 이 프로세스에서 이미 생성(--session-id)한 CLI 세션 UUID 집합.
        # 두 번째 호출부터는 --resume를 쓰도록 하여 "Session ID ... is already in use" 충돌을 방지한다.
        self._created_sessions = set()
        # 진행 중인 CLI 서브프로세스 추적(앱 종료 시 in-flight 호출을 즉시 중단하기 위함).
        self._active_procs = set()
        self._proc_lock = threading.Lock()
        self._shutting_down = False

    def _register_proc(self, proc) -> bool:
        """실행 중인 서브프로세스를 추적 집합에 등록한다. 이미 종료(shutdown) 중이면 즉시 죽이고 False."""
        with self._proc_lock:
            if self._shutting_down:
                try:
                    proc.kill()
                except Exception:
                    pass
                return False
            self._active_procs.add(proc)
            return True

    def _unregister_proc(self, proc):
        with self._proc_lock:
            self._active_procs.discard(proc)

    def terminate_all(self):
        """진행 중인 모든 CLI 서브프로세스를 강제 종료한다.

        앱 종료 시점에 호출하여, Flow/Report/Chat 에이전트가 붙들고 있는 in-flight CLI 호출을 즉시
        끊는다. 그러면 각 워커 스레드의 readline/communicate가 곧바로 반환되어 wait()가 빠르게 풀리고,
        앱이 CLI 응답을 기다리며 길게 멈추지 않는다. 이후 새 호출은 시작과 동시에 죽는다.
        """
        with self._proc_lock:
            self._shutting_down = True
            procs = list(self._active_procs)
        for p in procs:
            try:
                p.kill()
            except Exception:
                pass
        logger.info(f"terminate_all: killed {len(procs)} in-flight CLI process(es).")

    def _log_request(self, session_id, model, prompt: str):
        """요청(입력)을 호출 즉시 디버그 로그에 best-effort 기록한다(응답 전에도 실시간 표시)."""
        try:
            from prismflow.core.cli_activity import get_cli_activity_log
            get_cli_activity_log().record_request(session_id, model, prompt)
        except Exception:
            pass

    def _log_response(self, session_id, model, response: str, kind: str = "ok"):
        """응답(출력)/오류를 완료 시점에 디버그 로그에 best-effort 기록한다(실행을 절대 방해하지 않음)."""
        try:
            from prismflow.core.cli_activity import get_cli_activity_log
            get_cli_activity_log().record_response(session_id, model, response, kind)
        except Exception:
            pass

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
        """`claude -p <tail_args>`를 shell 없이 1회 실행하고, 프롬프트는 STDIN으로 전달합니다.

        앱 종료 시 강제 중단이 가능하도록 subprocess.run 대신 추적 가능한 Popen으로 실행한다.
        """
        cmd = [self._cli_exe, "-p"] + tail_args
        logger.debug(f"Executing Claude CLI: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            shell=False,
            cwd=self._cli_cwd,
        )
        self._register_proc(proc)
        try:
            out, err = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.communicate()
            except Exception:
                pass
            raise
        finally:
            self._unregister_proc(proc)
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)

    @staticmethod
    def _looks_like_session_limit(text: str) -> bool:
        """오류 텍스트가 Claude CLI 사용량 한도(session limit) 신호인지 판별합니다."""
        t = (text or "").lower()
        return "session limit" in t or "limit" in t or "reset" in t

    @staticmethod
    def _is_permanent_launch_error(exc: Exception) -> bool:
        """재시도해도 무의미한 영구적 실행 실패(실행 파일 부재/권한 오류 등)인지 판별합니다."""
        return isinstance(exc, (FileNotFoundError, PermissionError, NotADirectoryError))

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
        """Claude CLI를 실행하여 응답을 받아옵니다(디버그 활동 로그 래퍼).

        실제 실행은 _execute_command_impl에 위임하고, 원본 세션명 기준으로 성공/오류 결과를
        CLI 활동 로그에 기록한다(로그 기록 실패는 무시되어 실행에 영향을 주지 않음).
        """
        self._log_request(session_id, model, prompt)
        try:
            out = self._execute_command_impl(prompt, session_id, model=model, timeout=timeout, system_prompt=system_prompt)
            self._log_response(session_id, model, out, "ok")
            return out
        except Exception as e:
            self._log_response(session_id, model, str(e), "error")
            raise

    def _execute_command_impl(self, prompt: str, session_id: str, model: Optional[str] = None,
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

        import time
        max_retries = 3
        delay = 1.0
        last_exception = None

        for attempt in range(max_retries):
            try:
                # 1단계: 기존 세션이 있는지 확인하고 재개하기 위해 --resume로 시도합니다.
                result = self._run_once(["--resume", session_id] + extra_args, prompt, timeout)

                # 만약 해당 세션 ID를 찾을 수 없는 경우 (최초 호출) --session-id로 폴백하여 세션을 생성합니다.
                if result.returncode != 0 and "No conversation found with session ID" in result.stderr:
                    logger.info(f"Session {session_id} not found. Initializing new session with --session-id.")
                    result = self._run_once(["--session-id", session_id] + extra_args, prompt, timeout)

                if result.returncode != 0:
                    err_msg = result.stderr.strip()
                    logger.error(f"Claude CLI execution failed (Code {result.returncode}) on attempt {attempt+1}: {err_msg}")
                    if self._looks_like_session_limit(err_msg):
                        # 사용량 한도는 재시도 무의미 → 상태 플래그 설정 후 즉시 전파
                        self._session_limited = True
                        raise RuntimeError(f"Claude CLI execution failed: {err_msg}")
                    # 비정상 종료코드는 순시(transient) 실패일 수 있어 재시도 대상으로 둡니다.
                    last_exception = RuntimeError(f"Claude CLI execution failed: {err_msg}")
                else:
                    return result.stdout.strip()

            except subprocess.TimeoutExpired:
                # 타임아웃은 호출자가 지정한 한도이므로 재시도해도 동일하게 만료됩니다 → 즉시 전파(불필요한 지연 방지).
                logger.error(f"Claude CLI execution timed out after {timeout} seconds.")
                raise TimeoutError(f"Claude CLI execution timed out after {timeout} seconds.")
            except RuntimeError:
                # 위에서 만든 session-limit RuntimeError는 그대로 전파합니다.
                raise
            except Exception as e:
                # 실행 파일 부재/권한 오류 등 영구적 실패는 재시도해도 무의미하므로 즉시 RuntimeError로 표준화합니다.
                if self._is_permanent_launch_error(e):
                    logger.error(f"Claude CLI executable could not be launched: {e}")
                    raise RuntimeError(
                        f"Claude CLI executable not found or not executable: '{self._cli_exe}' ({e})"
                    ) from e
                last_exception = e
                if self._looks_like_session_limit(str(e)):
                    self._session_limited = True
                    raise RuntimeError(f"Claude CLI session limit reached: {e}") from e

            # 마지막 시도이면 재시도 스킵
            if attempt == max_retries - 1:
                break

            logger.warning(f"Claude CLI connection temporary failure on attempt {attempt+1}. Retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

        # 모든 재시도 소진: 계약(RuntimeError/TimeoutError)에 맞춰 표준화하여 전파합니다.
        if isinstance(last_exception, (RuntimeError, TimeoutError)):
            raise last_exception
        if last_exception is not None:
            raise RuntimeError(
                f"Claude CLI execution failed after {max_retries} attempts: {last_exception}"
            ) from last_exception
        raise RuntimeError("Unknown error during Claude CLI execution.")

    def execute_command_stream(self, prompt: str, session_id: str, model: Optional[str] = None,
                               system_prompt: Optional[str] = None,
                               allowed_tools: Optional[List[str]] = None,
                               work_dir: Optional[str] = None,
                               permission_mode: Optional[str] = None):
        """Claude CLI를 실행하여 스트리밍 출력을 generator로 반환합니다.

        Args:
            prompt (str): Claude에게 전송할 프롬프트
            session_id (str): 대화 세션을 공유하기 위한 UUID 형식의 식별자
            model (str, optional): 사용할 Claude 모델
            system_prompt (str, optional): 기본(코딩 에이전트) 시스템 프롬프트를 대체할 에이전트 페르소나
            allowed_tools (list[str], optional): 사전 승인할 도구 목록(--allowedTools). 지정 시 해당 도구는
                비대화형(-p)에서도 권한 프롬프트 없이 실행된다. 미지정이면 기존처럼 도구 없는 순수 텍스트 응답.
            work_dir (str, optional): 도구 작업 디렉토리 샌드박스. 지정 시 CLI를 이 경로에서 실행하고
                --add-dir로 허용 디렉토리에 추가한다(파일 도구의 기본 경계).
            permission_mode (str, optional): --permission-mode 값(예: 'acceptEdits').

        Yields:
            str: 실시간 출력 라인
        """
        # claude CLI는 유효 UUID만 세션 ID로 허용하므로 의미 기반 세션명을 결정적 UUID로 정규화합니다.
        orig_session_id = session_id  # 디버그 로그용 원본 세션명(에이전트 식별)
        session_id = self._normalize_session_id(session_id)
        extra_args = self._build_extra_args(model, system_prompt)

        # 도구 사용 모드: 도구 화이트리스트 사전 승인 + 작업 폴더 샌드박스. 미지정 시 기존 텍스트 응답과 동일.
        cwd = self._cli_cwd
        if allowed_tools:
            extra_args += ["--allowedTools"] + list(allowed_tools)
        if work_dir:
            extra_args += ["--add-dir", work_dir]
            cwd = work_dir
        if permission_mode:
            extra_args += ["--permission-mode", permission_mode]

        # 요청을 호출 즉시 기록 → 응답 완료 전에도 디버그 창에 실시간으로 보인다.
        self._log_request(orig_session_id, model, prompt)

        # 세션 결정: 이 프로세스에서 이미 만든 세션이면 --resume, 아니면 --session-id로 생성.
        # '이미 사용 중' 충돌이 나면(이전 실행에서 만든 세션 등) --resume로 1회 폴백한다.
        # (기존 프로브 방식은 --resume로 빈 턴을 실제 실행해 세션을 오염시키고 충돌을 유발했음 → 제거.)
        already = session_id in self._created_sessions
        candidates = [True] if already else [False, True]

        collected = []
        last_err = ""
        try:
            for as_resume in candidates:
                flag = ["--resume", session_id] if as_resume else ["--session-id", session_id]
                cmd = [self._cli_exe, "-p"] + flag + extra_args
                logger.debug(f"Executing Claude CLI Stream: {' '.join(cmd)}")

                try:
                    proc = subprocess.Popen(
                        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, encoding='utf-8', errors='ignore', shell=False, cwd=cwd,
                    )
                except Exception as e:
                    if self._is_permanent_launch_error(e):
                        raise RuntimeError(f"Claude CLI Stream executable not found: {e}") from e
                    raise
                proc.stdin.write(prompt)
                proc.stdin.close()
                # 앱 종료 시 강제 중단이 가능하도록 추적 등록(끝나면 finally에서 해제)
                self._register_proc(proc)

                try:
                    # 첫 줄을 읽어 즉시 실패(세션 충돌 등)와 정상 스트리밍을 구분한다.
                    first = proc.stdout.readline()
                    if first == "":
                        proc.stdout.close()
                        proc.wait()
                        err = (proc.stderr.read() or "").strip()
                        proc.stderr.close()
                        last_err = err
                        el = err.lower()
                        if "session limit" in el or "limit" in el or "reset" in el:
                            self._session_limited = True
                        # 세션이 이미 존재 → 다음 후보(--resume)로 재시도
                        if (not as_resume) and ("already in use" in el or "already exists" in el):
                            self._created_sessions.add(session_id)
                            continue
                        if proc.returncode != 0 and err:
                            raise RuntimeError(f"Claude CLI Stream failed: {err}")
                        # 빈 응답이지만 정상 종료
                        self._created_sessions.add(session_id)
                        self._log_response(orig_session_id, model, "", "ok")
                        return

                    # 정상 스트리밍 시작
                    self._created_sessions.add(session_id)
                    collected.append(first)
                    yield first
                    for line in iter(proc.stdout.readline, ''):
                        collected.append(line)
                        yield line
                    proc.stdout.close()
                    proc.wait()
                finally:
                    self._unregister_proc(proc)
                if proc.returncode != 0:
                    err = (proc.stderr.read() or "").strip()
                    proc.stderr.close()
                    el = err.lower()
                    if "session limit" in el or "limit" in el or "reset" in el:
                        self._session_limited = True
                    if err:
                        raise RuntimeError(f"Claude CLI Stream failed: {err}")
                else:
                    proc.stderr.close()
                self._log_response(orig_session_id, model, "".join(collected), "ok")
                return

            # 모든 후보 소진(세션 충돌이 끝내 해소되지 않음)
            raise RuntimeError(f"Claude CLI Stream failed: {last_err or 'unknown error'}")
        except Exception as e:
            err_str = str(e)
            el = err_str.lower()
            if "session limit" in el or "limit" in el or "reset" in el:
                self._session_limited = True
            logger.error(f"Failed to run Claude CLI Stream: {err_str}")
            self._log_response(orig_session_id, model, err_str, "error")
            raise RuntimeError(f"Failed to run Claude CLI Stream: {err_str}") from e

    def is_session_limited(self) -> bool:
        """현재 Claude CLI가 사용량 한도 초과 상태인지 여부를 반환합니다."""
        return self._session_limited

    def set_session_limited(self, val: bool):
        """Claude CLI의 사용량 한도 초과 상태를 직접 설정합니다."""
        self._session_limited = val

