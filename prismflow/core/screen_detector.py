import time
import logging
import numpy as np
from typing import Optional, Tuple, Union
from PIL import ImageGrab, Image

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)

# win32com은 Windows 환경에서만 임포트 가능하므로 예외 처리
try:
    import win32com.client
    import pythoncom
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

class ScreenTransitionDetector(QObject):
    """화면 변화를 감지하고 30초 정착(Debounce)된 전환 이벤트를 방출하는 감지기 클래스.
    
    PowerPoint COM API를 우선 활용하며, PPT가 없거나 비활성 상태일 경우
    PIL.ImageGrab을 사용해 32x32 초경량 픽셀 변화율(MSE) 기반 범용 감지로 Fallback합니다.
    """
    # 신호 정의: transition_type ("PPT" 또는 "GENERIC"), info (상세 정보 튜플 또는 배열)
    transition_detected = Signal(str, object)
    
    def __init__(self, debounce_sec: float = 30.0, check_interval_ms: int = 1000):
        super().__init__()
        self.debounce_sec = debounce_sec
        self.check_interval_ms = check_interval_ms
        
        # 주기적 화면 체크 타이머
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_screen)
        
        # 디바운스 정착 타이머
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._confirm_transition)
        
        # 이전 감지용 변수 (1초 주기 RAW 데이터 비교용)
        self.last_raw_ppt_info: Optional[Tuple[str, int]] = None
        self.last_raw_generic_frame: Optional[np.ndarray] = None
        
        # 정착 완료(Settled)된 변수 (30초 정착 완료된 데이터 중복 방지용)
        self.last_settled_info: Optional[Union[Tuple[str, int], np.ndarray]] = None
        
        # 디바운스 대기 중인 변수
        self.pending_type: Optional[str] = None
        self.pending_info: Optional[Union[Tuple[str, int], np.ndarray]] = None
        
        # COM 초기화 여부 체크용 (멀티스레드 대비)
        self._com_initialized = False

    def start(self):
        """감지 타이머를 시작합니다."""
        logger.info("Starting ScreenTransitionDetector...")
        self.check_timer.start(self.check_interval_ms)

    def stop(self):
        """모든 타이머를 중지합니다."""
        logger.info("Stopping ScreenTransitionDetector...")
        self.check_timer.stop()
        self.debounce_timer.stop()

    def _init_com(self):
        """Windows COM 라이브러리를 스레드 수준에서 초기화합니다."""
        if HAS_WIN32COM and not self._com_initialized:
            try:
                pythoncom.CoInitialize()
                self._com_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize CoInitialize: {str(e)}")

    def _get_active_ppt_info(self) -> Optional[Tuple[str, int]]:
        """현재 실행 중인 PowerPoint의 활성 슬라이드 정보를 가져옵니다.
        
        Returns:
            Optional[Tuple[str, int]]: (프레젠테이션 이름, 슬라이드 번호) 또는 None
        """
        if not HAS_WIN32COM:
            return None
            
        self._init_com()
        
        try:
            # PowerPoint 실행 인스턴스 획득 시도
            try:
                ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
            except Exception:
                # PowerPoint가 기동되어 있지 않음
                return None
                
            if not ppt_app or not ppt_app.Presentations.Count > 0:
                return None
                
            active_pres = ppt_app.ActivePresentation
            pres_name = active_pres.Name
            
            slide_index = -1
            # 1. 슬라이드 쇼 모드인지 체크
            if ppt_app.SlideShowWindows.Count > 0:
                # 현재 활성화된 슬라이드 쇼 윈도우의 뷰에서 가져옴
                try:
                    slide_index = ppt_app.SlideShowWindows(1).View.Slide.SlideIndex
                except Exception:
                    pass
            
            # 2. 일반 편집 모드 모니터링 폴백
            if slide_index == -1:
                try:
                    # 편집 모드 활성 윈도우의 현재 슬라이드 index 획득
                    slide_index = ppt_app.ActiveWindow.View.Slide.SlideIndex
                except Exception:
                    pass
                    
            if slide_index != -1:
                return (pres_name, slide_index)
                
        except Exception as e:
            # PPT 닫힘 등으로 인한 COM 오류는 무시하고 Fallback으로 넘김
            logger.debug(f"PowerPoint COM integration exception: {str(e)}")
            
        return None

    def _capture_generic_frame_32x32(self) -> np.ndarray:
        """기본 화면을 캡처하여 32x32 크기의 1채널 GrayScale Numpy 배열로 변환합니다."""
        try:
            # 기본 모니터 영역 스냅샷
            img = ImageGrab.grab()
            # 32x32 축소 및 흑백(L) 변환
            img_resized = img.resize((32, 32)).convert('L')
            return np.array(img_resized, dtype=np.float32)
        except Exception as e:
            logger.error(f"Generic screen capture failed: {str(e)}")
            # 에러 발생 시 더미 배열 반환
            return np.zeros((32, 32), dtype=np.float32)

    def _check_screen(self):
        """1초 주기로 실행되어 화면 변화(RAW) 여부를 검사합니다."""
        # 1. PPT 감지 시도
        ppt_info = self._get_active_ppt_info()
        
        if ppt_info is not None:
            # PPT 모드 작동
            if self.last_raw_ppt_info != ppt_info:
                logger.debug(f"RAW PPT slide change detected: {self.last_raw_ppt_info} -> {ppt_info}")
                self.last_raw_ppt_info = ppt_info
                
                # 디바운싱 트리거
                self.pending_type = "PPT"
                self.pending_info = ppt_info
                # 30초 디바운싱 타이머 시작 (혹은 재시작)
                self.debounce_timer.start(int(self.debounce_sec * 1000))
        else:
            # 2. PPT가 없으면 범용 감지(ImageGrab) 폴백
            self.last_raw_ppt_info = None  # PPT 해제 표시
            
            current_frame = self._capture_generic_frame_32x32()
            if self.last_raw_generic_frame is not None:
                # MSE 계산
                mse = np.mean((current_frame - self.last_raw_generic_frame) ** 2)
                # 픽셀 강도 변화율 임계값 체크
                if mse > 10.0:
                    logger.debug(f"RAW Generic screen change detected (MSE: {mse:.2f})")
                    self.pending_type = "GENERIC"
                    self.pending_info = current_frame
                    # 30초 디바운싱 타이머 시작 (재시작)
                    self.debounce_timer.start(int(self.debounce_sec * 1000))
                    
            self.last_raw_generic_frame = current_frame

    def _confirm_transition(self):
        """디바운스 타이머가 만료되었을 때, 중복 전송 방지 점검 후 이벤트를 확정 및 방출합니다."""
        if self.pending_info is None or self.pending_type is None:
            return
            
        # 중복 전송 방지(Deduplication) 검증
        is_duplicate = False
        
        if self.pending_type == "PPT":
            # PPT의 경우 (파일명, 슬라이드번호) 비교
            if self.last_settled_info == self.pending_info:
                is_duplicate = True
        elif self.pending_type == "GENERIC":
            # 범용 감지의 경우, 이전 확정 32x32 프레임과 현재 32x32 프레임의 MSE 비교
            if self.last_settled_info is not None and isinstance(self.last_settled_info, np.ndarray):
                mse = np.mean((self.pending_info - self.last_settled_info) ** 2)
                # 확정본과 거의 동일하면 중복 처리 (MSE < 1.0)
                if mse < 1.0:
                    is_duplicate = True
                    
        if is_duplicate:
            logger.info(f"Duplicate screen transition skipped for {self.pending_type} information.")
        else:
            logger.info(f"Screen transition confirmed. Type: {self.pending_type}")
            self.last_settled_info = self.pending_info
            
            # 최종 이벤트 방출
            self.transition_detected.emit(self.pending_type, self.pending_info)
            
        # 펜딩 상태 초기화
        self.pending_type = None
        self.pending_info = None

    def __del__(self):
        """소멸 시 COM 리소스를 해제합니다."""
        if HAS_WIN32COM and self._com_initialized:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
