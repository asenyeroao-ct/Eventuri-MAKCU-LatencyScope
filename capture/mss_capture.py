"""
MSS 擷取模組
提供屏幕截圖功能，支持範圍裁剪和偏移設置
"""

import mss
import numpy as np
import cv2
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class MSSCapture:
    """MSS 屏幕擷取類"""
    
    def __init__(self, config=None):
        """
        初始化 MSS 擷取
        
        Args:
            config: 配置對象，需要包含以下屬性：
                - screen_width: 屏幕寬度（默認自動檢測）
                - screen_height: 屏幕高度（默認自動檢測）
                - mss_range_x: X 軸範圍（0 = 全屏）
                - mss_range_y: Y 軸範圍（0 = 全屏）
                - mss_offset_x: X 軸偏移（相對於屏幕中心）
                - mss_offset_y: Y 軸偏移（相對於屏幕中心）
                - mss_trigger_offset_x: X 軸觸發中心點偏移
                - mss_trigger_offset_y: Y 軸觸發中心點偏移
        """
        try:
            self.mss_monitor = mss.mss()
        except Exception as e:
            logger.error(f"初始化 MSS 失敗: {e}")
            raise
        
        # 獲取主顯示器信息
        monitor = self.mss_monitor.monitors[1]  # 0是全部，1是主顯示器
        self.screen_width = monitor['width']
        self.screen_height = monitor['height']
        
        # 從 config 獲取設置（如果提供）
        if config:
            # 只有在 config 中明確設置且大於 0 時才使用，否則使用自動檢測的值
            config_screen_w = int(getattr(config, "screen_width", 0))
            config_screen_h = int(getattr(config, "screen_height", 0))
            if config_screen_w > 0:
                self.screen_width = config_screen_w
            if config_screen_h > 0:
                self.screen_height = config_screen_h
            
            self.range_x = int(getattr(config, "mss_range_x", 0))
            self.range_y = int(getattr(config, "mss_range_y", 0))
            self.offset_x = int(getattr(config, "mss_offset_x", 0))
            self.offset_y = int(getattr(config, "mss_offset_y", 0))
            self.trigger_offset_x = int(getattr(config, "mss_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(config, "mss_trigger_offset_y", 0))
        else:
            self.range_x = 0
            self.range_y = 0
            self.offset_x = 0
            self.offset_y = 0
            self.trigger_offset_x = 0
            self.trigger_offset_y = 0
        
        # 確保屏幕分辨率有效
        if self.screen_width <= 0 or self.screen_height <= 0:
            logger.error(f"無效的屏幕分辨率: {self.screen_width}x{self.screen_height}，使用默認值 1920x1080")
            self.screen_width = 1920
            self.screen_height = 1080
        
        self.config = config  # 保存 config 引用以便動態讀取
        self.running = True
        
        logger.info(f"MSS 初始化完成: {self.screen_width}x{self.screen_height}")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        獲取最新的屏幕截圖
        
        Returns:
            numpy.ndarray or None: 截圖幀（BGR 格式）
        """
        if not self.running:
            return None
        
        # 如果 mss_monitor 不存在，重新創建（線程安全）
        if not self.mss_monitor:
            try:
                self.mss_monitor = mss.mss()
            except Exception as e:
                logger.error(f"重新創建 MSS monitor 失敗: {e}")
                return None
        
        try:
            # 優化：減少配置讀取頻率（每 100 次調用讀取一次，約 1-2 秒一次）
            if not hasattr(self, '_config_read_counter'):
                self._config_read_counter = 0
            self._config_read_counter += 1
            
            # 動態讀取配置（允許實時更新，但降低頻率以提升性能）
            if self.config and (self._config_read_counter % 100 == 0):
                self.range_x = int(getattr(self.config, "mss_range_x", 0))
                self.range_y = int(getattr(self.config, "mss_range_y", 0))
                self.offset_x = int(getattr(self.config, "mss_offset_x", 0))
                self.offset_y = int(getattr(self.config, "mss_offset_y", 0))
                
                # 更新屏幕分辨率（如果配置中有且有效）
                config_screen_w = int(getattr(self.config, "screen_width", 0))
                config_screen_h = int(getattr(self.config, "screen_height", 0))
                if config_screen_w > 0:
                    self.screen_width = config_screen_w
                if config_screen_h > 0:
                    self.screen_height = config_screen_h
            
            # 確保屏幕分辨率有效
            if self.screen_width <= 0 or self.screen_height <= 0:
                logger.warning(f"屏幕分辨率無效: {self.screen_width}x{self.screen_height}，嘗試重新檢測")
                try:
                    monitor = self.mss_monitor.monitors[1]
                    self.screen_width = monitor['width']
                    self.screen_height = monitor['height']
                except:
                    logger.error("無法重新檢測屏幕分辨率，使用默認值 1920x1080")
                    self.screen_width = 1920
                    self.screen_height = 1080
            
            # 計算擷取區域（範圍至少為 1x1）
            capture_width = max(1, self.range_x) if self.range_x > 0 else self.screen_width
            capture_height = max(1, self.range_y) if self.range_y > 0 else self.screen_height
            
            # 計算中心點並應用偏移
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2
            
            # 計算左上角座標（基於中心點偏移）
            left = center_x - capture_width // 2 + self.offset_x
            top = center_y - capture_height // 2 + self.offset_y
            
            # 確保區域在屏幕範圍內
            left = max(0, min(left, self.screen_width - 1))
            top = max(0, min(top, self.screen_height - 1))
            right = min(left + capture_width, self.screen_width)
            bottom = min(top + capture_height, self.screen_height)
            
            # 調整實際擷取尺寸
            actual_width = right - left
            actual_height = bottom - top
            
            if actual_width <= 0 or actual_height <= 0:
                logger.warning(f"無效的擷取區域: {left}, {top}, {right}, {bottom}")
                return None
            
            # 擷取屏幕區域
            monitor = {
                "top": top,
                "left": left,
                "width": actual_width,
                "height": actual_height
            }
            
            # 確保在當前線程中使用 MSS（MSS 使用線程本地存儲）
            try:
                screenshot = self.mss_monitor.grab(monitor)
                frame = np.array(screenshot)
            except AttributeError as e:
                # 如果遇到線程本地存儲錯誤，重新創建 MSS 對象
                if "'_thread._local' object has no attribute" in str(e):
                    logger.warning("MSS 線程本地存儲錯誤，重新創建 monitor")
                    try:
                        self.mss_monitor = mss.mss()
                        screenshot = self.mss_monitor.grab(monitor)
                        frame = np.array(screenshot)
                    except Exception as e2:
                        logger.error(f"重新創建 MSS monitor 後仍失敗: {e2}")
                        return None
                else:
                    raise
            
            # MSS 返回 BGRA，轉換為 BGR
            if frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            elif frame.shape[2] == 3:
                # 已經是 BGR
                pass
            else:
                logger.warning(f"意外的幀格式: {frame.shape}")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"MSS 擷取錯誤: {e}")
            return None
    
    def get_trigger_center(self) -> Tuple[int, int]:
        """
        獲取觸發中心點座標（相對於擷取區域）
        
        Returns:
            Tuple[int, int]: (x, y) 觸發中心點座標
        """
        # 動態讀取配置
        if self.config:
            self.range_x = int(getattr(self.config, "mss_range_x", 0))
            self.range_y = int(getattr(self.config, "mss_range_y", 0))
            self.trigger_offset_x = int(getattr(self.config, "mss_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(self.config, "mss_trigger_offset_y", 0))
        
        # 計算擷取區域大小
        if self.range_x <= 0:
            capture_width = self.screen_width
        else:
            capture_width = self.range_x
        
        if self.range_y <= 0:
            capture_height = self.screen_height
        else:
            capture_height = self.range_y
        
        # 觸發中心點在擷取區域的中心，加上偏移
        center_x = capture_width // 2 + self.trigger_offset_x
        center_y = capture_height // 2 + self.trigger_offset_y
        
        return (center_x, center_y)
    
    def stop(self):
        """停止擷取"""
        self.running = False
        
        # 等待一小段時間讓線程完成當前操作
        import time
        time.sleep(0.1)
        
        if self.mss_monitor:
            try:
                # MSS 對象使用線程本地存儲，需要正確清理
                # 刪除引用，讓垃圾回收器處理
                del self.mss_monitor
            except Exception as e:
                logger.warning(f"清理 MSS monitor 時出錯: {e}")
            finally:
                self.mss_monitor = None
        
        # 強制垃圾回收
        import gc
        gc.collect()
        
        logger.info("MSS 已停止")


def create_mss_capture(config=None) -> MSSCapture:
    """
    創建 MSS 擷取實例的工廠函數
    
    Args:
        config: 配置對象
    
    Returns:
        MSSCapture: MSS 擷取實例
    """
    return MSSCapture(config)

