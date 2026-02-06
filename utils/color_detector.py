"""
顏色檢測模組
負責檢測畫面中心顏色並判斷是否觸發
"""

import numpy as np
import logging
from typing import Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ColorDetector(QObject):
    """顏色檢測器"""
    color_changed = pyqtSignal(str)  # 發送顏色變化信號
    
    def __init__(self):
        super().__init__()
        self.last_color_state = None
        self.enabled = False
        
        # 模式 1: 顏色變化檢測 (紅色 -> 綠色)
        self.mode = 1
        self.color_from = np.array([206, 38, 54], dtype=np.uint8)  # 紅色 RGB
        self.color_to = np.array([75, 219, 106], dtype=np.uint8)    # 綠色 RGB
        
        # 模式 2: 單一顏色檢測
        self.target_color = np.array([206, 38, 54], dtype=np.uint8)
        
        # 顏色容差
        self.tolerance = 30
        
        # 檢測區域 (畫面中心的像素數)
        self.detection_size = 10
    
    def set_mode(self, mode: int):
        """設置檢測模式"""
        self.mode = mode
        self.last_color_state = None
        logger.info(f"Detection mode set to: {mode}")
    
    def set_color_from(self, r: int, g: int, b: int):
        """設置起始顏色 (RGB)"""
        self.color_from = np.array([r, g, b], dtype=np.uint8)
        logger.debug(f"Color from set to: RGB({r}, {g}, {b})")
    
    def set_color_to(self, r: int, g: int, b: int):
        """設置目標顏色 (RGB)"""
        self.color_to = np.array([r, g, b], dtype=np.uint8)
        logger.debug(f"Color to set to: RGB({r}, {g}, {b})")
    
    def set_target_color(self, r: int, g: int, b: int):
        """設置模式2的目標顏色 (RGB)"""
        self.target_color = np.array([r, g, b], dtype=np.uint8)
        logger.debug(f"Target color set to: RGB({r}, {g}, {b})")
    
    def set_tolerance(self, tolerance: int):
        """設置顏色容差"""
        self.tolerance = tolerance
        logger.debug(f"Tolerance set to: {tolerance}")
    
    def color_matches(self, pixel_bgr, target_rgb, tolerance):
        """檢查像素顏色是否匹配目標顏色（優化版本）"""
        # OpenCV 使用 BGR，直接索引轉換而非創建新數組
        pixel_rgb = pixel_bgr[[2, 1, 0]]
        # 使用 numpy 的向量化運算，避免不必要的類型轉換
        return np.all(np.abs(pixel_rgb.astype(np.int16) - target_rgb.astype(np.int16)) <= tolerance)
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, bool]:
        """
        檢測畫面中心顏色
        
        Args:
            frame: 輸入畫面
            
        Returns:
            (triggered: bool, color_present: bool) - 是否觸發，目標顏色是否存在
        """
        if frame is None or not self.enabled:
            return False, False
        
        h, w = frame.shape[:2]
        center_y, center_x = h // 2, w // 2
        
        # 取得中心區域的平均顏色
        half_size = self.detection_size // 2
        y1 = max(0, center_y - half_size)
        y2 = min(h, center_y + half_size)
        x1 = max(0, center_x - half_size)
        x2 = min(w, center_x + half_size)
        
        center_region = frame[y1:y2, x1:x2]
        avg_color = np.mean(center_region, axis=(0, 1)).astype(np.uint8)
        
        if self.mode == 1:
            # 模式 1: 檢測顏色從紅色變為綠色
            is_from_color = self.color_matches(avg_color, self.color_from, self.tolerance)
            is_to_color = self.color_matches(avg_color, self.color_to, self.tolerance)
            
            current_state = None
            if is_from_color:
                current_state = "from"
            elif is_to_color:
                current_state = "to"
            
            # 檢測狀態變化
            if self.last_color_state == "from" and current_state == "to":
                self.last_color_state = current_state
                self.color_changed.emit(f"顏色變化: 紅色 -> 綠色")
                return True, is_to_color
            
            self.last_color_state = current_state
            return False, is_to_color
            
        elif self.mode == 2:
            # 模式 2: 檢測到特定顏色就觸發（支援冷卻後重複）
            if self.color_matches(avg_color, self.target_color, self.tolerance):
                rgb = (avg_color[2], avg_color[1], avg_color[0])
                self.color_changed.emit(f"檢測到顏色: RGB{rgb}")
                return True, True
            return False, False
        
        return False, False
    
    def reset(self):
        """重置檢測狀態"""
        self.last_color_state = None
        self.enabled = False
        logger.debug("Detector reset")

