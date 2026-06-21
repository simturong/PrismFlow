import pytest
import numpy as np
import base64
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QEventLoop, QTimer

from prismflow.core.context import MeetingContext
from prismflow.core.cli_controller import ClaudeCLIController
from prismflow.core.screen_detector import ScreenTransitionDetector
from prismflow.agents.flow.mermaid_html import get_mermaid_html
from prismflow.agents.flow.flow_ui import FlowUI
from prismflow.agents.flow.flow_agent import FlowAgent

def test_mermaid_html_generation():
    """Mermaid.js HTML 생성 템플릿 검증"""
    html = get_mermaid_html()
    assert "mermaid.min.js" in html
    assert "updateDiagram" in html
    assert "diagram-container" in html

def test_flow_ui_init(q_app):
    """FlowUI 로드 및 다이어그램 업데이트 호출 검증"""
    ui = FlowUI()
    assert ui.windowTitle() == "PrismFlow Agent"
    assert ui.web_view is not None
    
    # 예외 없이 실행되는지 테스트
    ui.update_diagram("graph TD\nA-->B")
    
    # 엔진 모드 표시 검증 (Phase 14)
    ui.update_engine_mode("Claude")
    assert "Claude" in ui.title_label.text()
    ui.update_engine_mode("Local")
    assert "Local" in ui.title_label.text()

    ui.close()


def test_flow_ui_embedded_chat_toggle(q_app):
    """Phase 16: chat_panel을 주면 우측에 임베드되고 토글로 접고 펼칠 수 있다."""
    from PySide6.QtWidgets import QWidget
    chat = QWidget()
    ui = FlowUI(chat_panel=chat)
    try:
        # 임베드 + 토글 버튼 생성, 기본 펼침(숨김 아님)
        assert ui.chat_panel is chat
        assert ui.chat_toggle_btn is not None
        assert chat.isHidden() is False
        # 접기 → 숨김, 글리프 전환
        ui.toggle_chat_panel()
        assert chat.isHidden() is True
        assert ui.chat_toggle_btn.text() == "‹"
        # 다시 펼치기
        ui.toggle_chat_panel()
        assert chat.isHidden() is False
        assert ui.chat_toggle_btn.text() == "›"
    finally:
        ui.close()


def test_flow_ui_no_chat_panel_default(q_app):
    """chat_panel 미지정 시 단독 Flow로 동작(토글 버튼 없음)."""
    ui = FlowUI()
    try:
        assert ui.chat_panel is None
        assert ui.chat_toggle_btn is None
    finally:
        ui.close()


def test_flow_ui_headline_keyword_highlight(q_app):
    """헤드라인 핵심어 강조: 숫자/수량 토큰은 색상 span으로 감싸고, HTML은 안전하게 이스케이프한다."""
    ui = FlowUI()
    out = ui._highlight_keywords("예산 30% 증액, 2026년 3건 승인")
    # 숫자/수량 토큰 강조
    assert "<span" in out and "30%" in out and "2026년" in out and "3건" in out
    # 평문 부분은 보존
    assert "예산" in out and "승인" in out

    # HTML 특수문자 안전 처리 (마크업 주입 방지)
    safe = ui._highlight_keywords("a<b>&c 5개")
    assert "<b>" not in safe and "&lt;b&gt;" in safe and "&amp;c" in safe
    assert "5개" in safe
    ui.close()

def test_screen_detector_generic_fallback(q_app):
    """범용 화면 감지기 픽셀 분석 및 디바운싱 동작 검증"""
    # 빠른 테스트를 위해 디바운스 시간을 0.1초로 설정
    detector = ScreenTransitionDetector(debounce_sec=0.1, check_interval_ms=10)
    
    # transition_detected 신호 수신 확인용 변수
    detected_events = []
    
    def on_detected(ttype, info):
        detected_events.append((ttype, info))
        
    detector.transition_detected.connect(on_detected)
    
    # 1. 캡처 프레임 모킹
    frame1 = np.zeros((32, 32), dtype=np.float32)
    frame2 = np.ones((32, 32), dtype=np.float32) * 50.0  # MSE가 임계치 10.0을 훌쩍 넘게 설정
    
    # win32com PPT는 기동 안 됨을 가정하여 None 모킹
    with patch.object(detector, '_get_active_ppt_info', return_value=None):
        # 첫 번째 체크 (기준 프레임 설정)
        with patch.object(detector, '_capture_generic_frame_32x32', return_value=frame1):
            detector._check_screen()
            
        assert detector.debounce_timer.isActive() == False
        
        # 두 번째 체크 (픽셀 변화율 감지 -> 디바운싱 타이머 시작)
        with patch.object(detector, '_capture_generic_frame_32x32', return_value=frame2):
            detector._check_screen()
            
        assert detector.debounce_timer.isActive() == True
        assert detector.pending_type == "GENERIC"
        
        # 0.1초 디바운싱 정착(Settled) 대기
        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec()
        
        # 정착 완료 이벤트 검증
        assert len(detected_events) == 1
        assert detected_events[0][0] == "GENERIC"
        assert np.array_equal(detected_events[0][1], frame2)

@patch('win32com.client.GetActiveObject')
def test_screen_detector_ppt_detection(mock_get_active, q_app):
    """PowerPoint 실행 시 COM API 기반 감지 및 디바운싱 검증"""
    detector = ScreenTransitionDetector(debounce_sec=0.1, check_interval_ms=10)
    
    # PPT COM 객체 구조 모킹
    mock_app = MagicMock()
    mock_pres = MagicMock()
    mock_pres.Name = "presentation1.pptx"
    mock_app.Presentations.Count = 1
    mock_app.ActivePresentation = mock_pres
    
    # 슬라이드 쇼 모드 모킹 (SlideIndex = 3)
    mock_app.SlideShowWindows.Count = 1
    mock_app.SlideShowWindows(1).View.Slide.SlideIndex = 3
    
    mock_get_active.return_value = mock_app
    
    detected_events = []
    detector.transition_detected.connect(lambda t, i: detected_events.append((t, i)))
    
    with patch('prismflow.core.screen_detector.HAS_WIN32COM', True):
        # 1차 체크 (SlideIndex=3 감지 -> 디바운싱 타이머 시작)
        detector._check_screen()
        assert detector.debounce_timer.isActive() == True
        assert detector.pending_type == "PPT"
        assert detector.pending_info == ("presentation1.pptx", 3)
        
        # 0.1초 대기하여 정착 확정
        loop = QEventLoop()
        QTimer.singleShot(150, loop.quit)
        loop.exec()
        
        assert len(detected_events) == 1
        assert detected_events[0] == ("PPT", ("presentation1.pptx", 3))

def test_flow_agent_trigger_cadence():
    """FlowAgent 갱신 트리거 결정 로직 검증: 최초/주제전환(버스트)/정기 캐치업.

    핵심 회귀 방어: 주제가 바뀌어 발화가 몰리면(버스트) 정기 주기(15초)를 기다리지 않고
    훨씬 짧은 바닥 간격(8초)만 지나도 즉시 갱신되어 실시간성이 보장되어야 한다.
    """
    context = MeetingContext()
    context.reset()
    mock_cli = MagicMock()
    agent = FlowAgent(context, mock_cli, check_interval_sec=15.0, burst_threshold=3, min_interval_sec=8.0)

    # 1) 최초 흐름도: 다이어그램이 아직 없으면 3초 바닥만 지나도 즉시 띄운다.
    assert agent._should_trigger(new_since=1, elapsed=3.0, has_diagram=False) is True
    assert agent._should_trigger(new_since=1, elapsed=2.0, has_diagram=False) is False

    # 2) 주제 전환(버스트): 발화 3개↑ + 8초 바닥 → 정기 15초 전이라도 즉시 갱신.
    assert agent._should_trigger(new_since=3, elapsed=8.0, has_diagram=True) is True
    assert agent._should_trigger(new_since=3, elapsed=7.9, has_diagram=True) is False  # 바닥 미달
    assert agent._should_trigger(new_since=2, elapsed=12.0, has_diagram=True) is False  # 버스트 임계 미달

    # 3) 정기 캐치업: 새 발화 1개라도 정기 주기 경과 시 갱신, 주기 전이면 보류.
    assert agent._should_trigger(new_since=1, elapsed=15.0, has_diagram=True) is True
    assert agent._should_trigger(new_since=1, elapsed=14.0, has_diagram=True) is False

    context.reset()


def test_flow_agent_bounded_stop_does_not_block(q_app):
    """회의 종료 프리즈 방지: 진행 중인 CLI 호출이 있어도 stop(wait_ms)는 바운드 시간 내 반환한다.

    핵심: stop(wait_ms=100)는 합류하지 못하면 False를 반환하되 메인 스레드를 CLI 호출 시간만큼
    잡아두지 않아야 한다(프리즈 없음). 이후 unbounded stop()으로 안전하게 합류한다.
    """
    import time
    context = MeetingContext()
    context.reset()
    context.start_meeting("s_stop_bound", "프리즈 방지")
    context.add_transcript("Speaker_00", "분석 트리거용 발화")

    mock_cli = MagicMock()
    mock_cli.is_session_limited.return_value = False

    def slow_execute(*a, **k):
        time.sleep(1.5)  # 진행 중인 느린 CLI 호출을 모사
        return "graph TD\nA-->B"
    mock_cli.execute_command = slow_execute

    agent = FlowAgent(context, mock_cli, check_interval_sec=0.1, burst_threshold=1, min_interval_sec=0.0)
    agent.start()
    try:
        time.sleep(0.5)  # 에이전트가 느린 CLI 호출에 진입할 시간을 준다

        t0 = time.monotonic()
        joined = agent.stop(wait_ms=100)
        elapsed = time.monotonic() - t0

        assert joined is False          # 진행 중 호출로 100ms 내 합류 불가
        assert elapsed < 0.6            # 그러나 바운드 대기라 즉시 반환(메인 스레드 프리즈 없음)
        assert agent.isRunning() is True
    finally:
        agent.stop()                    # unbounded 합류로 안전하게 회수
        assert agent.isRunning() is False
        context.end_meeting()
        context.reset()


def test_flow_agent_prompt_integration():
    """FlowAgent 발화 내용 및 시각 지시어/화면 맥락 결합 프롬프트 전달 검증"""
    context = MeetingContext()
    context.reset()
    context.start_meeting("test_session_abc", "시각 지시어 테스트")
    
    # 1. 시각 지시어가 포함된 대화 내용 주입
    context.add_transcript("Speaker_00", "네, 여기 보시면 1분기 매출 증가 그래프가 있습니다.")
    
    # 2. 화면 감지 정보 업데이트
    context.update_screen_info("PPT", ("sales_report.pptx", 5))
    
    # 3. CLI 컨트롤러 모킹
    mock_cli = MagicMock()
    mock_cli.is_session_limited.return_value = False
    
    agent = FlowAgent(context, mock_cli, check_interval_sec=0.1)
    
    # 분석 실행 및 조합되는 프롬프트 내용 가로채기
    captured_prompt = ""
    captured_model = ""
    def fake_execute(prompt, session_id, model, system_prompt=None):
        nonlocal captured_prompt, captured_model
        captured_prompt = prompt
        captured_model = model
        return "graph TD\nA-->B"
        
    mock_cli.execute_command = fake_execute
    
    # 내부 분석 함수 직접 작동
    agent._analyze_and_update(context.transcripts)
    
    # 프롬프트 검증
    # 발화 텍스트, PPT 슬라이드 파일명 및 페이지 정보가 프롬프트 내에 바인딩되어 있는지 확인
    assert "sales_report.pptx" in captured_prompt
    assert "5페이지" in captured_prompt
    assert "Here 보시면" or "여기 보시면" in captured_prompt
    assert captured_model == "claude-haiku-4-5"
    
    # Context에 생성된 Mermaid 코드가 올바르게 피드백되었는지 확인
    assert context.current_mermaid_code == "graph TD\nA-->B"
    
    context.end_meeting()
    context.reset()
