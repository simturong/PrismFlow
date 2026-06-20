import time
import logging
import re
from typing import Optional
from PySide6.QtCore import QThread, Signal

from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController

logger = logging.getLogger(__name__)

# claude CLI를 코딩 에이전트가 아닌 "Mermaid 흐름도 생성 엔진"으로 동작시키기 위한 시스템 프롬프트.
FLOW_SYSTEM_PROMPT = (
    "당신은 회의 발화를 분석해 Mermaid.js 흐름도를 생성하는 시각화 엔진입니다. "
    "반드시 유효한 Mermaid flowchart 코드만 출력하십시오. 인사·설명·메타 문구 없이 "
    "'graph TD' 또는 'flowchart TD'로 시작하는 코드만 반환하고, 도구·파일 작업을 하지 마십시오."
)

class FlowAgent(QThread):
    """30초 주기로 회의 발화를 분석하여 Mermaid.js 흐름도를 갱신하는 백그라운드 에이전트 QThread."""
    
    # 갱신 완료 신호: 새롭게 파싱된 Mermaid 코드
    diagram_updated = Signal(str)
    
    def __init__(self, context: MeetingContext, cli_controller: ClaudeCLIController, check_interval_sec: float = 30.0):
        super().__init__()
        self.context = context
        self.cli_controller = cli_controller
        self.check_interval_sec = check_interval_sec
        self.running = False
        
        # Flow Agent 전용 고유 세션 ID (매 회의마다 새로 생성)
        self.flow_session_id: Optional[str] = None
        
    def run(self):
        self.running = True
        logger.info("FlowAgent Thread started.")
        
        # 회의 세션 기반으로 Flow 전용 CLI 세션 UUID 정의
        self.flow_session_id = f"flow-session-{self.context.current_session_id}"
        
        # 마지막 분석 시점의 발화 개수 기록 (발화 추가 시에만 API 호출 유도)
        last_analyzed_count = 0
        
        # 30초 대기를 정밀하게 처리하기 위한 누적 카운터 (100ms 단위)
        wait_counter = 0
        trigger_ticks = int(self.check_interval_sec * 10)
        
        while self.running:
            # 회의가 진행 중일 때만 주기적으로 분석
            if self.context.is_meeting_active:
                if wait_counter >= trigger_ticks:
                    wait_counter = 0
                    
                    transcripts = self.context.transcripts
                    current_count = len(transcripts)
                    
                    # 새로운 발화가 추가되었거나 아직 다이어그램이 없는 경우에만 실행
                    if current_count > 0 and (current_count != last_analyzed_count or not self.context.current_mermaid_code):
                        self._analyze_and_update(transcripts)
                        last_analyzed_count = current_count
                else:
                    wait_counter += 1
            else:
                # 회의 미작동 시 분석 대기 리셋
                wait_counter = 0
                last_analyzed_count = 0
                
            self.msleep(100)  # 100ms 대기 (빠른 스레드 종료 대응)
            
        logger.info("FlowAgent Thread stopped.")

    def stop(self):
        """에이전트 루프를 안전하게 종료합니다."""
        self.running = False
        self.wait()

    def _analyze_and_update(self, transcripts: list):
        """최근 발화 내용 및 화면 맥락을 수집하여 Claude CLI로 Mermaid 코드를 갱신합니다."""
        # 1. 최근 10분 이내 혹은 누적 발화 문자열 생성
        transcript_lines = []
        has_visual_indicator = False
        visual_keywords = ["여기 보시면", "이 슬라이드", "이 도표", "이 그림", "이 화면", "여기를 보면"]
        
        for item in transcripts:
            line = f"[{item['speaker']}] {item['text']}"
            transcript_lines.append(line)
            
            # 발화 텍스트 중 시각 지시어 포함 여부 검사
            if not has_visual_indicator:
                for kw in visual_keywords:
                    if kw in item['text']:
                        has_visual_indicator = True
                        break
                        
        transcript_text = "\n".join(transcript_lines)
        
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

        # 3. 프롬프트 구성 (Stateful Upsert 제약 포함)
        prev_mermaid = self.context.current_mermaid_code or "없음 (최초 작성)"
        
        prompt = f"""당신은 오프라인 회의 흐름도 시각화를 돕는 Flow Agent입니다.
아래의 [회의 발화 내역]과 [기존 Mermaid 코드]를 참고하여, 회의의 핵심 흐름과 논의 사항을 반영하는 Mermaid flowchart TD 코드를 작성해 주세요.

[회의 발화 내역]
{transcript_text}
{screen_context_prompt}

[기존 Mermaid 코드]
{prev_mermaid}

[중요 작성 규칙]
1. 반드시 마크다운 코드 펜스(```mermaid 등)나 안내 문구를 모두 배제하고, graph TD 또는 flowchart TD로 시작하는 순수한 Mermaid flowchart 코드만 출력하세요.
2. [기존 Mermaid 코드]의 노드 ID(예: A, B, C 등)와 구조를 최대한 재사용(Upsert)하여 기존 흐름을 유지하세요. 새로 논의된 소주제 사항만 기존 흐름 아래에 새 노드로 연결하여 덧붙여 나가세요.
3. 대주제나 논의 단계가 바뀌면 subgraph로 그룹화하여 나타내세요.
4. 단순 인사말, 잡담, 중복 추임새는 노드에 추가하지 말고 노이즈로 필터링하세요.
5. 화자 정보(예: Speaker_00)를 노드 텍스트에 간략히 표기해 주세요 (예: "아이디어 제안 (Speaker_00)").
"""
        try:
            logger.info("Requesting Mermaid diagram update from Claude CLI...")
            # Haiku 모델을 명시하여 호출
            response = self.cli_controller.execute_command(
                prompt=prompt,
                session_id=self.flow_session_id,
                model="claude-haiku-4-5",
                system_prompt=FLOW_SYSTEM_PROMPT
            )
            
            # 4. 결과 파싱 및 검증
            parsed_code = self._clean_mermaid_code(response)
            if parsed_code and ("graph " in parsed_code or "flowchart " in parsed_code):
                logger.info("Successfully updated Mermaid diagram code.")
                self.context.update_mermaid_code(parsed_code)
                self.diagram_updated.emit(parsed_code)
            else:
                logger.warning(f"Claude returned invalid Mermaid code format: {response[:100]}...")
        except Exception as e:
            logger.error(f"Error during FlowAgent analysis loop: {str(e)}")

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
