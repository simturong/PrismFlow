import pytest
import time
from prismflow.core.context import MeetingContext
from prismflow.core.config import AppConfig
from prismflow.agents.stt.stt_agent import RealTimeEngineWorker
from prismflow.agents.stt.audio import MOCK_DIALOGUES

@pytest.fixture
def mock_stt_config(temp_config):
    # 테스트 속도를 위해 mock interval을 0.05초로 지정
    temp_config.stt_mock_mode = True
    temp_config.stt_mock_interval = 0.05
    return temp_config

def test_stt_mock_mode_pipeline(q_app, mock_stt_config, monkeypatch):
    """STT 스레드가 Mock 모드일 때 대화 데이터가 정기적으로 context에 적재되는지 검증"""
    # AppConfig가 모킹된 설정을 가져가도록 패치
    monkeypatch.setattr(AppConfig, "load_default", lambda: mock_stt_config)
    
    context = MeetingContext()
    context.reset() # 초기화
    
    # 스레드 생성
    worker = RealTimeEngineWorker()
    
    # 스레드 기동 상태 모니터링 시그널 수집
    status_history = []
    worker.status_changed.connect(status_history.append)
    
    # 1. 회의 활성화 전 기동
    worker.start()
    
    # 스레드가 기동될 때까지 대기 (최대 0.5초)
    for _ in range(50):
        if worker.isRunning():
            break
        time.sleep(0.01)
        
    assert worker.isRunning() is True
    # 회의가 아직 시작되지 않았으므로 transcripts는 비어있어야 함
    assert len(context.transcripts) == 0
    
    # 2. 회의 시작
    session_id = "test_stt_sess_1"
    context.start_meeting(session_id, title="STT 테스트 미팅")
    
    # QThread가 돌아가면서 발화를 쌓도록 대기 및 이벤트 처리
    # mock_interval이 0.05초이므로 0.5초 대기하면 최소 3개 이상 쌓여야 함
    # 타이밍 마진을 고려해 루프 대기를 100회(최대 1.0초)로 넉넉하게 지정
    for _ in range(100):
        q_app.processEvents()
        time.sleep(0.01)
        if len(context.transcripts) >= 3:
            break
            
    assert len(context.transcripts) >= 3
    # 데이터가 MOCK_DIALOGUES와 부합하는지 검증
    for i, item in enumerate(context.transcripts[:3]):
        assert item["speaker"] == MOCK_DIALOGUES[i][0]
        assert item["text"] == MOCK_DIALOGUES[i][1]
        assert item["start_time"] == MOCK_DIALOGUES[i][2]
        assert item["end_time"] == MOCK_DIALOGUES[i][3]
        
    # 3. 회의 종료 후 스레드가 추가 데이터를 주입하지 않고 대기 상태로 가는지 검증
    context.end_meeting()
    current_count = len(context.transcripts)
    time.sleep(0.1)
    q_app.processEvents()
    assert len(context.transcripts) == current_count
    
    # 4. 스레드 정지 및 마무리
    worker.stop()
    q_app.processEvents()  # 시그널 배달 보장
    assert worker.isRunning() is False
    assert "running" in status_history
    assert "idle" in status_history

def test_stt_real_mode_error_fallback(q_app, mock_stt_config, monkeypatch):
    """실제 모드 구동 시 라이브러리 부재나 장치 에러로 예외 발생 및 에러 시그널 전파 검증"""
    mock_stt_config.stt_mock_mode = False
    monkeypatch.setattr(AppConfig, "load_default", lambda: mock_stt_config)
    
    worker = RealTimeEngineWorker()
    
    error_msgs = []
    worker.error_occurred.connect(error_msgs.append)
    
    # 스레드 시작
    worker.start()
    
    # 스레드가 기동될 때까지 대기
    for _ in range(50):
        if worker.isRunning():
            break
        time.sleep(0.01)
    
    # run_real_loop에서 예외가 나서 error_occurred 시그널 방출 후 스레드가 종료될 때까지 대기
    # 최대 1.0초 대기
    for _ in range(100):
        q_app.processEvents()
        time.sleep(0.01)
        if not worker.isRunning():
            break
            
    assert worker.isRunning() is False
    q_app.processEvents()  # 시그널 배달 보장
    assert len(error_msgs) > 0
    # 환경에 따라 라이브러리 미설치 에러 또는 오디오 장치 에러가 잡혀야 함
    assert any("실패" in msg or "없습니다" in msg or "오류" in msg for msg in error_msgs)

