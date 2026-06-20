import os
import pytest
import sqlite3
from prismflow.core.db import DatabaseManager

@pytest.fixture
def db_manager(tmp_path):
    db_file = tmp_path / "test_db.db"
    manager = DatabaseManager(str(db_file))
    return manager

def test_init_db(db_manager):
    # 테이블 존재 여부 확인
    conn = sqlite3.connect(db_manager.db_path)
    cur = conn.cursor()
    
    tables = ["meeting_sessions", "transcripts", "chat_logs", "settings", "screen_logs"]
    for table in tables:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        assert cur.fetchone() is not None, f"Table {table} does not exist"
        
    conn.close()

def test_session_crud(db_manager):
    session_id = "20260620_120000"
    
    # 1. 세션 생성
    success = db_manager.create_session(session_id, title="스탠드업 미팅", start_time="2026-06-20T12:00:00")
    assert success is True
    
    # 2. 중복 생성 실패
    success_duplicate = db_manager.create_session(session_id, title="다른 미팅")
    assert success_duplicate is False
    
    # 3. 세션 조회
    session = db_manager.get_session(session_id)
    assert session is not None
    assert session["session_id"] == session_id
    assert session["title"] == "스탠드업 미팅"
    assert session["start_time"] == "2026-06-20T12:00:00"
    assert session["end_time"] is None
    assert session["summary"] is None
    
    # 4. 세션 종료
    end_success = db_manager.end_session(session_id, end_time="2026-06-20T12:30:00", summary="오늘의 회의 요약")
    assert end_success is True
    
    # 5. 종료 후 조회
    session_updated = db_manager.get_session(session_id)
    assert session_updated["end_time"] == "2026-06-20T12:30:00"
    assert session_updated["summary"] == "오늘의 회의 요약"
    
    # 존재하지 않는 세션 종료 실패
    assert db_manager.end_session("invalid_session_id") is False

def test_legacy_transcripts_migration(tmp_path):
    """Phase 2 이전 구 스키마(단일 timestamp 컬럼)를 start_time/end_time로 자동 마이그레이션한다."""
    db_file = tmp_path / "legacy.db"

    # 1. 구 스키마 DB를 수동으로 생성하고 더미 발화 1건 적재
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE meeting_sessions (
            session_id TEXT PRIMARY KEY, title TEXT NOT NULL,
            start_time TEXT NOT NULL, end_time TEXT, summary TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
            speaker TEXT NOT NULL, text TEXT NOT NULL, timestamp REAL NOT NULL
        )
    """)
    conn.execute("INSERT INTO meeting_sessions (session_id, title, start_time) VALUES ('s1','구회의','2026-06-20T12:00:00')")
    conn.execute("INSERT INTO transcripts (session_id, speaker, text, timestamp) VALUES ('s1','Speaker_00','레거시 발화', 3.5)")
    conn.commit()
    conn.close()

    # 2. DatabaseManager 초기화 시점에 자동 마이그레이션 발생
    mgr = DatabaseManager(str(db_file))

    # 3. 스키마가 신 스키마로 전환되었는지 확인
    conn = sqlite3.connect(str(db_file))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(transcripts)")]
    assert "start_time" in cols and "end_time" in cols
    assert "timestamp" not in cols
    # 4. 기존 데이터 보존: timestamp 값이 start_time/end_time 양쪽에 매핑
    row = conn.execute("SELECT speaker, text, start_time, end_time FROM transcripts").fetchone()
    assert row == ("Speaker_00", "레거시 발화", 3.5, 3.5)
    conn.close()

    # 5. 마이그레이션 후 신 스키마 기준 CRUD 정상 동작
    assert mgr.add_transcript("s1", "Speaker_01", "신규 발화", 5.0, 9.0) > 0
    assert len(mgr.get_transcripts("s1")) == 2

def test_transcripts_crud(db_manager):
    session_id = "20260620_120000"
    db_manager.create_session(session_id, title="테스트 미팅")
    
    # 1. 발화 등록
    t1_id = db_manager.add_transcript(session_id, speaker="Speaker_00", text="안녕하세요.", start_time=1.2, end_time=2.5)
    assert t1_id != -1
    
    t2_id = db_manager.add_transcript(session_id, speaker="Speaker_01", text="반갑습니다.", start_time=3.0, end_time=4.8)
    assert t2_id != -1
    
    # 2. 발화 조회
    transcripts = db_manager.get_transcripts(session_id)
    assert len(transcripts) == 2
    
    assert transcripts[0]["speaker"] == "Speaker_00"
    assert transcripts[0]["text"] == "안녕하세요."
    assert transcripts[0]["start_time"] == 1.2
    assert transcripts[0]["end_time"] == 2.5
    
    assert transcripts[1]["speaker"] == "Speaker_01"
    assert transcripts[1]["text"] == "반갑습니다."
    
    # 3. 존재하지 않는 세션에 발화 추가 실패 (외래키 제약조건)
    fail_id = db_manager.add_transcript("non_existent_session", speaker="Speaker_00", text="실패해야 함", start_time=0.0, end_time=1.0)
    assert fail_id == -1

def test_chat_logs_crud(db_manager):
    session_id = "20260620_120000"
    db_manager.create_session(session_id, title="테스트 미팅")
    
    # 1. 채팅 기록 등록
    log_id = db_manager.add_chat_log(session_id, query="오늘 주요 의제는?", response="STT 엔진 설계입니다.", timestamp=1718888888.0)
    assert log_id != -1
    
    # 2. 채팅 기록 조회
    logs = db_manager.get_chat_logs(session_id)
    assert len(logs) == 1
    assert logs[0]["query"] == "오늘 주요 의제는?"
    assert logs[0]["response"] == "STT 엔진 설계입니다."
    assert logs[0]["timestamp"] == 1718888888.0
    
    # 3. 외래키 제약조건 검증
    fail_log_id = db_manager.add_chat_log("non_existent_session", query="질문", response="답변", timestamp=1718888888.0)
    assert fail_log_id == -1

def test_settings_crud(db_manager):
    # 1. 없는 설정 조회 기본값 반환
    val = db_manager.get_setting("non_existent_key", default="default_val")
    assert val == "default_val"
    
    # 2. 설정 저장
    db_manager.set_setting("whisper_model_size", "base")
    assert db_manager.get_setting("whisper_model_size") == "base"
    
    # 3. 설정 업데이트 (중복 키)
    db_manager.set_setting("whisper_model_size", "medium")
    assert db_manager.get_setting("whisper_model_size") == "medium"

def test_screen_logs_crud(db_manager):
    session_id = "20260620_120000"
    db_manager.create_session(session_id, title="테스트 미팅")
    
    # 1. 화면 로그 추가
    log_id = db_manager.add_screen_log(session_id, screen_type="PPT", screen_info="sales.pptx|3")
    assert log_id != -1
    
    # 2. 화면 로그 조회
    logs = db_manager.get_screen_logs(session_id)
    assert len(logs) == 1
    assert logs[0]["screen_type"] == "PPT"
    assert logs[0]["screen_info"] == "sales.pptx|3"
    assert isinstance(logs[0]["timestamp"], float)
    
    # 3. 외래키 제약조건 검증
    fail_id = db_manager.add_screen_log("non_existent_session", screen_type="GENERIC", screen_info="1,2,3")
    assert fail_id == -1
