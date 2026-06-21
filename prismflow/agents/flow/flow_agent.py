import time
import logging
import re
from typing import Optional
from PySide6.QtCore import QThread, Signal

from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController

logger = logging.getLogger(__name__)

# claude CLI를 코딩 에이전트가 아닌 "Mermaid 흐름도 및 뉴스 요약 생성 엔진"으로 동작시키기 위한 시스템 프롬프트.
FLOW_SYSTEM_PROMPT = (
    "당신은 회의 발화를 분석해 Mermaid.js 흐름도와 실시간 뉴스 한 줄 요약을 생성하는 시각화 엔진입니다. "
    "출력 형식은 반드시 다음과 같이 맨 위에 1줄 핵심 요약, 그 뒤에 '===' 구분자, 그리고 순수한 Mermaid flowchart 코드를 작성하십시오.\n"
    "양식 예시:\n"
    "이번 회의에서 A 의제를 승인하고 담당자를 지정함\n"
    "===\n"
    "graph TD\n"
    "  A[의제 승인] --> B[담당자 지정]\n"
    "인사·설명·메타 문구는 절대 반환하지 말고, 마크다운 코드 펜스(```)도 사용하지 마십시오. 오직 위의 양식만 그대로 준수하십시오."
)

class FlowAgent(QThread):
    """30초 주기로 회의 발화를 분석하여 Mermaid.js 흐름도와 뉴스 요약을 갱신하는 백그라운드 에이전트 QThread."""
    
    # 갱신 완료 신호: 새롭게 파싱된 Mermaid 코드
    diagram_updated = Signal(str)
    # 신규 핵심 요약 신호 (뉴스 자막용)
    summary_updated = Signal(str)
    # 상태 가시화 신호 (Phase 10): 분석(CLI 호출) 시작 / 실패
    analysis_started = Signal()
    analysis_failed = Signal(str)
    
    def __init__(self, context: MeetingContext, cli_controller: ClaudeCLIController, check_interval_sec: float = 30.0,
                 burst_threshold: int = 3, min_interval_sec: float = 8.0):
        super().__init__()
        self.context = context
        self.cli_controller = cli_controller
        # 정기 갱신 주기(상한). 이 시간이 지나면 새 발화가 1개라도 있으면 갱신한다.
        self.check_interval_sec = check_interval_sec
        # 조기 갱신 트리거: 직전 분석 이후 발화가 이 개수 이상 쌓이면(=주제 전환 신호) 주기를 기다리지 않고 즉시 갱신.
        self.burst_threshold = burst_threshold
        # 조기 갱신의 최소 간격(바닥). CLI 호출 폭주를 막기 위한 하한선.
        self.min_interval_sec = min_interval_sec
        self.running = False

        # Flow Agent 전용 고유 세션 ID (매 회의마다 새로 생성)
        self.flow_session_id: Optional[str] = None
        self.last_analyzed_idx = -1

    def run(self):
        import time
        self.running = True
        logger.info("FlowAgent Thread started.")

        # 회의 세션 기반으로 Flow 전용 CLI 세션 UUID 정의
        self.flow_session_id = f"flow-session-{self.context.current_session_id}"

        # 마지막 분석 시점의 발화 인덱스/카운트/시각 기록 (회의 시작 시 리셋)
        self.last_analyzed_idx = -1
        last_analyzed_count = 0
        last_analysis_t = 0.0  # 0.0 = 아직 한 번도 분석 안 함

        while self.running:
            # 회의가 진행 중일 때만 분석. 폴링은 100ms로 촘촘히 돌되, 실제 CLI 호출은 아래 조건이 충족될 때만.
            if self.context.is_meeting_active:
                transcripts = self.context.transcripts
                count = len(transcripts)
                if count > 0:
                    now = time.monotonic()
                    new_since = count - last_analyzed_count
                    elapsed = (now - last_analysis_t) if last_analysis_t else float("inf")
                    has_diagram = bool(self.context.current_mermaid_code)

                    if self._should_trigger(new_since, elapsed, has_diagram):
                        self._analyze_and_update(transcripts)
                        last_analysis_t = time.monotonic()
                        last_analyzed_count = count
            else:
                # 회의 미작동 시 분석 대기 리셋
                last_analyzed_count = 0
                last_analysis_t = 0.0
                self.last_analyzed_idx = -1

            self.msleep(100)  # 100ms 대기 (빠른 스레드 종료 대응)

        logger.info("FlowAgent Thread stopped.")

    def _should_trigger(self, new_since: int, elapsed: float, has_diagram: bool) -> bool:
        """이번 폴링 틱에서 흐름도를 갱신(CLI 호출)할지 결정하는 순수 함수.

        세 가지 트리거:
          1) 최초 흐름도: 아직 다이어그램이 없으면 짧은 바닥(≤3초)만 지나도 가능한 한 빨리 띄운다.
          2) 주제 전환(버스트): 직전 분석 이후 발화가 burst_threshold개 이상 쌓였고, CLI 폭주
             방지 바닥(min_interval_sec, 단 정기 주기를 넘지 않음)을 지났으면 주기를 기다리지 않고 즉시.
          3) 정기 캐치업: 정기 주기가 지났고 새 발화가 1개라도 있으면 갱신.
        """
        burst_floor = min(self.min_interval_sec, self.check_interval_sec)
        if not has_diagram and elapsed >= min(self.check_interval_sec, 3.0):
            return True
        if new_since >= self.burst_threshold and elapsed >= burst_floor:
            return True
        if new_since >= 1 and elapsed >= self.check_interval_sec:
            return True
        return False

    def stop(self, wait_ms: Optional[int] = None) -> bool:
        """에이전트 루프 종료를 요청한다.

        wait_ms=None이면 스레드가 끝날 때까지 합류 대기한다(앱 종료 등). 정수면 그 시간(ms)만
        바운드 대기하고 합류 여부를 bool로 반환한다. 회의 종료 시 메인 스레드가 진행 중인 Flow
        CLI 호출(최대 수십 초)에 막혀 프리즈되지 않도록, 코디네이터가 짧은 바운드 대기로 호출한다.
        """
        self.running = False
        if wait_ms is None:
            self.wait()
            return True
        return bool(self.wait(wait_ms))

    def _analyze_and_update(self, transcripts: list):
        """최근 발화 내용 및 화면 맥락을 수집하여 Claude CLI로 Mermaid 코드를 갱신합니다."""
        # 상태 가시화: 분석(생성) 시작을 알림 (Flow 뱃지 '생성중' 표시용)
        self.analysis_started.emit()
        # 1. 최근 15개 발화록 슬라이딩 윈도우 추출 (맥락 보존 및 입력 토큰 다이어트)
        recent_transcripts = transcripts[-15:]
        recent_lines = []
        has_visual_indicator = False
        visual_keywords = ["여기 보시면", "이 슬라이드", "이 도표", "이 그림", "이 화면", "여기를 보면"]
        
        for item in recent_transcripts:
            line = f"[{item['speaker']}] {item['text']}"
            recent_lines.append(line)
            # 발화 텍스트 중 시각 지시어 포함 여부 검사
            for kw in visual_keywords:
                if kw in item['text']:
                    has_visual_indicator = True
                    break
                    
        recent_transcripts_text = "\n".join(recent_lines)
        max_idx = len(transcripts) - 1
        
        # 2. 스마트 화면 맥락 결합 (시각 지시어가 감지되었고 최근 화면 정보가 있을 때)
        screen_context_prompt = ""
        last_screen = self.context.last_screen_info
        if has_visual_indicator and last_screen:
            stype = last_screen.get("type")
            sinfo = last_screen.get("info")
            if stype == "PPT" and isinstance(sinfo, (list, tuple)):
                screen_context_prompt = f"\n[참고: 현재 사용자가 발표 중인 PPT 슬라이드는 '{sinfo[0]}' 파일의 {sinfo[1]}페이지입니다. 발표자가 '이 슬라이드', '여기 보시면' 등 화면을 언급하고 있으므로 이 슬라이드 정보를 회의 흐름도 생성에 핵심 맥락으로 반영해 주세요.]"
            elif stype == "GENERIC":
                screen_context_prompt = "\n[참고: 사용자가 최근 활성 창을 다른 화면으로 전환했습니다. 발표자가 화면을 가리켜 말하고 있으므로 화면 전환 상태를 고려하여 흐름을 정리해 주세요.]"

        # 3. 프롬프트 구성 (Stateful Upsert 제약 포함, 발화록 15개 및 기존 다이어그램 전달)
        prev_mermaid = self.context.current_mermaid_code or "없음 (최초 작성)"
        
        prompt = f"""당신은 오프라인 회의 흐름도 시각화를 돕는 Flow Agent입니다.
제공된 [기존 Mermaid 코드]는 지금까지의 전체 회의 지도입니다. [최근 15개 회의 발화 내역]을 참고하여 기존 지도의 노드 구조를 유지하며 흐름도를 갱신해 주세요.

[최근 15개 회의 발화 내역]
{recent_transcripts_text}
{screen_context_prompt}

[기존 Mermaid 코드]
{prev_mermaid}

[중요 작성 규칙]
1. 출력 형식은 반드시 다음과 같이 구성하세요:
<현재 논의 중인 대화 전체의 핵심 요약 1문장 (뉴스 자막용, 공백 포함 30자 내외)>
===
<graph TD 또는 flowchart TD로 시작하는 순수한 Mermaid flowchart 코드>
2. 반드시 마크다운 코드 펜스(```mermaid 등)나 안내 문구를 모두 배제하고 위의 양식대로만 출력하세요.
3. [기존 Mermaid 코드]의 노드 ID(예: A, B, C 등)와 구조를 최대한 재사용(Upsert)하여 기존 흐름을 유지하세요. 새로 논의된 소주제 사항만 기존 흐름 아래에 새 노드로 연결하여 덧붙여 나가세요.
4. 대주제나 논의 단계가 바뀌면 subgraph로 그룹화하여 나타내세요.
5. 단순 인사말, 잡담, 중복 추임새는 노드에 추가하지 말고 노이즈로 필터링하세요.
6. 화자 식별자(Speaker_00, Speaker_01 등)는 노드 및 다이어그램에 절대 포함하지 마십시오. 오직 논의 흐름과 핵심 내용만으로 노드를 구성해야 합니다.
"""
        # 4. 세션 리밋 상태이면 즉각 로컬 대체(Fallback) 모드 구동
        if self.cli_controller.is_session_limited():
            logger.warning("Claude CLI is session limited. Generating local fallback Mermaid diagram...")
            fallback_code = self._fallback_generate_mermaid(transcripts)
            self.context.update_mermaid_code(fallback_code)
            self.diagram_updated.emit(fallback_code)
            fallback_summary = "대체 모드: 대화 기록을 기반으로 타임라인을 표시합니다."
            if transcripts:
                fallback_summary = f"최근 논의: {transcripts[-1]['text'][:30]}..."
            self.summary_updated.emit(fallback_summary)
            return

        try:
            logger.info("Requesting Mermaid diagram update from Claude CLI...")
            # Haiku 모델을 명시하여 호출
            response = self.cli_controller.execute_command(
                prompt=prompt,
                session_id=self.flow_session_id,
                model="claude-haiku-4-5",
                system_prompt=FLOW_SYSTEM_PROMPT
            )
            
            # 5. 결과 파싱 및 검증
            summary = "현재 대화가 진행 중입니다..."
            mermaid_part = response
            if "===" in response:
                parts = response.split("===", 1)
                summary = parts[0].strip()
                mermaid_part = parts[1].strip()

            parsed_code = self._clean_mermaid_code(mermaid_part)
            if parsed_code and ("graph " in parsed_code or "flowchart " in parsed_code):
                logger.info("Successfully updated Mermaid diagram code and summary.")
                self.context.update_mermaid_code(parsed_code)
                self.diagram_updated.emit(parsed_code)
                self.summary_updated.emit(summary)
                self.last_analyzed_idx = max_idx
            else:
                logger.warning(f"Claude returned invalid Mermaid code format: {response[:100]}...")
        except Exception as e:
            logger.error(f"Error during FlowAgent analysis loop: {str(e)}")
            # 상태 가시화: CLI 입출력 실패를 알림 (Flow 뱃지 오류 표시용)
            self.analysis_failed.emit(str(e)[:24])
            # 장애 발생 시 로컬 룰베이스 폴백 연동
            logger.info("Falling back to local rule-based Mermaid generator...")
            fallback_code = self._fallback_generate_mermaid(transcripts)
            self.context.update_mermaid_code(fallback_code)
            self.diagram_updated.emit(fallback_code)
            fallback_summary = "대체 모드: 대화 기록을 기반으로 타임라인을 표시합니다."
            if transcripts:
                fallback_summary = f"최근 논의: {transcripts[-1]['text'][:30]}..."
            self.summary_updated.emit(fallback_summary)
            self.last_analyzed_idx = max_idx

    def _fallback_generate_mermaid(self, transcripts: list) -> str:
        """클라우드 한도 초과 시 로컬 발화 관계 및 타임라인을 나타내는 룰베이스 Mermaid flowchart TD를 생성합니다."""
        code = "graph TD\n"
        code += "    subgraph LocalFallback[⚠️ 로컬 대체 모드]\n"
        
        # 최근 10개 발화의 요약을 노드로 생성하고 순차 연결합니다. (화자 식별자 배제)
        recent = transcripts[-10:]
        node_ids = []
        for i, item in enumerate(recent):
            txt = item["text"].strip()
            # 특수문자 제거 및 요약
            txt_clean = re.sub(r'["\'\(\)\{\}\[\]]', '', txt)
            txt_trunc = txt_clean[:20] + "..." if len(txt_clean) > 20 else txt_clean
            node_id = f"Node{i}"
            code += f"        {node_id}[\"{txt_trunc}\"]\n"
            node_ids.append(node_id)
            
        for i in range(len(node_ids) - 1):
            code += f"        {node_ids[i]} --> {node_ids[i+1]}\n"
            
        code += "    end"
        return code

    def _clean_mermaid_code(self, raw_response: str) -> str:
        """반환된 텍스트에서 불필요한 마크다운 코드 블록 및 주석을 정제하여 순수 Mermaid 코드만 추출합니다."""
        # 1. ```mermaid ... ``` 또는 ``` ... ``` 추출
        match = re.search(r'```(?:mermaid)?\s*(.*?)\s*```', raw_response, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
        else:
            code = raw_response.strip()
            
        # 2. 앞뒤 안내 텍스트가 섞여있다면 graph/flowchart 시작 부분부터 추출
        if "graph " not in code and "flowchart " not in code:
            # 원본 반응에서 혹시 매칭되는 부분이 있는지 재탐색
            match_start = re.search(r'(graph\s+\w+|flowchart\s+\w+).*', code, re.DOTALL | re.IGNORECASE)
            if match_start:
                code = match_start.group(0).strip()
                
        # 3. 혹시나 남아있을 수 있는 앞뒤 빈 라인 정리
        lines = [line for line in code.split('\n') if not line.strip().startswith('```')]
        return '\n'.join(lines).strip()
