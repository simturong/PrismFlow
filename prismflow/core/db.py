import sqlite3
import os
import threading
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        # db 파일 부모 디렉토리가 없으면 생성
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 생성하고 외래키 및 다중 스레드 동시성 PRAGMA를 적용합니다.

        여러 QThread(STT·Flow·Chat·Report 워커)가 동시에 DB에 접근하므로, WAL 저널 모드로
        읽기/쓰기 동시성을 확보하고 busy_timeout으로 잠금 경합 시 즉시 실패하지 않고 대기하도록
        하여 'database is locked' 및 네이티브 접근 위반(access violation)을 방어합니다.
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        """스키마에 따라 테이블을 생성합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # 1. 회의 세션 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS meeting_sessions (
                            session_id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            start_time TEXT NOT NULL,
                            end_time TEXT,
                            summary TEXT
                        )
                    """)
                    # 2. 발화 데이터 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS transcripts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            speaker TEXT NOT NULL,
                            text TEXT NOT NULL,
                            start_time REAL NOT NULL,
                            end_time REAL NOT NULL,
                            FOREIGN KEY (session_id) REFERENCES meeting_sessions(session_id) ON DELETE CASCADE
                        )
                    """)
                    # 3. 채팅 기록 데이터 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS chat_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            query TEXT NOT NULL,
                            response TEXT NOT NULL,
                            timestamp REAL NOT NULL,
                            FOREIGN KEY (session_id) REFERENCES meeting_sessions(session_id) ON DELETE CASCADE
                        )
                    """)
                    # 4. 애플리케이션 설정 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL
                        )
                    """)
                    # 5. 화면 캡처 로그 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS screen_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            screen_type TEXT NOT NULL,
                            screen_info TEXT NOT NULL,
                            timestamp REAL NOT NULL,
                            FOREIGN KEY (session_id) REFERENCES meeting_sessions(session_id) ON DELETE CASCADE
                        )
                    """)
                    # 5-2. Mermaid 흐름도 히스토리 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS flow_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id TEXT NOT NULL,
                            mermaid_code TEXT NOT NULL,
                            timestamp REAL NOT NULL,
                            FOREIGN KEY (session_id) REFERENCES meeting_sessions(session_id) ON DELETE CASCADE
                        )
                    """)
                    # 5-3. 오인식 교정 사전 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS correction_dictionary (
                            pattern TEXT PRIMARY KEY,
                            replacement TEXT NOT NULL
                        )
                    """)
                    # 5-4. 화자 실제 이름 매핑 캐시 테이블
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS speaker_profiles (
                            speaker_id TEXT PRIMARY KEY,
                            actual_name TEXT NOT NULL
                        )
                    """)

                    # 6. 레거시 스키마 마이그레이션
                    #    CREATE TABLE IF NOT EXISTS는 기존 테이블의 컬럼을 갱신하지 못하므로,
                    #    Phase 2 이전의 구 transcripts 스키마(단일 timestamp 컬럼)가 남아 있으면
                    #    start_time/end_time 분리 스키마로 마이그레이션한다.
                    self._migrate_legacy_transcripts(conn)
            finally:
                conn.close()

    def _migrate_legacy_transcripts(self, conn: sqlite3.Connection):
        """구 transcripts 스키마(timestamp 단일 컬럼)를 start_time/end_time 스키마로 이관합니다.

        기존 데이터는 timestamp 값을 start_time·end_time 양쪽에 매핑하여 보존하며,
        이미 신 스키마이거나 테이블이 없으면 아무 작업도 하지 않습니다 (idempotent).
        """
        cols = [row[1] for row in conn.execute("PRAGMA table_info(transcripts)")]
        if not cols or "start_time" in cols:
            return  # 테이블 없음(신규 생성됨) 또는 이미 신 스키마

        has_timestamp = "timestamp" in cols
        conn.execute("ALTER TABLE transcripts RENAME TO transcripts_legacy")
        conn.execute("""
            CREATE TABLE transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES meeting_sessions(session_id) ON DELETE CASCADE
            )
        """)
        if has_timestamp:
            conn.execute("""
                INSERT INTO transcripts (id, session_id, speaker, text, start_time, end_time)
                SELECT id, session_id, speaker, text, timestamp, timestamp FROM transcripts_legacy
            """)
        conn.execute("DROP TABLE transcripts_legacy")

    def create_session(self, session_id: str, title: str = "새로운 회의", start_time: str = None) -> bool:
        """새 회의 세션을 데이터베이스에 등록합니다."""
        import datetime
        if start_time is None:
            start_time = datetime.datetime.now().isoformat()
        
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # 중복 체크
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM meeting_sessions WHERE session_id = ?", (session_id,))
                    if cur.fetchone():
                        return False
                    
                    conn.execute("""
                        INSERT INTO meeting_sessions (session_id, title, start_time, end_time, summary)
                        VALUES (?, ?, ?, NULL, NULL)
                    """, (session_id, title, start_time))
                return True
            except sqlite3.Error:
                return False
            finally:
                conn.close()

    def end_session(self, session_id: str, end_time: str = None, summary: str = None) -> bool:
        """회의 세션을 종료 처리하고 최종 보고서를 저장합니다."""
        import datetime
        if end_time is None:
            end_time = datetime.datetime.now().isoformat()
            
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM meeting_sessions WHERE session_id = ?", (session_id,))
                    if not cur.fetchone():
                        return False
                    
                    if summary is not None:
                        conn.execute("""
                            UPDATE meeting_sessions
                            SET end_time = ?, summary = ?
                            WHERE session_id = ?
                        """, (end_time, summary, session_id))
                    else:
                        conn.execute("""
                            UPDATE meeting_sessions
                            SET end_time = ?
                            WHERE session_id = ?
                        """, (end_time, session_id))
                return True
            except sqlite3.Error:
                return False
            finally:
                conn.close()

    def get_session(self, session_id: str) -> dict:
        """특정 회의 세션 정보를 가져옵니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM meeting_sessions WHERE session_id = ?", (session_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None
            finally:
                conn.close()

    def add_transcript(self, session_id: str, speaker: str, text: str, start_time: float, end_time: float) -> int:
        """발화 내역을 추가합니다. 성공 시 생성된 transcript의 ID를 반환하며 실패 시 -1을 반환합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO transcripts (session_id, speaker, text, start_time, end_time)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, speaker, text, start_time, end_time))
                    return cur.lastrowid
            except sqlite3.Error:
                return -1
            finally:
                conn.close()

    def get_transcripts(self, session_id: str) -> list:
        """특정 세션의 발화 기록을 순서대로 가져옵니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT speaker, text, start_time, end_time 
                    FROM transcripts 
                    WHERE session_id = ? 
                    ORDER BY id ASC
                """, (session_id,))
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def add_chat_log(self, session_id: str, query: str, response: str, timestamp: float) -> int:
        """채팅 기록을 추가합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO chat_logs (session_id, query, response, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, query, response, timestamp))
                    return cur.lastrowid
            except sqlite3.Error:
                return -1
            finally:
                conn.close()

    def get_chat_logs(self, session_id: str) -> list:
        """특정 세션의 채팅 기록을 시간순으로 가져옵니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT query, response, timestamp 
                    FROM chat_logs 
                    WHERE session_id = ? 
                    ORDER BY id ASC
                """, (session_id,))
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def set_setting(self, key: str, value: str):
        """설정값을 저장하거나 업데이트합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO settings (key, value)
                        VALUES (?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """, (key, value))
            finally:
                conn.close()

    def get_setting(self, key: str, default: str = None) -> str:
        """설정값을 조회합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cur.fetchone()
                if row:
                    return row['value']
                return default
            finally:
                conn.close()

    def add_screen_log(self, session_id: str, screen_type: str, screen_info: str) -> int:
        """화면 맥락 감지 로그를 데이터베이스에 추가합니다."""
        import time
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO screen_logs (session_id, screen_type, screen_info, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, screen_type, screen_info, time.time()))
                    return cur.lastrowid
            except sqlite3.Error:
                return -1
            finally:
                conn.close()

    def get_screen_logs(self, session_id: str) -> list:
        """특정 세션의 화면 맥락 로그를 시간순으로 조회합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT screen_type, screen_info, timestamp 
                    FROM screen_logs 
                    WHERE session_id = ? 
                    ORDER BY id ASC
                """, (session_id,))
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def add_flow_history(self, session_id: str, mermaid_code: str) -> int:
        """새로운 Mermaid 흐름도 스냅샷을 DB에 영구 기록합니다."""
        import time
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO flow_history (session_id, mermaid_code, timestamp)
                        VALUES (?, ?, ?)
                    """, (session_id, mermaid_code, time.time()))
                    return cur.lastrowid
            except sqlite3.Error:
                return -1
            finally:
                conn.close()

    def get_flow_history(self, session_id: str) -> list:
        """특정 세션의 Mermaid 흐름도 히스토리 스냅샷들을 시간순으로 조회합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT mermaid_code, timestamp 
                    FROM flow_history 
                    WHERE session_id = ? 
                    ORDER BY id ASC
                """, (session_id,))
                return [dict(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def add_correction(self, pattern: str, replacement: str) -> None:
        """오인식 교정 사전에 치환 패턴을 등록합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO correction_dictionary (pattern, replacement)
                        VALUES (?, ?)
                    """, (pattern, replacement))
            finally:
                conn.close()

    def get_corrections(self) -> dict:
        """등록된 모든 오인식 교정 패턴 매핑을 사전 형태로 가져옵니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT pattern, replacement FROM correction_dictionary")
                return {row["pattern"]: row["replacement"] for row in cur.fetchall()}
            finally:
                conn.close()

    def delete_correction(self, pattern: str) -> None:
        """교정 사전에서 특정 패턴을 삭제합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM correction_dictionary WHERE pattern = ?", (pattern,))
            finally:
                conn.close()

    def add_speaker_profile(self, speaker_id: str, actual_name: str) -> None:
        """화자 프로필(ID ↔ 실제 이름) 매핑 정보를 등록합니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO speaker_profiles (speaker_id, actual_name)
                        VALUES (?, ?)
                    """, (speaker_id, actual_name))
            finally:
                conn.close()

    def get_speaker_profiles(self) -> dict:
        """등록된 모든 화자 프로필 매핑 정보를 사전 형태로 가져옵니다."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT speaker_id, actual_name FROM speaker_profiles")
                return {row["speaker_id"]: row["actual_name"] for row in cur.fetchall()}
            finally:
                conn.close()
