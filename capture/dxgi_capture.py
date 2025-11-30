"""
DXGI 擷取模組
提供基於 DirectX Graphics Infrastructure 的高性能屏幕擷取功能
支持範圍裁剪和偏移設置
"""

try:
    import dxcam
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False

import numpy as np
import cv2
import logging
import ctypes
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DXGICapture:
    """DXGI 屏幕擷取類（使用 dxcam）"""
    
    def __init__(self, config=None, output_idx=0, target_fps=0):
        """
        初始化 DXGI 擷取
        
        Args:
            config: 配置對象，需要包含以下屬性：
                - screen_width: 屏幕寬度（默認自動檢測）
                - screen_height: 屏幕高度（默認自動檢測）
                - dxgi_range_x: X 軸範圍（0 = 全屏）
                - dxgi_range_y: Y 軸範圍（0 = 全屏）
                - dxgi_offset_x: X 軸偏移（相對於屏幕中心）
                - dxgi_offset_y: Y 軸偏移（相對於屏幕中心）
                - dxgi_trigger_offset_x: X 軸觸發中心點偏移
                - dxgi_trigger_offset_y: Y 軸觸發中心點偏移
                - dxgi_target_fps: 目標 FPS（0 = 無限制）
            output_idx: 輸出索引（默認 0，主顯示器）
            target_fps: 目標 FPS（0 = 無限制，默認 0）
        """
        if not DXCAM_AVAILABLE:
            raise ImportError("dxcam 未安裝，請先安裝: pip install dxcam")
        
        self.output_idx = output_idx
        self.target_fps = target_fps
        self.camera = None
        self.running = False
        
        # 從 config 獲取設置（如果提供）
        if config:
            self.screen_width = int(getattr(config, "screen_width", 1920))
            self.screen_height = int(getattr(config, "screen_height", 1080))
            self.range_x = int(getattr(config, "dxgi_range_x", 0))
            self.range_y = int(getattr(config, "dxgi_range_y", 0))
            self.offset_x = int(getattr(config, "dxgi_offset_x", 0))
            self.offset_y = int(getattr(config, "dxgi_offset_y", 0))
            self.trigger_offset_x = int(getattr(config, "dxgi_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(config, "dxgi_trigger_offset_y", 0))
            
            # 讀取目標 FPS（如果配置中有）
            config_fps = int(getattr(config, "dxgi_target_fps", 0))
            if config_fps > 0:
                self.target_fps = config_fps
        else:
            self.range_x = 0
            self.range_y = 0
            self.offset_x = 0
            self.offset_y = 0
            self.trigger_offset_x = 0
            self.trigger_offset_y = 0
        
        self.config = config  # 保存 config 引用以便動態讀取
        
        # 獲取屏幕分辨率
        try:
            # 嘗試使用 Windows API 獲取屏幕分辨率
            user32 = ctypes.windll.user32
            self.screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            self.screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            logger.info(f"使用 Windows API 檢測到屏幕分辨率: {self.screen_width}x{self.screen_height}")
        except:
            logger.warning("無法獲取屏幕分辨率，使用默認值 1920x1080")
            if not config or not hasattr(config, "screen_width") or getattr(config, "screen_width", 0) == 0:
                self.screen_width = 1920
                self.screen_height = 1080
        
        # 如果 config 中有有效的屏幕分辨率，使用它
        if config:
            config_screen_w = int(getattr(config, "screen_width", 0))
            config_screen_h = int(getattr(config, "screen_height", 0))
            if config_screen_w > 0:
                self.screen_width = config_screen_w
            if config_screen_h > 0:
                self.screen_height = config_screen_h
        
        logger.info(f"DXGI 初始化完成: {self.screen_width}x{self.screen_height}")
    
    def start(self):
        """啟動擷取"""
        if self.camera is not None:
            logger.warning("DXGI 實例已存在，先停止舊實例")
            self.stop()
        
        try:
            # 動態讀取配置（允許實時更新）
            if self.config:
                self.range_x = int(getattr(self.config, "dxgi_range_x", 0))
                self.range_y = int(getattr(self.config, "dxgi_range_y", 0))
                self.offset_x = int(getattr(self.config, "dxgi_offset_x", 0))
                self.offset_y = int(getattr(self.config, "dxgi_offset_y", 0))
                
                # 讀取目標 FPS（如果配置中有）
                config_fps = int(getattr(self.config, "dxgi_target_fps", 0))
                if config_fps > 0:
                    self.target_fps = config_fps
                
                # 更新屏幕分辨率（如果配置中有且有效）
                config_screen_w = int(getattr(self.config, "screen_width", 0))
                config_screen_h = int(getattr(self.config, "screen_height", 0))
                if config_screen_w > 0:
                    self.screen_width = config_screen_w
                if config_screen_h > 0:
                    self.screen_height = config_screen_h
            
            # 計算擷取區域
            left, top, right, bottom = self._calculate_region()
            
            # 創建 dxcam 實例（dxcam 使用 region 參數在創建時指定區域）
            # 增加緩衝區大小以支持高 FPS（默認 64，增加到 128）
            self.camera = dxcam.create(
                output_idx=self.output_idx, 
                output_color="BGR", 
                region=(left, top, right, bottom),
                max_buffer_len=128  # 增加緩衝區以支持高 FPS
            )
            
            # 啟動擷取（設置目標 FPS，0 表示無限制，使用高值如 300 來實現無限制）
            if self.target_fps > 0:
                self.camera.start(target_fps=self.target_fps)
                logger.info(f"DXGI 已啟動，區域: ({left}, {top}, {right}, {bottom}), 目標 FPS: {self.target_fps}")
            else:
                # dxcam 的 start() 默認 target_fps=60，所以我們需要傳遞一個高值來實現無限制
                self.camera.start(target_fps=300)
                logger.info(f"DXGI 已啟動，區域: ({left}, {top}, {right}, {bottom}), FPS: 無限制 (300)")
            
            self.running = True
            return True
            
        except Exception as e:
            logger.error(f"啟動 DXGI 失敗: {e}")
            self.camera = None
            self.running = False
            return False
    
    def _calculate_region(self) -> Tuple[int, int, int, int]:
        """計算擷取區域"""
        # 計算擷取區域大小（範圍至少為 1x1）
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
        
        return (left, top, right, bottom)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        獲取最新的屏幕截圖
        
        Returns:
            numpy.ndarray or None: 截圖幀（BGR 格式）
        """
        if not self.camera or not self.running:
            return None
        
        try:
            # 優化：減少配置讀取頻率（每 100 次調用讀取一次，約 1-2 秒一次）
            if not hasattr(self, '_config_read_counter'):
                self._config_read_counter = 0
            self._config_read_counter += 1
            
            # 動態讀取配置（允許實時更新，但降低頻率以提升性能）
            if self.config and (self._config_read_counter % 100 == 0):
                self.range_x = int(getattr(self.config, "dxgi_range_x", 0))
                self.range_y = int(getattr(self.config, "dxgi_range_y", 0))
                self.offset_x = int(getattr(self.config, "dxgi_offset_x", 0))
                self.offset_y = int(getattr(self.config, "dxgi_offset_y", 0))
                
                # 讀取目標 FPS（如果配置中有）
                config_fps = int(getattr(self.config, "dxgi_target_fps", 0))
                if config_fps > 0:
                    self.target_fps = config_fps
                
                # 更新屏幕分辨率（如果配置中有且有效）
                config_screen_w = int(getattr(self.config, "screen_width", 0))
                config_screen_h = int(getattr(self.config, "screen_height", 0))
                if config_screen_w > 0:
                    self.screen_width = config_screen_w
                if config_screen_h > 0:
                    self.screen_height = config_screen_h
            
            # dxcam 的 get_latest_frame() 會阻塞等待新幀
            # 這是正常的，因為它會等待內部擷取線程產生新幀
            frame = self.camera.get_latest_frame()
            
            if frame is None or frame.size == 0:
                return None
            
            # dxcam 返回 BGR 格式（因為我們設置了 output_color="BGR"）
            return frame
            
        except Exception as e:
            logger.error(f"DXGI 擷取錯誤: {e}")
            return None
    
    def get_trigger_center(self) -> Tuple[int, int]:
        """
        獲取觸發中心點座標（相對於擷取區域）
        
        Returns:
            Tuple[int, int]: (x, y) 觸發中心點座標
        """
        # 動態讀取配置
        if self.config:
            self.range_x = int(getattr(self.config, "dxgi_range_x", 0))
            self.range_y = int(getattr(self.config, "dxgi_range_y", 0))
            self.trigger_offset_x = int(getattr(self.config, "dxgi_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(self.config, "dxgi_trigger_offset_y", 0))
        
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
        
        if self.camera:
            try:
                self.camera.stop()
            except Exception as e:
                logger.warning(f"停止 DXGI 時出錯: {e}")
            finally:
                self.camera = None
        
        # 強制垃圾回收
        import gc
        gc.collect()
        
        logger.info("DXGI 已停止")
    
    def restart(self):
        """重新啟動擷取（用於更新設置）"""
        self.stop()
        return self.start()


def create_dxgi_capture(config=None, output_idx=0, target_fps=0) -> DXGICapture:
    """
    創建 DXGI 擷取實例的工廠函數
    
    Args:
        config: 配置對象
        output_idx: 輸出索引
        target_fps: 目標 FPS（0 = 無限制）
    
    Returns:
        DXGICapture 實例
    """
    return DXGICapture(config, output_idx, target_fps)

