"""
GUI 回調函數定義
集中管理所有 UI 事件處理函數，提高代碼組織性
"""

from PyQt5.QtCore import Qt, QTimer
from ui.language_manager import t
from ui.gui_constants import *


class GUICallbacks:
    """GUI 回調函數集合類"""
    
    def __init__(self, main_window):
        """
        初始化回調管理器
        
        Args:
            main_window: MainWindow 實例
        """
        self.main_window = main_window
    
    def on_language_changed(self, index):
        """語言切換處理"""
        lang_code = self.main_window.language_combo.itemData(index)
        if lang_code and self.main_window.language_manager.load_language(lang_code):
            # 保存語言設置
            self.main_window.config_manager.set("language", lang_code)
            self.main_window.config_manager.save()
            
            # 更新所有 UI 文字
            self.main_window.update_ui_texts()
            self.main_window.update_window_title()
            
            self.main_window.log(t("language_changed", f"語言已切換為: {self.main_window.language_combo.itemText(index)}"))
    
    def on_capture_mode_changed(self, index):
        """擷取模式切換處理"""
        mode_data = self.main_window.capture_mode_combo.itemData(index)
        if not mode_data:
            return
        
        # 解析模式
        if mode_data.startswith("bettercam_"):
            mode = "bettercam"
            bettercam_mode = mode_data.split("_")[1]
        else:
            mode = mode_data
            bettercam_mode = "cpu"
        
        self.main_window.current_capture_mode = mode
        
        # 顯示/隱藏對應的設置面板
        self.main_window.udp_settings_group.setVisible(mode == "udp")
        self.main_window.capture_card_settings_group.setVisible(mode == "capture_card")
        self.main_window.mss_settings_group.setVisible(mode == "mss")
        self.main_window.bettercam_settings_group.setVisible(mode == "bettercam" or mode == "bettercam_cpu" or mode == "bettercam_gpu")
        
        # 如果正在連接，先斷開
        if self.main_window.udp_receiver and self.main_window.udp_receiver.is_connected:
            self.main_window.toggle_connection()
        
        # 如果正在運行檢測，先停止
        if self.main_window.is_running:
            self.main_window.toggle_detection()
        
        self.main_window.log(f"切換到擷取模式: {self.main_window.capture_mode_combo.itemText(index)}")
        
        # 更新連接按鈕文字
        if mode == "udp":
            self.main_window.connect_btn.setText(t("connect_obs", "連接 OBS"))
        else:
            self.main_window.connect_btn.setText(t("connect", "連接"))
    
    def on_mode_changed(self):
        """檢測模式切換處理"""
        mode = self.main_window.mode_button_group.checkedId()
        self.main_window.mode1_group.setVisible(mode == 1)
        self.main_window.mode2_group.setVisible(mode == 2)
        self.main_window.color_detector.set_mode(mode)
        self.main_window.log(t("mode_switched", f"切換到模式 {mode}"))
    
    def on_tolerance_changed(self, value):
        """顏色容差改變時"""
        self.main_window.log(f"顏色容差設置為: {value}")
        # 如果檢測正在運行，立即更新
        if self.main_window.is_running:
            self.main_window.color_detector.set_tolerance(value)
            self.main_window.log(f"✓ 已應用新的顏色容差")
    
    def on_press_delay_range_changed(self, min_val: int, max_val: int):
        """按下延遲範圍改變時"""
        self.main_window.log(f"按下延遲範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.main_window.click_controller.set_press_delay_range(min_val, max_val)
        # 保存配置
        self.main_window.config_manager.set("press_delay_min", min_val)
        self.main_window.config_manager.set("press_delay_max", max_val)
        self.main_window.config_manager.save()
        if self.main_window.is_running:
            self.main_window.log(f"✓ 已應用新的按下延遲範圍")
    
    def on_release_delay_range_changed(self, min_val: int, max_val: int):
        """釋放延遲範圍改變時"""
        self.main_window.log(f"釋放延遲範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.main_window.click_controller.set_release_delay_range(min_val, max_val)
        # 保存配置
        self.main_window.config_manager.set("release_delay_min", min_val)
        self.main_window.config_manager.set("release_delay_max", max_val)
        self.main_window.config_manager.save()
        if self.main_window.is_running:
            self.main_window.log(f"✓ 已應用新的釋放延遲範圍")
    
    def on_cooldown_range_changed(self, min_val: int, max_val: int):
        """觸發冷卻範圍改變時"""
        self.main_window.log(f"觸發冷卻範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.main_window.click_controller.set_cooldown_range(min_val, max_val)
        # 保存配置
        self.main_window.config_manager.set("trigger_cooldown_min", min_val)
        self.main_window.config_manager.set("trigger_cooldown_max", max_val)
        self.main_window.config_manager.save()
        if self.main_window.is_running:
            self.main_window.log(f"✓ 已應用新的觸發冷卻範圍")
    
    def on_detection_size_changed(self, value):
        """檢測區域改變時"""
        self.main_window.log(f"檢測區域大小設置為: {value} px")
        # 立即更新檢測器
        self.main_window.color_detector.detection_size = value
        # 更新調試窗口
        if self.main_window.debug_window:
            self.main_window.debug_window.set_detection_size(value)
        # 如果檢測正在運行，通知用戶
        if self.main_window.is_running:
            self.main_window.log(f"✓ 已應用新的檢測區域大小")

