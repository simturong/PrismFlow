import threading
import pytest
import time
from prismflow.core.config import AppConfig
from prismflow.core.context import MeetingContext
from prismflow.core.db import DatabaseManager

def test_config_load(temp_config):
    """AppConfig가 올바른 임시 경로 정보를 불러오는지 테스트"""
    assert "test_prismflow.db" in temp_config.db_path
    assert "test_reports" in temp_config.docs_save_dir
    assert temp_config.stt_mock_mode is True

def test_context_singleton(q_app):
    """MeetingContext가 싱글톤으로 동작하는지 확인"""
    context1 = MeetingContext()
    context2 = MeetingContext()
    assert context1 is context2

def test_context_state_transition(q_app):
    """회의 시작 및 종료에 따른 상태 전이 및 시그널 방출 검증"""
    context = MeetingContext()
    
    # 1. 초기화 상태 검증
    # 이전 테스트 영향이 있을 수 있으므로 reset() 호출로 상태 초기화 보장
    context.reset()
    assert context.is_meeting_active is False
    assert context.current_session_id is None
    
    # 시작 시그널 모니터링
    started_session = None
    def on_started(sess_id):
        nonlocal started_session
        started_session = sess_id
    context.signals.meeting_started.connect(on_started)
    
    # 2. 회의 시작 테스트
    success = context.start_meeting("sess_test_123")
    assert success is True
    assert context.is_meeting_active is True
    assert context.current_session_id == "sess_test_123"
    assert started_session == "sess_test_123"
    
    # 중복 시작 방지 검증
    success_retry = context.start_meeting("sess_test_456")
    assert success_retry is False
    assert context.current_session_id == "sess_test_123"
    
    # 종료 시그널 모니터링
    ended_session = None
    def on_ended(sess_id):
        nonlocal ended_session
        ended_session = sess_id
    context.signals.meeting_ended.connect(on_ended)
    
    # 3. 회의 종료 테스트
    success_end = context.end_meeting()
    assert success_end is True
    assert context.is_meeting_active is False
    assert context.current_session_id is None
    assert ended_session == "sess_test_123"

def test_context_thread_safety(q_app):
    """다중 스레드에서 동시에 발화를 추가할 때 Race Condition 없이 안정적으로 누적되는지 검증"""
    context = MeetingContext()
    context.reset()
    context.start_meeting("thread_safety_session")
    
    num_threads = 8
    loops_per_thread = 50
    
    signal_count = 0
    def on_transcript(item):
        nonlocal signal_count
        signal_count += 1
    context.signals.transcript_updated.connect(on_transcript)
    
    def worker(thread_idx):
        for i in range(loops_per_thread):
            context.add_transcript(
                speaker=f"User_{thread_idx}",
                text=f"Message {i} from thread {thread_idx}",
                timestamp=time.time()
            )
            
    threads = []
    for t in range(num_threads):
        thread = threading.Thread(target=worker, args=(t,))
        threads.append(thread)
        thread.start()
        
    for thread in threads:
        thread.join()
        
    # 1. 누적 데이터 개수 일치 확인
    transcripts = context.transcripts
    expected_total = num_threads * loops_per_thread
    assert len(transcripts) == expected_total
    
    # 2. Qt 이벤트 루프 전파 확인
    q_app.processEvents()
    assert signal_count == expected_total
    
    context.end_meeting()

def test_context_db_integration(q_app, tmp_path):
    """MeetingContext가 DB 매니저와 올바르게 상호작용하여 데이터를 영구 저장하는지 검증"""
    db_file = tmp_path / "test_integration.db"
    db_manager = DatabaseManager(str(db_file))
    
    context = MeetingContext()
    # DB 매니저 교체
    context.db_manager = db_manager
    context.reset()  # 초기화
    
    # 1. 회의 시작
    session_id = "sess_integration_999"
    assert context.start_meeting(session_id, title="통합 테스트 회의") is True
    
    # DB에 세션이 생성되었는지 확인
    sess_data = db_manager.get_session(session_id)
    assert sess_data is not None
    assert sess_data["title"] == "통합 테스트 회의"
    assert sess_data["end_time"] is None
    
    # 2. 발화 추가
    context.add_transcript(speaker="User_A", text="첫 번째 테스트 발화", start_time=1.0, end_time=2.5)
    context.add_transcript(speaker="User_B", text="두 번째 테스트 발화", start_time=3.0, end_time=4.5)
    
    # DB에 발화가 저장되었는지 확인
    transcripts = db_manager.get_transcripts(session_id)
    assert len(transcripts) == 2
    assert transcripts[0]["speaker"] == "User_A"
    assert transcripts[0]["text"] == "첫 번째 테스트 발화"
    assert transcripts[0]["start_time"] == 1.0
    assert transcripts[0]["end_time"] == 2.5
    
    assert transcripts[1]["speaker"] == "User_B"
    assert transcripts[1]["text"] == "두 번째 테스트 발화"
    assert transcripts[1]["start_time"] == 3.0
    assert transcripts[1]["end_time"] == 4.5
    
    # 3. 회의 종료
    assert context.end_meeting() is True
    
    # DB에 종료 일시가 업데이트되었는지 확인
    sess_data_end = db_manager.get_session(session_id)
    assert sess_data_end["end_time"] is not None

