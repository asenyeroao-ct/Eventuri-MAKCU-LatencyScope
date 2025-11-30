"""
BetterCam 擷取模組
提供高性能屏幕擷取功能，支持範圍裁剪和偏移設置
"""

import bettercam
import numpy as np
import cv2
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class BetterCamCapture:
    """BetterCam 屏幕擷取類"""
    
    def __init__(self, config=None, device_idx=0, output_idx=0, use_gpu=False, target_fps=0):
        """
        初始化 BetterCam 擷取
        
        Args:
            config: 配置對象，需要包含以下屬性：
                - screen_width: 屏幕寬度（默認自動檢測）
                - screen_height: 屏幕高度（默認自動檢測）
                - bettercam_range_x: X 軸範圍（0 = 全屏）
                - bettercam_range_y: Y 軸範圍（0 = 全屏）
                - bettercam_offset_x: X 軸偏移（相對於屏幕中心）
                - bettercam_offset_y: Y 軸偏移（相對於屏幕中心）
                - bettercam_trigger_offset_x: X 軸觸發中心點偏移
                - bettercam_trigger_offset_y: Y 軸觸發中心點偏移
                - bettercam_target_fps: 目標 FPS（0 = 無限制）
            device_idx: GPU 設備索引（默認 0）
            output_idx: 輸出索引（默認 0，主顯示器）
            use_gpu: 是否使用 GPU（默認 False）
            target_fps: 目標 FPS（0 = 無限制，默認 0）
        """
        self.target_fps = target_fps
        self.device_idx = device_idx
        self.output_idx = output_idx
        self.use_gpu = use_gpu
        self.target_fps = target_fps
        self.camera = None
        self.running = False
        self._gpu_bgra_mode = False  # GPU 模式是否使用 BGRA（需要手動轉換）
        
        # 從 config 獲取設置（如果提供）
        if config:
            self.screen_width = int(getattr(config, "screen_width", 1920))
            self.screen_height = int(getattr(config, "screen_height", 1080))
            self.range_x = int(getattr(config, "bettercam_range_x", 0))
            self.range_y = int(getattr(config, "bettercam_range_y", 0))
            self.offset_x = int(getattr(config, "bettercam_offset_x", 0))
            self.offset_y = int(getattr(config, "bettercam_offset_y", 0))
            self.trigger_offset_x = int(getattr(config, "bettercam_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(config, "bettercam_trigger_offset_y", 0))
        else:
            self.screen_width = 1920
            self.screen_height = 1080
            self.range_x = 0
            self.range_y = 0
            self.offset_x = 0
            self.offset_y = 0
            self.trigger_offset_x = 0
            self.trigger_offset_y = 0
        
        self.config = config  # 保存 config 引用以便動態讀取
        
        # 獲取屏幕分辨率（如果可能）
        try:
            # BetterCam 可以獲取輸出信息
            output_info = bettercam.output_info()
            if output_info and len(output_info) > output_idx:
                output = output_info[output_idx]
                # Output 對象有 resolution 屬性，返回 (width, height) 元組
                if hasattr(output, 'resolution'):
                    width, height = output.resolution
                    self.screen_width = width
                    self.screen_height = height
                    logger.info(f"檢測到屏幕分辨率: {self.screen_width}x{self.screen_height}")
                elif hasattr(output, 'width') and hasattr(output, 'height'):
                    self.screen_width = output.width
                    self.screen_height = output.height
                    logger.info(f"檢測到屏幕分辨率: {self.screen_width}x{self.screen_height}")
        except Exception as e:
            logger.warning(f"無法自動檢測屏幕分辨率: {e}")
            # 如果檢測失敗且 config 中沒有設置，使用默認值
            if not config or not hasattr(config, "screen_width") or getattr(config, "screen_width", 0) == 0:
                # 嘗試使用 Windows API 獲取屏幕分辨率
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    self.screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                    self.screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                    logger.info(f"使用 Windows API 檢測到屏幕分辨率: {self.screen_width}x{self.screen_height}")
                except:
                    logger.warning("無法獲取屏幕分辨率，使用默認值 1920x1080")
                    if not config or not hasattr(config, "screen_width"):
                        self.screen_width = 1920
                        self.screen_height = 1080
        
        logger.info(f"BetterCam 初始化: {self.screen_width}x{self.screen_height}, GPU={use_gpu}")
    
    def start(self):
        """啟動擷取"""
        if self.camera is not None:
            logger.warning("BetterCam 實例已存在，先停止舊實例")
            self.stop()
        
        try:
            # 動態讀取配置（允許實時更新）
            if self.config:
                self.range_x = int(getattr(self.config, "bettercam_range_x", 0))
                self.range_y = int(getattr(self.config, "bettercam_range_y", 0))
                self.offset_x = int(getattr(self.config, "bettercam_offset_x", 0))
                self.offset_y = int(getattr(self.config, "bettercam_offset_y", 0))
                # 讀取目標 FPS（如果配置中有）
                config_fps = int(getattr(self.config, "bettercam_target_fps", 0))
                if config_fps > 0:
                    self.target_fps = config_fps
                # 如果屏幕分辨率為0，嘗試重新檢測
                if self.screen_width == 0 or self.screen_height == 0:
                    screen_w = int(getattr(self.config, "screen_width", 0))
                    screen_h = int(getattr(self.config, "screen_height", 0))
                    if screen_w > 0 and screen_h > 0:
                        self.screen_width = screen_w
                        self.screen_height = screen_h
                    else:
                        # 嘗試使用 Windows API
                        try:
                            import ctypes
                            user32 = ctypes.windll.user32
                            self.screen_width = user32.GetSystemMetrics(0)
                            self.screen_height = user32.GetSystemMetrics(1)
                        except:
                            self.screen_width = 1920
                            self.screen_height = 1080
            
            # 確保屏幕分辨率有效
            if self.screen_width <= 0 or self.screen_height <= 0:
                logger.error(f"無效的屏幕分辨率: {self.screen_width}x{self.screen_height}")
                # 嘗試使用 Windows API 獲取
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    self.screen_width = user32.GetSystemMetrics(0)
                    self.screen_height = user32.GetSystemMetrics(1)
                    logger.info(f"使用 Windows API 獲取屏幕分辨率: {self.screen_width}x{self.screen_height}")
                except:
                    logger.error("無法獲取屏幕分辨率，使用默認值 1920x1080")
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
                logger.error(f"無效的擷取區域: {left}, {top}, {right}, {bottom}, 屏幕: {self.screen_width}x{self.screen_height}")
                return False
            
            # 確保 region 參數有效（BetterCam 要求 right > left 且 bottom > top）
            if right <= left or bottom <= top:
                logger.error(f"無效的擷取區域尺寸: width={actual_width}, height={actual_height}")
                return False
            
            # 創建 BetterCam 實例
            # 增加緩衝區大小以支持高 FPS（默認 64，增加到 128）
            # 注意：BetterCam 的 region 參數格式是 (left, top, right, bottom)
            region_tuple = (left, top, right, bottom)
            
            if self.use_gpu:
                try:
                    # 檢查是否安裝了 cupy（GPU 模式需要）
                    try:
                        import cupy as cp
                    except ImportError:
                        logger.warning("GPU 模式需要 cupy 模組，但未安裝。使用 CPU 模式。")
                        raise ImportError("cupy not installed")
                    
                    # BetterCam GPU 模式在處理 BGR 轉換時有問題（cupy 數組無法直接傳給 cv2.cvtColor）
                    # 使用 BGRA 避免內部顏色轉換，然後在 get_latest_frame 中手動轉換
                    self.camera = bettercam.create(
                        device_idx=self.device_idx,
                        output_idx=self.output_idx,
                        output_color="BGRA",  # 使用 BGRA 避免 GPU 模式的顏色轉換問題
                        nvidia_gpu=True,  # 明確指定使用 GPU
                        region=region_tuple,
                        max_buffer_len=128  # 增加緩衝區以支持高 FPS
                    )
                    self._gpu_bgra_mode = True  # 標記需要手動轉換 BGRA -> BGR
                except Exception as e:
                    logger.warning(f"GPU 模式失敗，使用 CPU: {e}")
                    self.use_gpu = False
                    self._gpu_bgra_mode = False
                    # 如果 GPU 失敗，回退到 CPU 模式
                    self.camera = bettercam.create(
                        output_idx=self.output_idx,
                        output_color="BGR",
                        region=region_tuple,
                        max_buffer_len=128  # 增加緩衝區以支持高 FPS
                    )
            else:
                self._gpu_bgra_mode = False
                self.camera = bettercam.create(
                    output_idx=self.output_idx,
                    output_color="BGR",
                    region=region_tuple,
                    max_buffer_len=128  # 增加緩衝區以支持高 FPS
                )
            
            # GPU 模式不能使用 start() + get_latest_frame()，因為 frame_buffer 是 numpy 數組
            # 但 GPU 模式返回的是 cupy 數組，無法存儲到 numpy 數組中
            # 所以對於 GPU 模式，我們不使用 start()，而是直接使用 grab()
            if self.use_gpu:
                # GPU 模式：不使用 start()，直接使用 grab()
                logger.info(f"BetterCam GPU 模式已啟動（使用 grab()），區域: ({left}, {top}, {right}, {bottom})")
                self.running = True
                return True
            else:
                # CPU 模式：使用 start() + get_latest_frame()
                if self.target_fps > 0:
                    self.camera.start(target_fps=self.target_fps)
                    logger.info(f"BetterCam 已啟動，區域: ({left}, {top}, {right}, {bottom}), 目標 FPS: {self.target_fps}")
                else:
                    # BetterCam 的 start() 默認 target_fps=60，所以我們需要傳遞一個高值來實現無限制
                    # 使用 300 作為"無限制"的標記（BetterCam 支持的最高值）
                    self.camera.start(target_fps=300)
                    logger.info(f"BetterCam 已啟動，區域: ({left}, {top}, {right}, {bottom}), FPS: 無限制 (300)")
                self.running = True
                return True
            
        except Exception as e:
            logger.error(f"啟動 BetterCam 失敗: {e}")
            self.camera = None
            self.running = False
            return False
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        獲取最新的屏幕截圖
        
        Returns:
            numpy.ndarray or None: 截圖幀（BGR 格式）
        """
        if not self.camera or not self.running:
            return None
        
        try:
            # GPU 模式：使用 grab() 而不是 get_latest_frame()
            # 因為 GPU 模式的 frame_buffer 是 numpy 數組，無法存儲 cupy 數組
            if self.use_gpu:
                # 直接使用 grab()，不經過 frame_buffer
                frame = self.camera.grab()
                if frame is None or frame.size == 0:
                    return None
                
                # GPU 模式返回的是 cupy 數組，需要轉換為 numpy 數組
                try:
                    import cupy as cp
                    if isinstance(frame, cp.ndarray):
                        # 將 cupy 數組轉換為 numpy 數組
                        frame = cp.asnumpy(frame)
                except (ImportError, AttributeError):
                    # 如果無法轉換，嘗試使用 get() 方法（cupy 數組的方法）
                    if hasattr(frame, 'get'):
                        frame = frame.get()
                    else:
                        logger.error("無法將 cupy 數組轉換為 numpy 數組")
                        return None
                
                # 如果使用 GPU BGRA 模式，需要手動轉換為 BGR
                if self._gpu_bgra_mode and frame is not None:
                    # BGRA -> BGR（移除 alpha 通道）
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                return frame
            else:
                # CPU 模式：使用 get_latest_frame()（經過 frame_buffer）
                frame = self.camera.get_latest_frame()
                if frame is None or frame.size == 0:
                    return None
                
                # CPU 模式已經返回 numpy 數組，直接返回
                return frame
            
        except Exception as e:
            logger.error(f"BetterCam 擷取錯誤: {e}")
            return None
    
    def get_trigger_center(self) -> Tuple[int, int]:
        """
        獲取觸發中心點座標（相對於擷取區域）
        
        Returns:
            Tuple[int, int]: (x, y) 觸發中心點座標
        """
        # 動態讀取配置
        if self.config:
            self.range_x = int(getattr(self.config, "bettercam_range_x", 0))
            self.range_y = int(getattr(self.config, "bettercam_range_y", 0))
            self.trigger_offset_x = int(getattr(self.config, "bettercam_trigger_offset_x", 0))
            self.trigger_offset_y = int(getattr(self.config, "bettercam_trigger_offset_y", 0))
        
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
        
        if self.camera:
            camera_ref = self.camera  # 保存引用，避免在清理過程中丟失
            self.camera = None  # 先清空引用，避免其他線程繼續使用
            
            try:
                # GPU 模式可能沒有調用 start()，所以不需要調用 stop()
                # 但為了安全，我們還是嘗試調用（如果沒有 start()，stop() 不會出錯）
                if not self.use_gpu:
                    # CPU 模式：嘗試停止擷取（不檢查 is_capturing，因為可能已經不存在）
                    try:
                        # 直接調用 stop()，讓 BetterCam 內部處理狀態檢查
                        camera_ref.stop()
                    except AttributeError:
                        # 如果 stop() 方法不存在或對象已損壞，跳過
                        pass
                    except Exception as e:
                        logger.warning(f"停止 BetterCam 擷取時出錯: {e}")
            except Exception as e:
                logger.warning(f"停止 BetterCam 時出錯: {e}")
            
            # 等待一小段時間讓線程完成
            import time
            time.sleep(0.2)  # 增加等待時間，確保線程完全停止
            
            # 釋放資源
            try:
                if hasattr(camera_ref, 'release'):
                    camera_ref.release()
            except AttributeError:
                # 如果 release() 方法不存在，跳過
                pass
            except Exception as e:
                logger.warning(f"釋放 BetterCam 資源時出錯: {e}")
            
            # 清空引用
            camera_ref = None
            
            # 強制垃圾回收
            import gc
            gc.collect()
            
            logger.info("BetterCam 已停止")
    
    def restart(self):
        """重新啟動擷取（用於更新設置）"""
        self.stop()
        return self.start()


def create_bettercam_capture(config=None, device_idx=0, output_idx=0, use_gpu=False, target_fps=0) -> BetterCamCapture:
    """
    創建 BetterCam 擷取實例的工廠函數
    
    Args:
        config: 配置對象
        device_idx: GPU 設備索引
        output_idx: 輸出索引
        use_gpu: 是否使用 GPU
        target_fps: 目標 FPS（0 = 無限制）
    
    Returns:
        BetterCamCapture: BetterCam 擷取實例
    """
    return BetterCamCapture(config, device_idx, output_idx, use_gpu, target_fps)

