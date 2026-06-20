import threading
import datetime
from typing import Optional
from PySide6.QtCore import QObject, Signal
from prismflow.core.config import AppConfig
from prismflow.core.db import DatabaseManager

class MeetingSignals(QObject):
    meeting_started = Signal(str)       # session_id
    meeting_ended = Signal(str)         # session_id
    transcript_updated = Signal(dict)   # new transcript item
    flow_updated = Signal(str)          # new mermaid code

class MeetingContext:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MeetingContext, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        
        self._lock = threading.Lock()
        self._signals = MeetingSignals()
        
        # 상태 변수
        self._is_meeting_active = False
        self._current_session_id = None
        self._transcripts = []
        self._current_mermaid_code = ""
        self._last_screen_info = None
        
        # DB 매니저 기본 초기화
        self._config = AppConfig.load_default()
        self._db_manager = DatabaseManager(self._config.db_path)
        
        self._initialized = True

    @property
    def signals(self) -> MeetingSignals:
        return self._signals

    @property
    def is_meeting_active(self) -> bool:
        with self._lock:
            return self._is_meeting_active

    @property
    def current_session_id(self) -> str:
        with self._lock:
            return self._current_session_id

    @property
    def transcripts(self) -> list:
        with self._lock:
            return list(self._transcripts)

    @property
    def current_mermaid_code(self) -> str:
        with self._lock:
            return self._current_mermaid_code

    @property
    def last_screen_info(self) -> Optional[dict]:
        with self._lock:
            return self._last_screen_info

    @property
    def db_manager(self) -> DatabaseManager:
        with self._lock:
            return self._db_manager

    @db_manager.setter
    def db_manager(self, manager: DatabaseManager):
        with self._lock:
            self._db_manager = manager

    def start_meeting(self, session_id: str, title: str = "새로운 회의") -> bool:
        start_time_iso = datetime.datetime.now().isoformat()
        with self._lock:
            if self._is_meeting_active:
                return False
            self._is_meeting_active = True
            self._current_session_id = session_id
            self._transcripts.clear()
            self._current_mermaid_code = ""
            
            # DB 저장
            if self._db_manager:
                self._db_manager.create_session(session_id, title=title, start_time=start_time_iso)
        
        self._signals.meeting_started.emit(session_id)
        return True

    def end_meeting(self) -> bool:
        session_id = None
        end_time_iso = datetime.datetime.now().isoformat()
        with self._lock:
            if not self._is_meeting_active:
                return False
            self._is_meeting_active = False
            session_id = self._current_session_id
            self._current_session_id = None
            
            # DB 저장
            if self._db_manager and session_id:
                self._db_manager.end_session(session_id, end_time=end_time_iso)
        
        if session_id:
            self._signals.meeting_ended.emit(session_id)
        return True

    def add_transcript(self, speaker: str, text: str, start_time: float = None, end_time: float = None, timestamp: float = None) -> None:
        if start_time is None:
            start_time = timestamp if timestamp is not None else 0.0
        if end_time is None:
            end_time = start_time + 1.0
            
        item = {
            "speaker": speaker, 
            "text": text, 
            "start_time": start_time, 
            "end_time": end_time,
            "timestamp": start_time
        }
        with self._lock:
            self._transcripts.append(item)
            if self._db_manager and self._is_meeting_active and self._current_session_id:
                self._db_manager.add_transcript(
                    session_id=self._current_session_id,
                    speaker=speaker,
                    text=text,
                    start_time=start_time,
                    end_time=end_time
                )
        
        self._signals.transcript_updated.emit(item)

    def update_mermaid_code(self, code: str) -> None:
        with self._lock:
            self._current_mermaid_code = code
        
        self._signals.flow_updated.emit(code)

    def update_screen_info(self, screen_type: str, info: object) -> None:
        # DB 저장용 문자열 변환
        info_str = ""
        if screen_type == "PPT" and isinstance(info, (tuple, list)) and len(info) >= 2:
            info_str = f"{info[0]}|{info[1]}"
        elif screen_type == "GENERIC":
            import numpy as np
            if isinstance(info, np.ndarray):
                info_str = ",".join(map(str, info.flatten().tolist()))
            else:
                info_str = str(info)
        else:
            info_str = str(info)
            
        with self._lock:
            self._last_screen_info = {
                "type": screen_type,
                "info": info,
                "timestamp": datetime.datetime.now().isoformat()
            }
            if self._is_meeting_active and self._current_session_id and self._db_manager:
                self._db_manager.add_screen_log(
                    session_id=self._current_session_id,
                    screen_type=screen_type,
                    screen_info=info_str
                )

    def reset(self) -> None:
        """MeetingContext의 모든 내부 상태를 강제 초기화합니다."""
        with self._lock:
            self._is_meeting_active = False
            self._current_session_id = None
            self._transcripts.clear()
            self._current_mermaid_code = ""
            self._last_screen_info = None
