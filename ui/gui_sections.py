"""
GUI 區塊定義
將 UI 創建邏輯模組化，提高代碼組織性和可維護性
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSpinBox, QGroupBox, QRadioButton, 
                            QButtonGroup, QLineEdit, QFormLayout, QTextEdit, 
                            QCheckBox, QFrame, QGridLayout, QSlider, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.language_manager import t
from ui.gui_constants import *


def create_top_bar(language_manager, config_manager):
    """
    創建頂部控制欄
    
    Args:
        language_manager: 語言管理器實例
        config_manager: 配置管理器實例
    
    Returns:
        tuple: (container_widget, widgets_dict)
            widgets_dict 包含所有控件的引用
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(LAYOUT_SPACING)
    
    widgets = {}
    
    # 語言選擇
    lang_label = QLabel(t("language", "語言"))
    layout.addWidget(lang_label)
    
    language_combo = QComboBox()
    # 添加所有可用語言
    for lang_code, lang_name in language_manager.get_available_languages():
        language_combo.addItem(lang_name, lang_code)
    # 設置當前語言
    current_index = language_combo.findData(language_manager.get_current_lang())
    if current_index >= 0:
        language_combo.setCurrentIndex(current_index)
    layout.addWidget(language_combo)
    widgets['language_combo'] = language_combo
    
    layout.addStretch()
    
    # 連接按鈕
    connect_btn = QPushButton(t("connect_obs", "連接 OBS"))
    connect_btn.setObjectName("ConnectButton")
    connect_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
    layout.addWidget(connect_btn)
    widgets['connect_btn'] = connect_btn
    
    # 啟動/停止按鈕
    start_btn = QPushButton(t("start_detection", "啟動檢測"))
    start_btn.setObjectName("StartButton")
    start_btn.setMinimumHeight(BUTTON_MIN_HEIGHT)
    start_btn.setEnabled(False)
    layout.addWidget(start_btn)
    widgets['start_btn'] = start_btn
    
    # 配置按鈕
    save_config_btn = QPushButton(t("save_config", "保存配置"))
    layout.addWidget(save_config_btn)
    widgets['save_config_btn'] = save_config_btn
    
    load_config_btn = QPushButton(t("reload_config", "重載配置"))
    layout.addWidget(load_config_btn)
    widgets['load_config_btn'] = load_config_btn
    
    return container, widgets


def create_capture_mode_section(BETTERCAM_AVAILABLE, MSS_AVAILABLE):
    """
    創建擷取模式選擇區塊
    
    Returns:
        tuple: (layout, widgets_dict)
    """
    layout = QFormLayout()
    layout.setSpacing(FORM_SPACING)
    
    widgets = {}
    
    capture_mode_combo = QComboBox()
    capture_mode_combo.addItem(t("udp", "UDP"), "udp")
    capture_mode_combo.addItem(t("capture_card", "Capture Card"), "capture_card")
    if BETTERCAM_AVAILABLE:
        capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)"), "bettercam_cpu")
        capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)"), "bettercam_gpu")
    else:
        capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_cpu")
        capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_gpu")
    if MSS_AVAILABLE:
        capture_mode_combo.addItem(t("mss", "MSS"), "mss")
    else:
        capture_mode_combo.addItem(t("mss", "MSS") + " " + t("mss_not_installed", "[未安裝]"), "mss")
    
    layout.addRow(t("capture_mode", "擷取模式") + ":", capture_mode_combo)
    widgets['capture_mode_combo'] = capture_mode_combo
    
    return layout, widgets


def create_udp_settings_section():
    """
    創建 UDP 設置區塊
    
    Returns:
        tuple: (group_widget, widgets_dict)
    """
    group = QGroupBox(t("udp_settings", "UDP 設置"))
    layout = QFormLayout()
    layout.setSpacing(FORM_SPACING)
    
    widgets = {}
    
    ip_input = QLineEdit()
    layout.addRow(t("ip_address", "IP 地址") + ":", ip_input)
    widgets['ip_input'] = ip_input
    
    port_input = QSpinBox()
    port_input.setRange(PORT_MIN, PORT_MAX)
    layout.addRow(t("port", "端口") + ":", port_input)
    widgets['port_input'] = port_input
    
    udp_fps_input = QSpinBox()
    udp_fps_input.setRange(FPS_MIN, FPS_MAX)
    layout.addRow(t("target_fps", "目標 FPS") + ":", udp_fps_input)
    widgets['udp_fps_input'] = udp_fps_input
    
    # 本機IP顯示
    local_ip_label = QLabel()
    local_ip_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 9pt;")
    local_ip_label.setWordWrap(True)
    layout.addRow(t("local_ip", "本機 IP") + ":", local_ip_label)
    widgets['local_ip_label'] = local_ip_label
    
    # 當前連接信息顯示
    connection_info_label = QLabel(t("not_connected", "未連接"))
    connection_info_label.setStyleSheet(CONNECTION_INFO_DISCONNECTED)
    connection_info_label.setWordWrap(True)
    layout.addRow(t("connection_info", "連接信息") + ":", connection_info_label)
    widgets['connection_info_label'] = connection_info_label
    
    group.setLayout(layout)
    return group, widgets


def create_capture_card_settings_section():
    """
    創建 Capture Card 設置區塊
    
    Returns:
        tuple: (group_widget, widgets_dict)
    """
    group = QGroupBox(t("capture_card_settings", "Capture Card 設置"))
    layout = QFormLayout()
    layout.setSpacing(FORM_SPACING)
    
    widgets = {}
    
    capture_device_index_input = QSpinBox()
    capture_device_index_input.setRange(DEVICE_INDEX_MIN, DEVICE_INDEX_MAX)
    layout.addRow(t("device_index", "設備索引") + ":", capture_device_index_input)
    widgets['capture_device_index_input'] = capture_device_index_input
    
    capture_width_input = QSpinBox()
    capture_width_input.setRange(WIDTH_MIN, WIDTH_MAX)
    layout.addRow(t("width", "寬度") + ":", capture_width_input)
    widgets['capture_width_input'] = capture_width_input
    
    capture_height_input = QSpinBox()
    capture_height_input.setRange(HEIGHT_MIN, HEIGHT_MAX)
    layout.addRow(t("height", "高度") + ":", capture_height_input)
    widgets['capture_height_input'] = capture_height_input
    
    capture_fps_input = QSpinBox()
    capture_fps_input.setRange(CAPTURE_FPS_MIN, CAPTURE_FPS_MAX)
    layout.addRow(t("fps", "FPS") + ":", capture_fps_input)
    widgets['capture_fps_input'] = capture_fps_input
    
    capture_range_x_input = QSpinBox()
    capture_range_x_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_x", "範圍 X (0=自動)") + ":", capture_range_x_input)
    widgets['capture_range_x_input'] = capture_range_x_input
    
    capture_range_y_input = QSpinBox()
    capture_range_y_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_y", "範圍 Y (0=自動)") + ":", capture_range_y_input)
    widgets['capture_range_y_input'] = capture_range_y_input
    
    capture_offset_x_input = QSpinBox()
    capture_offset_x_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_x", "偏移 X") + ":", capture_offset_x_input)
    widgets['capture_offset_x_input'] = capture_offset_x_input
    
    capture_offset_y_input = QSpinBox()
    capture_offset_y_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_y", "偏移 Y") + ":", capture_offset_y_input)
    widgets['capture_offset_y_input'] = capture_offset_y_input
    
    group.setLayout(layout)
    group.setVisible(False)
    return group, widgets


def create_mss_settings_section():
    """
    創建 MSS 設置區塊
    
    Returns:
        tuple: (group_widget, widgets_dict)
    """
    group = QGroupBox(t("mss_settings", "MSS 設置"))
    layout = QFormLayout()
    layout.setSpacing(FORM_SPACING)
    
    widgets = {}
    
    mss_range_x_input = QSpinBox()
    mss_range_x_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_x", "範圍 X (0=全屏)") + ":", mss_range_x_input)
    widgets['mss_range_x_input'] = mss_range_x_input
    
    mss_range_y_input = QSpinBox()
    mss_range_y_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_y", "範圍 Y (0=全屏)") + ":", mss_range_y_input)
    widgets['mss_range_y_input'] = mss_range_y_input
    
    mss_offset_x_input = QSpinBox()
    mss_offset_x_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_x", "偏移 X (中心點)") + ":", mss_offset_x_input)
    widgets['mss_offset_x_input'] = mss_offset_x_input
    
    mss_offset_y_input = QSpinBox()
    mss_offset_y_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_y", "偏移 Y (中心點)") + ":", mss_offset_y_input)
    widgets['mss_offset_y_input'] = mss_offset_y_input
    
    mss_trigger_offset_x_input = QSpinBox()
    mss_trigger_offset_x_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("trigger_offset_x", "觸發中心偏移 X") + ":", mss_trigger_offset_x_input)
    widgets['mss_trigger_offset_x_input'] = mss_trigger_offset_x_input
    
    mss_trigger_offset_y_input = QSpinBox()
    mss_trigger_offset_y_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("trigger_offset_y", "觸發中心偏移 Y") + ":", mss_trigger_offset_y_input)
    widgets['mss_trigger_offset_y_input'] = mss_trigger_offset_y_input
    
    group.setLayout(layout)
    group.setVisible(False)
    return group, widgets


def create_bettercam_settings_section():
    """
    創建 BetterCam 設置區塊
    
    Returns:
        tuple: (group_widget, widgets_dict)
    """
    group = QGroupBox(t("bettercam_settings", "BetterCam 設置"))
    layout = QFormLayout()
    layout.setSpacing(FORM_SPACING)
    
    widgets = {}
    
    bettercam_range_x_input = QSpinBox()
    bettercam_range_x_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_x", "範圍 X (0=全屏)") + ":", bettercam_range_x_input)
    widgets['bettercam_range_x_input'] = bettercam_range_x_input
    
    bettercam_range_y_input = QSpinBox()
    bettercam_range_y_input.setRange(RANGE_MIN, RANGE_MAX)
    layout.addRow(t("range_y", "範圍 Y (0=全屏)") + ":", bettercam_range_y_input)
    widgets['bettercam_range_y_input'] = bettercam_range_y_input
    
    bettercam_offset_x_input = QSpinBox()
    bettercam_offset_x_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_x", "偏移 X (中心點)") + ":", bettercam_offset_x_input)
    widgets['bettercam_offset_x_input'] = bettercam_offset_x_input
    
    bettercam_offset_y_input = QSpinBox()
    bettercam_offset_y_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("offset_y", "偏移 Y (中心點)") + ":", bettercam_offset_y_input)
    widgets['bettercam_offset_y_input'] = bettercam_offset_y_input
    
    bettercam_trigger_offset_x_input = QSpinBox()
    bettercam_trigger_offset_x_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("trigger_offset_x", "觸發中心偏移 X") + ":", bettercam_trigger_offset_x_input)
    widgets['bettercam_trigger_offset_x_input'] = bettercam_trigger_offset_x_input
    
    bettercam_trigger_offset_y_input = QSpinBox()
    bettercam_trigger_offset_y_input.setRange(OFFSET_MIN, OFFSET_MAX)
    layout.addRow(t("trigger_offset_y", "觸發中心偏移 Y") + ":", bettercam_trigger_offset_y_input)
    widgets['bettercam_trigger_offset_y_input'] = bettercam_trigger_offset_y_input
    
    group.setLayout(layout)
    group.setVisible(False)
    return group, widgets

