"""
配置管理模組
負責載入、保存和管理程式配置
"""

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    # 擷取模式
    "capture_mode": "udp",  # "udp", "capture_card", "bettercam", "mss"
    "bettercam_mode": "cpu",  # "cpu", "gpu"
    
    # UDP 連接
    "udp_ip": "127.0.0.1",
    "udp_port": 1234,
    "target_fps": 60,
    
    # Capture Card 設置
    "capture_width": 1920,
    "capture_height": 1080,
    "capture_fps": 240,
    "capture_device_index": 0,
    "capture_fourcc_preference": ["NV12", "YUY2", "MJPG"],
    "capture_range_x": 0,
    "capture_range_y": 0,
    "capture_offset_x": 0,
    "capture_offset_y": 0,
    
    # 檢測模式
    "detection_mode": 1,
    
    # 模式 1 顏色
    "color_from_r": 206,
    "color_from_g": 38,
    "color_from_b": 54,
    "color_to_r": 75,
    "color_to_g": 219,
    "color_to_b": 106,
    
    # 模式 2 顏色
    "target_color_r": 206,
    "target_color_g": 38,
    "target_color_b": 54,
    
    # 檢測設置
    "tolerance": 30,
    "detection_size": 10,
    
    # 點擊設置（支持範圍隨機）
    "press_delay": 0,  # 向後兼容
    "press_delay_min": 0,
    "press_delay_max": 0,
    "release_delay": 50,  # 向後兼容
    "release_delay_min": 50,
    "release_delay_max": 50,
    "trigger_cooldown": 100,  # 向後兼容
    "trigger_cooldown_min": 100,
    "trigger_cooldown_max": 100
}


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """載入配置檔案"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合併預設值（處理新增的配置項）
                    merged_config = DEFAULT_CONFIG.copy()
                    merged_config.update(config)  # 用戶配置覆蓋預設值
                    logger.info(f"Configuration loaded from {self.config_file}")
                    return merged_config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            logger.info("Config file not found, using default configuration")
            return DEFAULT_CONFIG.copy()
    
    def save(self, config: Dict[str, Any] = None) -> bool:
        """保存配置檔案"""
        if config is not None:
            # 合併傳入的配置和現有配置，避免丟失配置項
            self.config.update(config)
        
        # 確保所有預設值都存在（處理新增的配置項）
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """設置配置值"""
        self.config[key] = value
    
    def update(self, updates: Dict[str, Any]):
        """批量更新配置"""
        self.config.update(updates)
    
    def reset_to_default(self):
        """重置為預設配置"""
        self.config = DEFAULT_CONFIG.copy()
        logger.info("Configuration reset to default")
    
    def get_all(self) -> Dict[str, Any]:
        """獲取所有配置"""
        return self.config.copy()

