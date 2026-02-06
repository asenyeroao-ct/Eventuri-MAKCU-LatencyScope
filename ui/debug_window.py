"""
調試窗口模組 - 獨立顯示 OBS UDP 串流畫面
使用異步處理確保不影響主程式性能
"""

import cv2
import numpy as np
import threading
import time
import logging
from queue import Queue, Empty
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class DebugWindow:
    """
    獨立的調試窗口，用於顯示即時畫面
    使用獨立線程處理，避免阻塞主程式
    """
    
    def __init__(self, window_name: str = "Debug Window - OBS UDP Stream"):
        """
        初始化調試窗口
        
        Args:
            window_name: 窗口名稱
        """
        self.window_name = window_name
        self.is_running = False
        self.display_thread = None
        self.frame_queue = Queue(maxsize=2)  # 只保留最新的 2 幀
        
        # 窗口狀態
        self.window_created = False
        self.last_frame_time = 0
        self.fps_counter = 0
        self.display_fps = 0.0
        self.last_fps_update = time.time()
        
        # 窗口大小管理
        self.current_frame_size = None  # (width, height)
        self.window_resized = False
        self.always_on_top = False  # 窗口置頂
        
        # 顯示設置
        self.show_info = True  # 顯示信息疊加層
        self.show_crosshair = True  # 顯示十字線
        self.detection_size = 10  # 檢測區域大小
        self.capture_region = None  # 擷取區域 (left, top, right, bottom)，用於顯示邊界
        self.target_size = None  # 目標窗口大小 (width, height)，用於自動調整窗口大小
        
        # 信息顯示開關（獨立控制每個項目）
        self.info_items = {
            'fps': True,
            'resolution': True,
            'detection_size': True,
            'state': True,
            'hotkeys': True
        }
        
        # 顏色檢測視覺化
        self.color_detector_callback: Optional[Callable] = None
        self.detected_color = None
        self.detection_state = None
        
        # 顏色選擇器
        self.color_picker_callback: Optional[Callable] = None
        
        logger.info(f"DebugWindow initialized: {window_name}")
    
    def start(self):
        """啟動調試窗口"""
        if self.is_running:
            logger.warning("Debug window already running")
            return False
        
        self.is_running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        logger.info("Debug window started")
        return True
    
    def stop(self):
        """停止調試窗口"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 等待線程結束
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2.0)
        
        # 清理隊列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break
        
        # 銷毀窗口
        if self.window_created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.waitKey(1)  # 處理窗口事件
            except Exception as e:
                logger.error(f"Error destroying window: {e}")
        
        self.window_created = False
        logger.info("Debug window stopped")
    
    def update_frame(self, frame: np.ndarray):
        """
        更新顯示幀（異步，非阻塞）
        
        Args:
            frame: OpenCV 格式的幀 (BGR)
        """
        if not self.is_running or frame is None:
            return
        
        # 非阻塞式添加幀，如果隊列滿則丟棄舊幀
        try:
            # 清空隊列，只保留最新幀
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    break
            
            # 添加新幀
            self.frame_queue.put_nowait(frame.copy())
        except Exception as e:
            # 隊列滿或其他錯誤，靜默忽略（不影響主程式）
            pass
    
    def set_detection_size(self, size: int):
        """設置檢測區域大小"""
        self.detection_size = size
    
    def set_capture_region(self, region: tuple):
        """
        設置擷取區域（用於顯示邊界）
        
        Args:
            region: (left, top, right, bottom) 擷取區域座標
        """
        self.capture_region = region
    
    def set_target_size(self, size: tuple):
        """
        設置目標窗口大小（用於自動調整窗口大小）
        
        Args:
            size: (width, height) 目標窗口大小
        """
        self.target_size = size
        # 如果窗口已創建，立即調整大小
        if self.window_created and self.target_size:
            try:
                w, h = self.target_size
                # 添加一些邊距以便顯示信息
                cv2.resizeWindow(self.window_name, max(w, 320), max(h, 240))
            except Exception as e:
                logger.warning(f"調整窗口大小時出錯: {e}")
    
    def set_detection_state(self, state: str, color: tuple = None):
        """
        設置檢測狀態（用於視覺化）
        
        Args:
            state: 檢測狀態 ("from", "to", "detected", None)
            color: 檢測到的顏色 (BGR)
        """
        self.detection_state = state
        self.detected_color = color
    
    def set_always_on_top(self, enable: bool):
        """設置窗口是否置頂"""
        self.always_on_top = enable
        if self.window_created:
            try:
                if enable:
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                else:
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 0)
            except Exception as e:
                logger.warning(f"Failed to set always on top: {e}")
    
    def set_info_item(self, item: str, visible: bool):
        """
        設置信息項目的可見性
        
        Args:
            item: 項目名稱 ('fps', 'resolution', 'detection_size', 'state', 'hotkeys')
            visible: 是否顯示
        """
        if item in self.info_items:
            self.info_items[item] = visible
    
    def set_color_picker_callback(self, callback: Optional[Callable]):
        """
        設置顏色選擇器回調
        
        Args:
            callback: 回調函數，接收 (b, g, r) 顏色元組
        """
        self.color_picker_callback = callback
        if callback:
            logger.info("Color picker activated - click on the debug window to select color")
        else:
            logger.info("Color picker deactivated")
    
    def _mouse_callback(self, event, x, y, flags, param):
        """
        OpenCV 鼠標回調函數
        
        Args:
            event: 鼠標事件類型
            x, y: 鼠標座標
            flags: 鼠標按鍵狀態
            param: 額外參數
        """
        if event == cv2.EVENT_LBUTTONDOWN and self.color_picker_callback:
            # 獲取當前幀
            try:
                # 從隊列中獲取最新幀
                frame = None
                temp_queue = []
                while not self.frame_queue.empty():
                    try:
                        temp_queue.append(self.frame_queue.get_nowait())
                    except Empty:
                        break
                
                if temp_queue:
                    # 使用最新的幀
                    frame = temp_queue[-1]
                    # 將其他幀放回隊列
                    for f in temp_queue[:-1]:
                        try:
                            self.frame_queue.put_nowait(f)
                        except:
                            pass
                
                if frame is not None and 0 <= y < frame.shape[0] and 0 <= x < frame.shape[1]:
                    # 獲取點擊位置的顏色（BGR 格式）
                    bgr_color = tuple(frame[y, x].tolist())
                    # 調用回調函數
                    self.color_picker_callback(bgr_color)
                    logger.info(f"Color picked at ({x}, {y}): BGR{bgr_color}")
            except Exception as e:
                logger.error(f"Error in mouse callback: {e}")
    
    def _display_loop(self):
        """顯示循環（獨立線程）"""
        logger.info("Debug window display loop started")
        
            # 創建窗口（初始大小，會根據第一幀或目標大小調整）
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            # 如果有目標大小，使用目標大小；否則使用預設大小
            if self.target_size:
                w, h = self.target_size
                cv2.resizeWindow(self.window_name, max(w, 320), max(h, 240))
            else:
                cv2.resizeWindow(self.window_name, 960, 540)  # 預設大小
            
            # 設置鼠標回調用於顏色選擇
            cv2.setMouseCallback(self.window_name, self._mouse_callback)
            
            # 設置置頂屬性
            if self.always_on_top:
                try:
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                except Exception:
                    pass  # 某些平台可能不支持
            
            self.window_created = True
        except Exception as e:
            logger.error(f"Failed to create debug window: {e}")
            self.is_running = False
            return
        
        no_frame_shown = False
        
        while self.is_running:
            try:
                # 優化：減少 timeout 以提高響應速度
                try:
                    frame = self.frame_queue.get(timeout=0.001)  # 1ms timeout
                    no_frame_shown = False
                except Empty:
                    # 沒有新幀，顯示等待訊息
                    if not no_frame_shown:
                        placeholder = self._create_placeholder_frame()
                        cv2.imshow(self.window_name, placeholder)
                        no_frame_shown = True
                    
                    # 處理窗口事件
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27 or cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                        # ESC 鍵或窗口被關閉
                        logger.info("Debug window closed by user")
                        self.is_running = False
                        break
                    continue
                
                # 檢查並調整窗口大小（優先使用目標大小）
                frame_h, frame_w = frame.shape[:2]
                target_w, target_h = self.target_size if self.target_size else (frame_w, frame_h)
                if self.current_frame_size != (target_w, target_h):
                    try:
                        cv2.resizeWindow(self.window_name, max(target_w, 320), max(target_h, 240))
                        self.current_frame_size = (target_w, target_h)
                    except Exception as e:
                        logger.warning(f"調整窗口大小時出錯: {e}")
                
                # 處理幀
                display_frame = self._process_frame(frame)
                
                # 顯示幀
                cv2.imshow(self.window_name, display_frame)
                
                # 更新 FPS
                self._update_fps()
                
                # 處理窗口事件
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    # ESC 鍵或窗口被關閉
                    logger.info("Debug window closed by user")
                    self.is_running = False
                    break
                elif key == ord('i'):
                    # 切換信息顯示
                    self.show_info = not self.show_info
                elif key == ord('c'):
                    # 切換十字線顯示
                    self.show_crosshair = not self.show_crosshair
                elif key == ord('f'):
                    # 切換全螢幕
                    self._toggle_fullscreen()
                
            except Exception as e:
                logger.error(f"Error in debug window display loop: {e}", exc_info=True)
                time.sleep(0.1)
        
        logger.info("Debug window display loop ended")
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        處理幀，添加視覺化元素
        
        Args:
            frame: 原始幀
            
        Returns:
            處理後的幀
        """
        display_frame = frame.copy()
        h, w = display_frame.shape[:2]
        center_y, center_x = h // 2, w // 2
        
        # 繪製擷取區域邊界（如果設置了）
        if self.capture_region is not None:
            # 由於 frame 已經是裁剪後的區域，直接繪製整個幀的邊界
            # 繪製邊界框（綠色虛線，表示這是擷取的區域）
            cv2.rectangle(display_frame, 
                         (0, 0),
                         (w - 1, h - 1),
                         (0, 255, 0), 2)  # 綠色邊界，表示擷取區域
        
        # 繪製檢測區域
        if self.show_crosshair:
            size = self.detection_size
            
            # 根據檢測狀態選擇顏色
            if self.detection_state == "from":
                color = (0, 0, 255)  # 紅色 (起始顏色)
                thickness = 3
            elif self.detection_state == "to":
                color = (0, 255, 0)  # 綠色 (目標顏色)
                thickness = 3
            elif self.detection_state == "detected":
                color = (0, 255, 255)  # 黃色 (檢測到)
                thickness = 3
            else:
                color = (255, 255, 0)  # 青色 (無檢測)
                thickness = 2
            
            # 繪製檢測框
            cv2.rectangle(display_frame, 
                         (center_x - size, center_y - size),
                         (center_x + size, center_y + size),
                         color, thickness)
            
            # 繪製中心十字線
            line_length = size + 15
            cv2.line(display_frame, 
                    (center_x - line_length, center_y), 
                    (center_x + line_length, center_y), 
                    color, 1)
            cv2.line(display_frame, 
                    (center_x, center_y - line_length), 
                    (center_x, center_y + line_length), 
                    color, 1)
            
            # 繪製中心點
            cv2.circle(display_frame, (center_x, center_y), 2, color, -1)
        
        # 添加信息疊加層
        if self.show_info:
            self._draw_info_overlay(display_frame)
        
        return display_frame
    
    def _draw_info_overlay(self, frame: np.ndarray):
        """
        繪製信息疊加層
        
        Args:
            frame: 要繪製的幀（會被修改）
        """
        h, w = frame.shape[:2]
        
        # 計算需要顯示的項目數量
        visible_items = sum(1 for key in ['fps', 'resolution', 'detection_size', 'state'] 
                           if self.info_items.get(key, True))
        
        # 動態調整背景高度
        bg_height = 20 + (visible_items * 25) + 10
        
        # 半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, bg_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # 文字信息
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        color = (255, 255, 255)
        thickness = 1
        
        y_offset = 30
        line_height = 25
        
        # FPS
        if self.info_items.get('fps', True):
            cv2.putText(frame, f"Display FPS: {self.display_fps:.1f}", 
                       (20, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
        
        # 解析度
        if self.info_items.get('resolution', True):
            cv2.putText(frame, f"Resolution: {w}x{h}", 
                       (20, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
        
        # 檢測區域
        if self.info_items.get('detection_size', True):
            cv2.putText(frame, f"Detection Size: {self.detection_size}px", 
                       (20, y_offset), font, font_scale, color, thickness)
            y_offset += line_height
        
        # 檢測狀態
        if self.info_items.get('state', True):
            if self.detection_state:
                state_text = f"State: {self.detection_state.upper()}"
                state_color = (0, 255, 0) if self.detection_state in ["to", "detected"] else (0, 165, 255)
                cv2.putText(frame, state_text, 
                           (20, y_offset), font, font_scale, state_color, thickness + 1)
            else:
                cv2.putText(frame, "State: IDLE", 
                           (20, y_offset), font, font_scale, (128, 128, 128), thickness)
            y_offset += line_height
        
        # 快捷鍵提示
        if self.info_items.get('hotkeys', True):
            cv2.putText(frame, "Press: 'I'-Info | 'C'-Crosshair | 'F'-Fullscreen | 'ESC'-Close", 
                       (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    def _create_placeholder_frame(self) -> np.ndarray:
        """創建佔位符幀（當沒有數據時顯示）"""
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        
        # 添加文字
        text = "Waiting for frames..."
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (960 - text_size[0]) // 2
        text_y = (540 + text_size[1]) // 2
        
        cv2.putText(frame, text, (text_x, text_y), font, font_scale, (128, 128, 128), thickness)
        
        return frame
    
    def _resize_window_to_frame(self, width: int, height: int):
        """
        根據幀大小調整窗口
        
        Args:
            width: 幀寬度
            height: 幀高度
        """
        try:
            # 獲取屏幕尺寸（假設主屏幕）
            import tkinter as tk
            try:
                root = tk.Tk()
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                root.destroy()
            except Exception:
                # 如果 tkinter 失敗，使用預設值
                screen_width = 1920
                screen_height = 1080
            
            # 計算合適的窗口大小
            # 最大不超過屏幕的 90%
            max_width = int(screen_width * 0.9)
            max_height = int(screen_height * 0.9)
            
            # 如果畫面太大，按比例縮小
            if width > max_width or height > max_height:
                scale = min(max_width / width, max_height / height)
                window_width = int(width * scale)
                window_height = int(height * scale)
            else:
                # 使用實際畫面大小
                window_width = width
                window_height = height
            
            # 調整窗口大小
            cv2.resizeWindow(self.window_name, window_width, window_height)
            logger.info(f"Window resized to {window_width}x{window_height} (frame: {width}x{height})")
            self.window_resized = True
            
        except Exception as e:
            logger.error(f"Failed to resize window: {e}")
    
    def _toggle_fullscreen(self):
        """切換全螢幕模式"""
        try:
            prop = cv2.getWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN)
            if prop == cv2.WINDOW_FULLSCREEN:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            else:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        except Exception as e:
            logger.error(f"Failed to toggle fullscreen: {e}")
    
    def _update_fps(self):
        """更新 FPS 計數器"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.last_fps_update >= 1.0:
            self.display_fps = self.fps_counter / (current_time - self.last_fps_update)
            self.fps_counter = 0
            self.last_fps_update = current_time
    
    def is_window_open(self) -> bool:
        """檢查窗口是否仍然打開"""
        if not self.is_running or not self.window_created:
            return False
        
        try:
            return cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) >= 1
        except Exception:
            return False


class DebugWindowManager:
    """
    調試窗口管理器（單例模式）
    確保只有一個調試窗口實例
    """
    
    _instance: Optional[DebugWindow] = None
    
    @classmethod
    def get_instance(cls) -> Optional[DebugWindow]:
        """獲取調試窗口實例"""
        return cls._instance
    
    @classmethod
    def create_window(cls, window_name: str = "Debug Window") -> DebugWindow:
        """創建或獲取調試窗口實例"""
        if cls._instance is None:
            cls._instance = DebugWindow(window_name)
        return cls._instance
    
    @classmethod
    def destroy_window(cls):
        """銷毀調試窗口實例"""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None
    
    @classmethod
    def is_active(cls) -> bool:
        """檢查調試窗口是否活躍"""
        return cls._instance is not None and cls._instance.is_running


# 便捷函數
def create_debug_window(window_name: str = "Debug Window") -> DebugWindow:
    """創建調試窗口"""
    return DebugWindowManager.create_window(window_name)


def destroy_debug_window():
    """銷毀調試窗口"""
    DebugWindowManager.destroy_window()


def is_debug_window_active() -> bool:
    """檢查調試窗口是否活躍"""
    return DebugWindowManager.is_active()

