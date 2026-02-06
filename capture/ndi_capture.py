"""
NDI 擷取模組
提供 NDI (Network Device Interface) 流接收功能
包裝 obs_ndi.py 中的 NDI_Receiver
"""

import numpy as np
import cv2
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

# 嘗試導入 NDI 模組
try:
    from capture.obs_ndi import NDI_Receiver
    NDI_AVAILABLE = True
except ImportError as e:
    NDI_AVAILABLE = False
    logger.warning(f"NDI 模組未安裝或載入失敗: {e}")


class NDICapture:
    """NDI 擷取類"""
    
    def __init__(self, config=None, source_name_or_index=None):
        """
        初始化 NDI 擷取
        
        Args:
            config: 配置對象，需要包含以下屬性：
                - ndi_width: NDI 流寬度（自動檢測）
                - ndi_height: NDI 流高度（自動檢測）
            source_name_or_index: NDI 源名稱或索引（默認 None，使用索引 0）
        """
        if not NDI_AVAILABLE:
            raise ImportError("NDI 模組未安裝，請先安裝: pip install cyndilib")
        
        self.config = config
        self.source_name_or_index = source_name_or_index or 0
        self.receiver = None
        self.running = False
        
        logger.info(f"NDI 初始化: source={self.source_name_or_index}")
    
    def start(self) -> bool:
        """
        啟動 NDI 擷取
        
        Returns:
            bool: True 如果啟動成功，False 否則
        """
        if self.receiver is not None:
            logger.warning("NDI 實例已存在，先停止舊實例")
            self.stop()
        
        try:
            self.receiver = NDI_Receiver(config=self.config)
            
            # 設置幀回調（如果需要）
            # self.receiver.set_frame_callback(self._on_frame_received)
            
            # 選擇源
            self.receiver.select_source(self.source_name_or_index)
            
            # 等待連接
            max_wait = 50  # 最多等待 5 秒
            wait_count = 0
            while wait_count < max_wait:
                if self.receiver.connected:
                    self.running = True
                    logger.info("NDI 連接成功")
                    return True
                time.sleep(0.1)
                wait_count += 1
                # 嘗試維持連接
                self.receiver.maintain_connection()
            
            logger.warning("NDI 連接超時")
            return False
            
        except Exception as e:
            logger.error(f"NDI 啟動失敗: {e}")
            self.receiver = None
            return False
    
    def stop(self):
        """停止 NDI 擷取"""
        self.running = False
        if self.receiver:
            try:
                self.receiver.disconnect()
            except Exception as e:
                logger.error(f"NDI 停止時出錯: {e}")
            self.receiver = None
        logger.info("NDI 已停止")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        獲取最新的 NDI 幀
        
        Returns:
            numpy.ndarray or None: 當前幀（BGR 格式）或 None 如果不可用
        """
        if not self.running or not self.receiver:
            return None
        
        try:
            # 維持連接
            self.receiver.maintain_connection()
            
            # 獲取當前幀
            frame = self.receiver.get_current_frame()
            
            if frame is not None and frame.size > 0:
                # NDI_Receiver 已經返回 BGR 格式的幀
                return frame
            else:
                return None
                
        except Exception as e:
            logger.error(f"NDI 獲取幀失敗: {e}")
            return None
    
    def is_connected(self) -> bool:
        """檢查是否已連接"""
        return self.running and self.receiver is not None and self.receiver.connected
    
    def list_sources(self) -> list:
        """列出可用的 NDI 源"""
        if not self.receiver:
            return []
        try:
            return self.receiver.list_sources(refresh=True)
        except Exception as e:
            logger.error(f"NDI 列出源失敗: {e}")
            return []
    
    def switch_source(self, source_name_or_index):
        """切換到不同的 NDI 源"""
        if self.receiver:
            self.receiver.switch_source(source_name_or_index)
            self.source_name_or_index = source_name_or_index


def create_ndi_capture(config=None, source_name_or_index=None):
    """
    創建 NDI 擷取實例
    
    Args:
        config: 配置對象
        source_name_or_index: NDI 源名稱或索引
        
    Returns:
        NDICapture: NDI 擷取實例
    """
    return NDICapture(config=config, source_name_or_index=source_name_or_index)

