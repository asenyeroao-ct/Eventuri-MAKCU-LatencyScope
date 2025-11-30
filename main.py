import sys
import os
import cv2
import numpy as np
import time
import logging
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSpinBox, 
                            QGroupBox, QRadioButton, QButtonGroup, QLineEdit,
                            QFormLayout, QTextEdit, QCheckBox, QFrame, QGridLayout, QSlider, QComboBox)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QFont

# 導入詳細的日誌系統
from utils.debugLog import get_logger, log_exception, log_connection_event, log_state_change

# 初始化 logger - 使用新的日誌系統
logger = get_logger(__name__)

# 導入自定義模組 - 直接使用 OBS_UDP.py
try:
    from capture.OBS_UDP import OBS_UDP_Receiver
    logger.info("成功載入 OBS_UDP.py")
except Exception as e:
    log_exception(e, context="載入 OBS_UDP 模組", additional_info={
        "模組": "OBS_UDP.py"
    })
    raise  # 如果無法載入 OBS_UDP.py，應該報錯

# 導入 OBS_TCP 模組
try:
    from capture.OBS_TCP import OBS_TCP_Receiver
    TCP_AVAILABLE = True
    logger.info("成功載入 OBS_TCP.py")
except Exception as e:
    TCP_AVAILABLE = False
    log_exception(e, context="載入 OBS_TCP 模組", additional_info={
        "模組": "OBS_TCP.py",
        "影響": "TCP 擷取模式不可用"
    })
    logger.warning(f"OBS_TCP 未安裝或載入失敗，TCP 擷取模式不可用: {e}")

# 導入 OBS_SRT 模組
try:
    from capture.OBS_SRT import OBS_SRT_Receiver
    SRT_AVAILABLE = True
    logger.info("成功載入 OBS_SRT.py")
except Exception as e:
    SRT_AVAILABLE = False
    log_exception(e, context="載入 OBS_SRT 模組", additional_info={
        "模組": "OBS_SRT.py",
        "影響": "SRT 擷取模式不可用"
    })
    logger.warning(f"OBS_SRT 未安裝或載入失敗，SRT 擷取模式不可用: {e}")
from utils.mouse import Mouse
import utils.mouse as mouse_module
from ui.debug_window import DebugWindowManager
from utils.color_detector import ColorDetector
from utils.click_controller import ClickController
from utils.config_manager import ConfigManager
from capture.CaptureCard import create_capture_card_camera, CaptureCardCamera
from ui.language_manager import get_language_manager, t

# 嘗試導入可選的擷取庫
try:
    from capture.mss_capture import create_mss_capture, MSSCapture
    MSS_AVAILABLE = True
    logger.info("MSS 擷取庫載入成功")
except ImportError as e:
    MSS_AVAILABLE = False
    log_exception(e, context="載入 MSS 擷取庫", additional_info={
        "模組": "mss_capture",
        "影響": "MSS 擷取模式不可用"
    })
    logger.warning(f"mss 未安裝或載入失敗，MSS 擷取模式不可用: {e}")

try:
    from capture.bettercam_capture import create_bettercam_capture, BetterCamCapture
    BETTERCAM_AVAILABLE = True
    logger.info("BetterCam 擷取庫載入成功")
except ImportError as e:
    BETTERCAM_AVAILABLE = False
    log_exception(e, context="載入 BetterCam 擷取庫", additional_info={
        "模組": "bettercam_capture",
        "影響": "BetterCam 擷取模式不可用"
    })
    logger.warning(f"bettercam 未安裝或載入失敗，BetterCam 擷取模式不可用: {e}")

try:
    from capture.dxgi_capture import create_dxgi_capture, DXGICapture
    DXGI_AVAILABLE = True
    logger.info("DXGI 擷取庫載入成功")
except ImportError as e:
    DXGI_AVAILABLE = False
    log_exception(e, context="載入 DXGI 擷取庫", additional_info={
        "模組": "dxgi_capture",
        "影響": "DXGI 擷取模式不可用"
    })
    logger.warning(f"dxcam 未安裝或載入失敗，DXGI 擷取模式不可用: {e}")

try:
    from capture.ndi_capture import create_ndi_capture, NDICapture
    NDI_AVAILABLE = True
    logger.info("NDI 擷取庫載入成功")
except ImportError as e:
    NDI_AVAILABLE = False
    log_exception(e, context="載入 NDI 擷取庫", additional_info={
        "模組": "ndi_capture",
        "影響": "NDI 擷取模式不可用"
    })
    logger.warning(f"NDI 未安裝或載入失敗，NDI 擷取模式不可用: {e}")

CONFIG_FILE = "config.json"

# 暗色科技風樣式表
MODERN_STYLESHEET = """
QMainWindow {
    background-color: #121212;
    color: #E0E0E0;
}

QWidget {
    color: #E0E0E0;
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    font-size: 10pt;
}

/* GroupBox - 半透明面板風格 */
QGroupBox {
    background-color: rgba(30, 30, 30, 0.6);
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 24px;
    font-weight: bold;
    color: #00E5FF; /* 標題青色 */
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: transparent;
}

/* 輸入框 */
QLineEdit, QSpinBox, QTextEdit {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #FFFFFF;
    padding: 4px;
    selection-background-color: #00E5FF;
    selection-color: #000000;
}

QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #00E5FF; /* 聚焦時青色邊框 */
}

/* 下拉選單 */
QComboBox {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #FFFFFF;
    padding: 4px 8px;
    min-width: 120px;
}

QComboBox:hover {
    border: 1px solid #00E5FF;
}

QComboBox:focus {
    border: 1px solid #00E5FF;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
    background-color: transparent;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #00E5FF;
    width: 0;
    height: 0;
    margin-right: 5px;
}

QComboBox QAbstractItemView {
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 4px;
    color: #FFFFFF;
    selection-background-color: #00E5FF;
    selection-color: #000000;
    outline: none;
    padding: 2px;
}

QComboBox QAbstractItemView::item {
    padding: 4px 8px;
    border-radius: 2px;
    min-height: 20px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #2D2D2D;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #00E5FF;
    color: #000000;
}

/* 按鈕 - 科技平面風格 */
QPushButton {
    background-color: #2D2D2D;
    border: 1px solid #444444;
    border-radius: 4px;
    color: #FFFFFF;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3D3D3D;
    border: 1px solid #00E5FF;
    color: #00E5FF;
}

QPushButton:pressed {
    background-color: #00E5FF;
    color: #000000;
}

QPushButton:disabled {
    background-color: #1a1a1a;
    border: 1px solid #2a2a2a;
    color: #555555;
}

/* 特殊按鈕樣式 - 連接/啟動 */
QPushButton#ConnectButton, QPushButton#StartButton {
    background-color: rgba(0, 100, 100, 0.3);
    border: 1px solid #00E5FF;
    color: #00E5FF;
    font-size: 11pt;
}

QPushButton#ConnectButton:hover, QPushButton#StartButton:hover {
    background-color: rgba(0, 229, 255, 0.2);
}

QPushButton#ConnectButton:checked, QPushButton#StartButton:checked {
    background-color: rgba(255, 85, 85, 0.3);
    border: 1px solid #FF5555;
    color: #FF5555;
}

/* Checkbox & RadioButton */
QCheckBox, QRadioButton {
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    background-color: #1E1E1E;
    border: 1px solid #555555;
    border-radius: 3px;
}

QCheckBox::indicator:checked {
    background-color: #00E5FF;
    border: 1px solid #00E5FF;
    image: url(none); /* 可以放自定義圖標，這裡簡化為顏色 */
}

QRadioButton::indicator {
    border-radius: 9px;
}

QRadioButton::indicator:checked {
    background-color: #00E5FF;
    border: 2px solid #1E1E1E;
}

/* 滾動條 */
QScrollBar:vertical {
    border: none;
    background: #121212;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #00E5FF;
}

/* 滑條 */
QSlider::groove:horizontal {
    border: 1px solid #333333;
    height: 6px;
    background: #1E1E1E;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #00E5FF;
    border: 1px solid #00E5FF;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #00B8D4;
    border: 1px solid #00B8D4;
}

QSlider::handle:horizontal:pressed {
    background: #0097A7;
    border: 1px solid #0097A7;
}

/* 標籤高亮 */
QLabel#StatusLabel {
    color: #00E5FF;
    font-family: 'Consolas', monospace;
}

QLabel#DetectionStatus {
    background-color: #1E1E1E;
    border: 1px solid #333;
    color: #FFF;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化模組
        self.config_manager = ConfigManager()
        self.language_manager = get_language_manager()
        self.click_controller = ClickController()
        self.color_detector = ColorDetector()
        
        # 從配置載入語言設置
        saved_lang = self.config_manager.get("language", "zh_CN")
        if saved_lang:
            self.language_manager.load_language(saved_lang)
        
        # 從配置初始化控制器（支持範圍或單一值）
        press_delay_min = self.config_manager.get("press_delay_min", self.config_manager.get("press_delay", 0))
        press_delay_max = self.config_manager.get("press_delay_max", self.config_manager.get("press_delay", 0))
        self.click_controller.set_press_delay_range(press_delay_min, press_delay_max)
        
        release_delay_min = self.config_manager.get("release_delay_min", self.config_manager.get("release_delay", 50))
        release_delay_max = self.config_manager.get("release_delay_max", self.config_manager.get("release_delay", 50))
        self.click_controller.set_release_delay_range(release_delay_min, release_delay_max)
        
        cooldown_min = self.config_manager.get("trigger_cooldown_min", self.config_manager.get("trigger_cooldown", 100))
        cooldown_max = self.config_manager.get("trigger_cooldown_max", self.config_manager.get("trigger_cooldown", 100))
        self.click_controller.set_cooldown_range(cooldown_min, cooldown_max)
        
        # 初始化組件
        self.udp_receiver = None
        self.tcp_receiver = None
        self.srt_receiver = None
        self.capture_card_camera = None
        self.bettercam_camera = None
        self.mss_capture = None
        self.dxgi_capture = None
        self.ndi_capture = None
        self.current_capture_mode = None
        self.mouse = None
        self.is_running = False
        self.debug_window = None  # 調試窗口實例
        
        # 畫面更新標記
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.frame_count_start_time = time.time()
        
        # FPS 計算
        self.ui_update_count = 0
        self.ui_update_start_time = time.time()
        self.capture_fps = 0.0
        self.ui_fps = 0.0
        
        # 異步處理框架
        # 檢測線程池：用於並行處理顏色檢測
        # 增加線程數以支持高 FPS 處理
        self.detection_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="Detection")
        
        # 幀處理隊列：用於異步處理接收到的幀
        # 增大隊列大小以支持高 FPS（144+），避免成為瓶頸
        self.frame_processing_queue = Queue(maxsize=60)  # 增加隊列大小以支持更高 FPS
        
        # 檢測結果隊列：用於從檢測線程傳遞結果到主線程
        self.detection_result_queue = Queue(maxsize=20)  # 增加結果隊列大小
        
        # 啟動多個幀處理線程以提升並行處理能力
        # 使用多線程並行處理幀，提升高 FPS 下的處理能力
        num_frame_processors = 4  # 使用 4 個幀處理線程
        self.frame_processor_threads = []
        for i in range(num_frame_processors):
            thread = threading.Thread(
            target=self._frame_processor_loop,
            daemon=True,
                name=f"FrameProcessor-{i}"
        )
            thread.start()
            self.frame_processor_threads.append(thread)
        
        # 檢測結果處理線程
        self.result_processor_thread = threading.Thread(
            target=self._result_processor_loop,
            daemon=True,
            name="ResultProcessor"
        )
        self.result_processor_thread.start()
        
        # 線程安全鎖
        self.detection_lock = threading.Lock()
        self.frame_lock = threading.Lock()
        
        # 當前處理中的幀（用於調試窗口）
        self.current_display_frame = None
        
        # 顏色選擇器狀態
        self.color_picker_active = False
        self.color_picker_target = None  # 'from', 'to', 'target'
        
        # 連接信息
        self.current_connection_ip = None
        self.current_connection_port = None
        
        # 設置 UI
        self.setup_ui()
        
        # 從配置載入設置
        self.load_settings_from_config()
        
        # 初始化當前擷取模式
        mode_data = self.capture_mode_combo.currentData()
        if mode_data and mode_data.startswith("bettercam_"):
            self.current_capture_mode = "bettercam"
        elif mode_data:
            self.current_capture_mode = mode_data
        else:
            self.current_capture_mode = "udp"
        
        # 定時器用於更新畫面和統計
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(33)  # 約 30 FPS
        
        # 更新窗口標題
        self.update_window_title()
        
        self.log(t("program_started", "程式已啟動，配置已載入"))
        
        # 自動連接 MAKCU 設備
        QTimer.singleShot(500, self.auto_connect_mouse)  # 延遲 500ms 後自動連接
    
    def setup_ui(self):
        """設置用戶界面 (三欄式佈局)"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 使用垂直主佈局：頂部控制 -> 中間內容 -> 底部日誌
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. 頂部控制欄 (Top Bar)
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # 2. 中間內容區 (Main Content)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左欄：設置 (參數配置)
        settings_panel = self.create_settings_panel()
        content_layout.addWidget(settings_panel, 1)
        
        # 右欄：監控 (狀態與測試)
        monitor_panel = self.create_monitor_panel()
        content_layout.addWidget(monitor_panel, 1)
        
        main_layout.addLayout(content_layout, 3)
        
        # 3. 底部日誌區 (Bottom Log)
        log_panel = self.create_log_panel()
        main_layout.addWidget(log_panel, 1)

        # 4. 底部資訊條 (Footer)
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(5)

        footer_label = QLabel(
            "made by asenyeroao   |   server: "
            "<a href=\"https://discord.gg/M6dVNKq8zP\">https://discord.gg/M6dVNKq8zP</a>"
        )
        footer_label.setTextFormat(Qt.RichText)
        footer_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        footer_label.setOpenExternalLinks(True)
        footer_label.setStyleSheet("color: #777777; font-size: 9pt; padding-top: 4px;")

        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()

        main_layout.addWidget(footer_widget)

    def create_top_bar(self):
        """創建頂部控制欄"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 語言選擇 + 作者資訊（頂部）
        lang_container = QWidget()
        lang_layout = QVBoxLayout(lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(0)

        lang_label = QLabel(t("language", "語言"))
        lang_layout.addWidget(lang_label)
        
        self.language_combo = QComboBox()
        # 添加所有可用語言
        for lang_code, lang_name in self.language_manager.get_available_languages():
            self.language_combo.addItem(lang_name, lang_code)
        # 設置當前語言
        current_index = self.language_combo.findData(self.language_manager.get_current_lang())
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.language_combo)

        top_author_label = QLabel(
            "made by asenyeroao | "
            "<a href=\"https://discord.gg/M6dVNKq8zP\">Discord server</a>"
        )
        top_author_label.setTextFormat(Qt.RichText)
        top_author_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        top_author_label.setOpenExternalLinks(True)
        top_author_label.setStyleSheet("color: #777777; font-size: 8pt; padding-top: 2px;")
        lang_layout.addWidget(top_author_label)

        layout.addWidget(lang_container)
        
        # FPS 顯示標籤
        self.fps_label = QLabel(t("ui_fps_display", "UI FPS: 0.0 | 擷取FPS: 0.0"))
        self.fps_label.setStyleSheet("color: #00E5FF; font-family: 'Consolas', monospace; font-size: 9pt; padding: 4px 8px;")
        layout.addWidget(self.fps_label)
        
        layout.addStretch()
        
        # 連接按鈕
        self.connect_btn = QPushButton(t("connect_obs", "連接 OBS"))
        self.connect_btn.setObjectName("ConnectButton")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        # 啟動/停止按鈕
        self.start_btn = QPushButton(t("start_detection", "啟動檢測"))
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.toggle_detection)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)
        
        # 配置按鈕
        self.save_config_btn = QPushButton(t("save_config", "保存配置"))
        self.save_config_btn.clicked.connect(self.save_current_config)
        layout.addWidget(self.save_config_btn)
        
        self.load_config_btn = QPushButton(t("reload_config", "重載配置"))
        self.load_config_btn.clicked.connect(self.reload_config)
        layout.addWidget(self.load_config_btn)
        
        return container

    def create_settings_panel(self):
        """創建設置面板 (左欄)"""
        panel = QGroupBox(t("parameter_settings", "參數設置"))
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # 0. 擷取模式選擇
        capture_mode_layout = QFormLayout()
        capture_mode_layout.setSpacing(8)
        
        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItem(t("udp", "UDP"), "udp")
        if TCP_AVAILABLE:
            self.capture_mode_combo.addItem(t("tcp", "TCP"), "tcp")
        else:
            self.capture_mode_combo.addItem(t("tcp", "TCP") + " " + t("tcp_not_installed", "[未安裝]"), "tcp")
        if SRT_AVAILABLE:
            self.capture_mode_combo.addItem(t("srt", "SRT"), "srt")
        else:
            self.capture_mode_combo.addItem(t("srt", "SRT") + " " + t("srt_not_installed", "[未安裝]"), "srt")
        self.capture_mode_combo.addItem(t("capture_card", "Capture Card"), "capture_card")
        if BETTERCAM_AVAILABLE:
            self.capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)"), "bettercam_cpu")
            self.capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)"), "bettercam_gpu")
        else:
            self.capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_cpu")
            self.capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_gpu")
        if MSS_AVAILABLE:
            self.capture_mode_combo.addItem(t("mss", "MSS"), "mss")
        else:
            self.capture_mode_combo.addItem(t("mss", "MSS") + " " + t("mss_not_installed", "[未安裝]"), "mss")
        if DXGI_AVAILABLE:
            self.capture_mode_combo.addItem(t("dxgi", "DXGI"), "dxgi")
        else:
            self.capture_mode_combo.addItem(t("dxgi", "DXGI") + " " + t("dxgi_not_installed", "[未安裝]"), "dxgi")
        if NDI_AVAILABLE:
            self.capture_mode_combo.addItem(t("ndi", "OBS NDI"), "ndi")
        else:
            self.capture_mode_combo.addItem(t("ndi", "OBS NDI") + " " + t("ndi_not_installed", "[未安裝]"), "ndi")
        
        self.capture_mode_combo.currentIndexChanged.connect(self.on_capture_mode_changed)
        capture_mode_label = QLabel(t("capture_mode", "擷取模式") + ":")
        capture_mode_layout.addRow(capture_mode_label, self.capture_mode_combo)
        self.capture_mode_label = capture_mode_label  # 保存引用以便更新
        
        layout.addLayout(capture_mode_layout)
        
        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)
        
        # 1. UDP 設置面板
        self.udp_settings_group = QGroupBox(t("udp_settings", "UDP 設置"))
        udp_layout = QFormLayout()
        udp_layout.setSpacing(8)
        
        self.ip_input = QLineEdit()
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.udp_fps_input = QSpinBox()
        self.udp_fps_input.setRange(30, 240)
        
        udp_layout.addRow(t("ip_address", "IP 地址") + ":", self.ip_input)
        udp_layout.addRow(t("port", "端口") + ":", self.port_input)
        udp_layout.addRow(t("target_fps", "目標 FPS") + ":", self.udp_fps_input)
        
        # 本機IP顯示
        self.local_ip_label = QLabel()
        self.local_ip_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
        self.local_ip_label.setWordWrap(True)
        self._update_local_ip_display()
        udp_layout.addRow(t("local_ip", "本機 IP") + ":", self.local_ip_label)
        
        # 當前連接信息顯示
        self.connection_info_label = QLabel(t("not_connected", "未連接"))
        self.connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        self.connection_info_label.setWordWrap(True)
        udp_layout.addRow(t("connection_info", "連接信息") + ":", self.connection_info_label)
        
        self.udp_settings_group.setLayout(udp_layout)
        layout.addWidget(self.udp_settings_group)
        
        # 1.5. TCP 設置面板
        self.tcp_settings_group = QGroupBox(t("tcp_settings", "TCP 設置"))
        tcp_layout = QFormLayout()
        tcp_layout.setSpacing(8)
        
        self.tcp_ip_input = QLineEdit()
        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_fps_input = QSpinBox()
        self.tcp_fps_input.setRange(30, 240)
        self.tcp_server_mode_checkbox = QCheckBox()
        
        tcp_layout.addRow(t("ip_address", "IP 地址") + ":", self.tcp_ip_input)
        tcp_layout.addRow(t("port", "端口") + ":", self.tcp_port_input)
        tcp_layout.addRow(t("target_fps", "目標 FPS") + ":", self.tcp_fps_input)
        tcp_layout.addRow(t("server_mode", "伺服器模式 (監聽連接)") + ":", self.tcp_server_mode_checkbox)
        
        # 本機IP顯示
        self.tcp_local_ip_label = QLabel()
        self.tcp_local_ip_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
        self.tcp_local_ip_label.setWordWrap(True)
        self._update_local_ip_display()
        tcp_layout.addRow(t("local_ip", "本機 IP") + ":", self.tcp_local_ip_label)
        
        # 當前連接信息顯示
        self.tcp_connection_info_label = QLabel(t("not_connected", "未連接"))
        self.tcp_connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        self.tcp_connection_info_label.setWordWrap(True)
        tcp_layout.addRow(t("connection_info", "連接信息") + ":", self.tcp_connection_info_label)
        
        self.tcp_settings_group.setLayout(tcp_layout)
        self.tcp_settings_group.setVisible(False)
        layout.addWidget(self.tcp_settings_group)
        
        # 1.6. SRT 設置面板
        self.srt_settings_group = QGroupBox(t("srt_settings", "SRT 設置"))
        srt_layout = QFormLayout()
        srt_layout.setSpacing(8)
        
        self.srt_ip_input = QLineEdit()
        self.srt_port_input = QSpinBox()
        self.srt_port_input.setRange(1, 65535)
        self.srt_fps_input = QSpinBox()
        self.srt_fps_input.setRange(30, 240)
        self.srt_listener_mode_checkbox = QCheckBox()
        
        srt_layout.addRow(t("ip_address", "IP 地址") + ":", self.srt_ip_input)
        srt_layout.addRow(t("port", "端口") + ":", self.srt_port_input)
        srt_layout.addRow(t("target_fps", "目標 FPS") + ":", self.srt_fps_input)
        srt_layout.addRow(t("listener_mode", "監聽模式 (等待連接)") + ":", self.srt_listener_mode_checkbox)
        
        # 本機IP顯示
        self.srt_local_ip_label = QLabel()
        self.srt_local_ip_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
        self.srt_local_ip_label.setWordWrap(True)
        self._update_local_ip_display()
        srt_layout.addRow(t("local_ip", "本機 IP") + ":", self.srt_local_ip_label)
        
        # 當前連接信息顯示
        self.srt_connection_info_label = QLabel(t("not_connected", "未連接"))
        self.srt_connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        self.srt_connection_info_label.setWordWrap(True)
        srt_layout.addRow(t("connection_info", "連接信息") + ":", self.srt_connection_info_label)
        
        self.srt_settings_group.setLayout(srt_layout)
        self.srt_settings_group.setVisible(False)
        layout.addWidget(self.srt_settings_group)
        
        # 2. Capture Card 設置面板
        self.capture_card_settings_group = QGroupBox(t("capture_card_settings", "Capture Card 設置"))
        capture_card_layout = QFormLayout()
        capture_card_layout.setSpacing(8)
        
        self.capture_device_index_input = QSpinBox()
        self.capture_device_index_input.setRange(0, 10)
        self.capture_width_input = QSpinBox()
        self.capture_width_input.setRange(320, 7680)
        self.capture_height_input = QSpinBox()
        self.capture_height_input.setRange(240, 4320)
        self.capture_fps_input = QSpinBox()
        self.capture_fps_input.setRange(1, 300)
        self.capture_range_x_input = QSpinBox()
        self.capture_range_x_input.setRange(0, 7680)
        self.capture_range_y_input = QSpinBox()
        self.capture_range_y_input.setRange(0, 4320)
        self.capture_offset_x_input = QSpinBox()
        self.capture_offset_x_input.setRange(-3840, 3840)
        self.capture_offset_y_input = QSpinBox()
        self.capture_offset_y_input.setRange(-2160, 2160)
        
        capture_card_layout.addRow(t("device_index", "設備索引") + ":", self.capture_device_index_input)
        capture_card_layout.addRow(t("width", "寬度") + ":", self.capture_width_input)
        capture_card_layout.addRow(t("height", "高度") + ":", self.capture_height_input)
        capture_card_layout.addRow(t("fps", "FPS") + ":", self.capture_fps_input)
        capture_card_layout.addRow(t("range_x", "範圍 X (0=自動)") + ":", self.capture_range_x_input)
        capture_card_layout.addRow(t("range_y", "範圍 Y (0=自動)") + ":", self.capture_range_y_input)
        capture_card_layout.addRow(t("offset_x", "偏移 X") + ":", self.capture_offset_x_input)
        capture_card_layout.addRow(t("offset_y", "偏移 Y") + ":", self.capture_offset_y_input)
        
        self.capture_card_settings_group.setLayout(capture_card_layout)
        self.capture_card_settings_group.setVisible(False)
        layout.addWidget(self.capture_card_settings_group)
        
        # 3. MSS 設置面板
        self.mss_settings_group = QGroupBox(t("mss_settings", "MSS 設置"))
        mss_layout = QFormLayout()
        mss_layout.setSpacing(8)
        
        self.mss_range_x_input = QSpinBox()
        self.mss_range_x_input.setRange(1, 7680)  # 最小值改為 1
        self.mss_range_y_input = QSpinBox()
        self.mss_range_y_input.setRange(1, 4320)  # 最小值改為 1
        self.mss_offset_x_input = QSpinBox()
        self.mss_offset_x_input.setRange(-3840, 3840)
        self.mss_offset_y_input = QSpinBox()
        self.mss_offset_y_input.setRange(-2160, 2160)
        self.mss_trigger_offset_x_input = QSpinBox()
        self.mss_trigger_offset_x_input.setRange(-3840, 3840)
        self.mss_trigger_offset_y_input = QSpinBox()
        self.mss_trigger_offset_y_input.setRange(-2160, 2160)
        
        mss_layout.addRow(t("range_x", "範圍 X (0=全屏)") + ":", self.mss_range_x_input)
        mss_layout.addRow(t("range_y", "範圍 Y (0=全屏)") + ":", self.mss_range_y_input)
        mss_layout.addRow(t("offset_x", "偏移 X (中心點)") + ":", self.mss_offset_x_input)
        mss_layout.addRow(t("offset_y", "偏移 Y (中心點)") + ":", self.mss_offset_y_input)
        mss_layout.addRow(t("trigger_offset_x", "觸發中心偏移 X") + ":", self.mss_trigger_offset_x_input)
        mss_layout.addRow(t("trigger_offset_y", "觸發中心偏移 Y") + ":", self.mss_trigger_offset_y_input)
        
        # 連接範圍和偏移變化的回調
        self.mss_range_x_input.valueChanged.connect(self.on_mss_range_changed)
        self.mss_range_y_input.valueChanged.connect(self.on_mss_range_changed)
        self.mss_offset_x_input.valueChanged.connect(self.on_mss_range_changed)
        self.mss_offset_y_input.valueChanged.connect(self.on_mss_range_changed)
        
        self.mss_settings_group.setLayout(mss_layout)
        self.mss_settings_group.setVisible(False)
        layout.addWidget(self.mss_settings_group)
        
        # 4. BetterCam 設置面板
        self.bettercam_settings_group = QGroupBox(t("bettercam_settings", "BetterCam 設置"))
        bettercam_layout = QFormLayout()
        bettercam_layout.setSpacing(8)
        
        self.bettercam_range_x_input = QSpinBox()
        self.bettercam_range_x_input.setRange(1, 7680)  # 最小值改為 1
        self.bettercam_range_y_input = QSpinBox()
        self.bettercam_range_y_input.setRange(1, 4320)  # 最小值改為 1
        self.bettercam_offset_x_input = QSpinBox()
        self.bettercam_offset_x_input.setRange(-3840, 3840)
        self.bettercam_offset_y_input = QSpinBox()
        self.bettercam_offset_y_input.setRange(-2160, 2160)
        self.bettercam_trigger_offset_x_input = QSpinBox()
        self.bettercam_trigger_offset_x_input.setRange(-3840, 3840)
        self.bettercam_trigger_offset_y_input = QSpinBox()
        self.bettercam_trigger_offset_y_input.setRange(-2160, 2160)
        
        # FPS 限制滑條
        bettercam_fps_layout = QHBoxLayout()
        self.bettercam_fps_slider = QSlider(Qt.Horizontal)
        self.bettercam_fps_slider.setRange(0, 300)
        self.bettercam_fps_slider.setValue(0)  # 默認無限制
        self.bettercam_fps_input = QSpinBox()
        self.bettercam_fps_input.setRange(0, 300)
        self.bettercam_fps_input.setValue(0)
        self.bettercam_fps_input.setSuffix(" FPS (0=無限制)")
        bettercam_fps_layout.addWidget(self.bettercam_fps_slider)
        bettercam_fps_layout.addWidget(self.bettercam_fps_input)
        
        # 連接滑條和輸入框
        self.bettercam_fps_slider.valueChanged.connect(self.bettercam_fps_input.setValue)
        self.bettercam_fps_input.valueChanged.connect(self.bettercam_fps_slider.setValue)
        
        bettercam_layout.addRow(t("target_fps", "目標 FPS (0=無限制)") + ":", bettercam_fps_layout)
        bettercam_layout.addRow(t("range_x", "範圍 X (0=全屏)") + ":", self.bettercam_range_x_input)
        bettercam_layout.addRow(t("range_y", "範圍 Y (0=全屏)") + ":", self.bettercam_range_y_input)
        bettercam_layout.addRow(t("offset_x", "偏移 X (中心點)") + ":", self.bettercam_offset_x_input)
        bettercam_layout.addRow(t("offset_y", "偏移 Y (中心點)") + ":", self.bettercam_offset_y_input)
        bettercam_layout.addRow(t("trigger_offset_x", "觸發中心偏移 X") + ":", self.bettercam_trigger_offset_x_input)
        bettercam_layout.addRow(t("trigger_offset_y", "觸發中心偏移 Y") + ":", self.bettercam_trigger_offset_y_input)
        
        # 連接範圍和偏移變化的回調
        self.bettercam_range_x_input.valueChanged.connect(self.on_bettercam_range_changed)
        self.bettercam_range_y_input.valueChanged.connect(self.on_bettercam_range_changed)
        self.bettercam_offset_x_input.valueChanged.connect(self.on_bettercam_range_changed)
        self.bettercam_offset_y_input.valueChanged.connect(self.on_bettercam_range_changed)
        
        self.bettercam_settings_group.setLayout(bettercam_layout)
        self.bettercam_settings_group.setVisible(False)
        layout.addWidget(self.bettercam_settings_group)
        
        # 5. DXGI 設置面板
        self.dxgi_settings_group = QGroupBox(t("dxgi_settings", "DXGI 設置"))
        dxgi_layout = QFormLayout()
        dxgi_layout.setSpacing(8)
        
        self.dxgi_range_x_input = QSpinBox()
        self.dxgi_range_x_input.setRange(1, 7680)  # 最小值改為 1
        self.dxgi_range_y_input = QSpinBox()
        self.dxgi_range_y_input.setRange(1, 4320)  # 最小值改為 1
        self.dxgi_offset_x_input = QSpinBox()
        self.dxgi_offset_x_input.setRange(-3840, 3840)
        self.dxgi_offset_y_input = QSpinBox()
        self.dxgi_offset_y_input.setRange(-2160, 2160)
        self.dxgi_trigger_offset_x_input = QSpinBox()
        self.dxgi_trigger_offset_x_input.setRange(-3840, 3840)
        self.dxgi_trigger_offset_y_input = QSpinBox()
        self.dxgi_trigger_offset_y_input.setRange(-2160, 2160)
        
        # FPS 限制滑條
        dxgi_fps_layout = QHBoxLayout()
        self.dxgi_fps_slider = QSlider(Qt.Horizontal)
        self.dxgi_fps_slider.setRange(0, 300)
        self.dxgi_fps_slider.setValue(0)  # 默認無限制
        self.dxgi_fps_input = QSpinBox()
        self.dxgi_fps_input.setRange(0, 300)
        self.dxgi_fps_input.setValue(0)
        self.dxgi_fps_input.setSuffix(" FPS (0=無限制)")
        dxgi_fps_layout.addWidget(self.dxgi_fps_slider)
        dxgi_fps_layout.addWidget(self.dxgi_fps_input)
        
        # 連接滑條和輸入框
        self.dxgi_fps_slider.valueChanged.connect(self.dxgi_fps_input.setValue)
        self.dxgi_fps_input.valueChanged.connect(self.dxgi_fps_slider.setValue)
        self.dxgi_fps_input.valueChanged.connect(self.on_dxgi_fps_changed)
        
        dxgi_layout.addRow(t("target_fps", "目標 FPS (0=無限制)") + ":", dxgi_fps_layout)
        dxgi_layout.addRow(t("range_x", "範圍 X (0=全屏)") + ":", self.dxgi_range_x_input)
        dxgi_layout.addRow(t("range_y", "範圍 Y (0=全屏)") + ":", self.dxgi_range_y_input)
        dxgi_layout.addRow(t("offset_x", "偏移 X (中心點)") + ":", self.dxgi_offset_x_input)
        dxgi_layout.addRow(t("offset_y", "偏移 Y (中心點)") + ":", self.dxgi_offset_y_input)
        dxgi_layout.addRow(t("trigger_offset_x", "觸發中心偏移 X") + ":", self.dxgi_trigger_offset_x_input)
        dxgi_layout.addRow(t("trigger_offset_y", "觸發中心偏移 Y") + ":", self.dxgi_trigger_offset_y_input)
        
        # 連接範圍和偏移變化的回調
        self.dxgi_range_x_input.valueChanged.connect(self.on_dxgi_range_changed)
        self.dxgi_range_y_input.valueChanged.connect(self.on_dxgi_range_changed)
        self.dxgi_offset_x_input.valueChanged.connect(self.on_dxgi_range_changed)
        self.dxgi_offset_y_input.valueChanged.connect(self.on_dxgi_range_changed)
        
        self.dxgi_settings_group.setLayout(dxgi_layout)
        self.dxgi_settings_group.setVisible(False)
        layout.addWidget(self.dxgi_settings_group)
        
        # NDI 設置面板
        self.ndi_settings_group = QGroupBox(t("ndi_settings", "NDI 設置"))
        ndi_layout = QFormLayout()
        ndi_layout.setSpacing(8)
        
        # NDI 源選擇
        ndi_source_layout = QHBoxLayout()
        self.ndi_source_combo = QComboBox()
        self.ndi_source_combo.setEditable(True)  # 允許手動輸入源名稱
        self.ndi_source_combo.setMinimumWidth(200)
        ndi_source_layout.addWidget(self.ndi_source_combo)
        
        self.ndi_refresh_btn = QPushButton(t("refresh", "刷新"))
        self.ndi_refresh_btn.clicked.connect(self.refresh_ndi_sources)
        ndi_source_layout.addWidget(self.ndi_refresh_btn)
        
        ndi_layout.addRow(t("ndi_source", "NDI 源") + ":", ndi_source_layout)
        
        # NDI 源索引（如果使用索引）
        self.ndi_source_index_input = QSpinBox()
        self.ndi_source_index_input.setRange(0, 99)
        self.ndi_source_index_input.setValue(0)
        self.ndi_source_index_input.setToolTip(t("ndi_source_index_tooltip", "使用索引選擇 NDI 源（0 為第一個可用源）"))
        ndi_layout.addRow(t("ndi_source_index", "源索引 (可選)") + ":", self.ndi_source_index_input)
        
        self.ndi_settings_group.setLayout(ndi_layout)
        self.ndi_settings_group.setVisible(False)
        layout.addWidget(self.ndi_settings_group)
        
        # 初始化時刷新 NDI 源列表
        if NDI_AVAILABLE:
            QTimer.singleShot(1000, self.refresh_ndi_sources)  # 延遲 1 秒後刷新，讓 NDI 有時間初始化
        
        # 分隔線
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)
        
        # 2. 檢測模式選擇
        mode_layout = QHBoxLayout()
        mode_label = QLabel(t("detection_mode", "檢測模式") + ":")
        mode_label.setStyleSheet("font-weight: bold; color: #E0E0E0;")
        mode_layout.addWidget(mode_label)
        
        self.mode_button_group = QButtonGroup()
        self.mode1_radio = QRadioButton(t("mode_1", "模式 1 (變色)"))
        self.mode2_radio = QRadioButton(t("mode_2", "模式 2 (單色)"))
        
        self.mode_button_group.addButton(self.mode1_radio, 1)
        self.mode_button_group.addButton(self.mode2_radio, 2)
        self.mode_button_group.buttonClicked.connect(self.on_mode_changed)
        
        mode_layout.addWidget(self.mode1_radio)
        mode_layout.addWidget(self.mode2_radio)
        layout.addLayout(mode_layout)
        
        # 3. 顏色設置 (動態切換)
        self.mode1_group = QWidget()
        mode1_layout = QFormLayout(self.mode1_group)
        mode1_layout.setContentsMargins(0, 0, 0, 0)
        
        # 起始顏色
        color_from_layout = QHBoxLayout()
        self.color_from_r = QSpinBox()
        self.color_from_g = QSpinBox()
        self.color_from_b = QSpinBox()
        for spin in [self.color_from_r, self.color_from_g, self.color_from_b]:
            spin.setRange(0, 255)
            spin.valueChanged.connect(lambda: self._update_color_preview('from'))
        # 顏色預覽框
        self.color_from_preview = QPushButton()
        self.color_from_preview.setFixedSize(40, 30)
        self.color_from_preview.setToolTip("點擊此框，然後在監視窗口點擊選擇顏色")
        self.color_from_preview.clicked.connect(lambda: self._start_color_picker('from'))
        color_from_layout.addWidget(QLabel(t("r", "R")))
        color_from_layout.addWidget(self.color_from_r)
        color_from_layout.addWidget(QLabel(t("g", "G")))
        color_from_layout.addWidget(self.color_from_g)
        color_from_layout.addWidget(QLabel(t("b", "B")))
        color_from_layout.addWidget(self.color_from_b)
        color_from_layout.addWidget(self.color_from_preview)
        color_from_layout.addStretch()
        mode1_layout.addRow(t("start_color", "起始顏色") + ":", color_from_layout)
        
        # 目標顏色
        color_to_layout = QHBoxLayout()
        self.color_to_r = QSpinBox()
        self.color_to_g = QSpinBox()
        self.color_to_b = QSpinBox()
        for spin in [self.color_to_r, self.color_to_g, self.color_to_b]:
            spin.setRange(0, 255)
            spin.valueChanged.connect(lambda: self._update_color_preview('to'))
        # 顏色預覽框
        self.color_to_preview = QPushButton()
        self.color_to_preview.setFixedSize(40, 30)
        self.color_to_preview.setToolTip("點擊此框，然後在監視窗口點擊選擇顏色")
        self.color_to_preview.clicked.connect(lambda: self._start_color_picker('to'))
        color_to_layout.addWidget(QLabel(t("r", "R")))
        color_to_layout.addWidget(self.color_to_r)
        color_to_layout.addWidget(QLabel(t("g", "G")))
        color_to_layout.addWidget(self.color_to_g)
        color_to_layout.addWidget(QLabel(t("b", "B")))
        color_to_layout.addWidget(self.color_to_b)
        color_to_layout.addWidget(self.color_to_preview)
        color_to_layout.addStretch()
        mode1_layout.addRow(t("target_color", "目標顏色") + ":", color_to_layout)
        layout.addWidget(self.mode1_group)
        
        self.mode2_group = QWidget()
        mode2_layout = QFormLayout(self.mode2_group)
        mode2_layout.setContentsMargins(0, 0, 0, 0)
        
        target_color_layout = QHBoxLayout()
        self.target_color_r = QSpinBox()
        self.target_color_g = QSpinBox()
        self.target_color_b = QSpinBox()
        for spin in [self.target_color_r, self.target_color_g, self.target_color_b]:
            spin.setRange(0, 255)
            spin.valueChanged.connect(lambda: self._update_color_preview('target'))
        # 顏色預覽框
        self.target_color_preview = QPushButton()
        self.target_color_preview.setFixedSize(40, 30)
        self.target_color_preview.setToolTip("點擊此框，然後在監視窗口點擊選擇顏色")
        self.target_color_preview.clicked.connect(lambda: self._start_color_picker('target'))
        target_color_layout.addWidget(QLabel(t("r", "R")))
        target_color_layout.addWidget(self.target_color_r)
        target_color_layout.addWidget(QLabel(t("g", "G")))
        target_color_layout.addWidget(self.target_color_g)
        target_color_layout.addWidget(QLabel(t("b", "B")))
        target_color_layout.addWidget(self.target_color_b)
        target_color_layout.addWidget(self.target_color_preview)
        target_color_layout.addStretch()
        mode2_layout.addRow(t("target_color", "目標顏色") + ":", target_color_layout)
        layout.addWidget(self.mode2_group)
        self.mode2_group.setVisible(False)
        
        # 4. 通用設置
        settings_layout = QFormLayout()
        settings_layout.setSpacing(8)
        
        self.tolerance_input = QSpinBox()
        self.tolerance_input.setRange(0, 100)
        self.tolerance_input.valueChanged.connect(self.on_tolerance_changed)
        settings_layout.addRow(t("color_tolerance", "顏色容差") + ":", self.tolerance_input)
        
        # 按下延遲範圍
        press_delay_widget = self._create_range_input_widget(
            t("press_delay", "按下延遲"), 0, 5000, 
            lambda min_val, max_val: self.on_press_delay_range_changed(min_val, max_val)
        )
        self.press_delay_min_input = press_delay_widget['min_input']
        self.press_delay_min_slider = press_delay_widget['min_slider']
        self.press_delay_max_input = press_delay_widget['max_input']
        self.press_delay_max_slider = press_delay_widget['max_slider']
        settings_layout.addRow(t("press_delay", "按下延遲") + ":", press_delay_widget['container'])
        
        # 釋放延遲範圍
        release_delay_widget = self._create_range_input_widget(
            t("release_delay", "釋放延遲"), 0, 5000,
            lambda min_val, max_val: self.on_release_delay_range_changed(min_val, max_val)
        )
        self.release_delay_min_input = release_delay_widget['min_input']
        self.release_delay_min_slider = release_delay_widget['min_slider']
        self.release_delay_max_input = release_delay_widget['max_input']
        self.release_delay_max_slider = release_delay_widget['max_slider']
        settings_layout.addRow(t("release_delay", "釋放延遲") + ":", release_delay_widget['container'])
        
        # 觸發冷卻範圍
        cooldown_widget = self._create_range_input_widget(
            t("trigger_cooldown", "觸發冷卻"), 0, 10000,
            lambda min_val, max_val: self.on_cooldown_range_changed(min_val, max_val)
        )
        self.cooldown_min_input = cooldown_widget['min_input']
        self.cooldown_min_slider = cooldown_widget['min_slider']
        self.cooldown_max_input = cooldown_widget['max_input']
        self.cooldown_max_slider = cooldown_widget['max_slider']
        settings_layout.addRow(t("trigger_cooldown", "觸發冷卻") + ":", cooldown_widget['container'])
        
        self.detection_size_input = QSpinBox()
        self.detection_size_input.setRange(2, 50)
        self.detection_size_input.setSuffix(t("px", " px"))
        self.detection_size_input.valueChanged.connect(self.on_detection_size_changed)
        settings_layout.addRow(t("detection_size", "檢測區域") + ":", self.detection_size_input)
        
        layout.addLayout(settings_layout)
        layout.addStretch()
        
        return panel
    
    def _create_range_input_widget(self, name: str, default_min: int, default_max: int, callback):
        """
        創建帶有滑條的範圍輸入控件
        
        Args:
            name: 控件名稱（用於提示）
            default_min: 默認最小值
            default_max: 默認最大值
            callback: 當值改變時的回調函數 (min_val, max_val)
        
        Returns:
            dict: 包含所有控件的字典
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 最小值行
        min_row = QHBoxLayout()
        min_row.setSpacing(8)
        
        min_label = QLabel(t("min", "最小") + ":")
        min_label.setMinimumWidth(40)
        min_input = QSpinBox()
        min_input.setRange(0, 99999)  # 輸入可以超過500
        min_input.setSuffix(t("ms", " ms"))
        min_input.setValue(default_min)
        min_input.setToolTip(f"{name}的最小值（可超過500）")
        
        min_slider = QSlider(Qt.Horizontal)
        min_slider.setRange(0, 500)
        min_slider.setValue(default_min)
        min_slider.setToolTip(f"{name}最小值滑條（0~500）")
        
        # 連接最小值的輸入框和滑條
        def on_min_input_changed(value):
            # 限制滑條範圍在0~500
            if value <= 500:
                min_slider.setValue(value)
            # 確保最小值不超過最大值
            if value > max_input.value():
                max_input.setValue(value)
            callback(min_input.value(), max_input.value())
        
        def on_min_slider_changed(value):
            min_input.setValue(value)
            callback(min_input.value(), max_input.value())
        
        min_input.valueChanged.connect(on_min_input_changed)
        min_slider.valueChanged.connect(on_min_slider_changed)
        
        min_row.addWidget(min_label)
        min_row.addWidget(min_input)
        min_row.addWidget(min_slider)
        min_row.addStretch()
        
        # 最大值行
        max_row = QHBoxLayout()
        max_row.setSpacing(8)
        
        max_label = QLabel(t("max", "最大") + ":")
        max_label.setMinimumWidth(40)
        max_input = QSpinBox()
        max_input.setRange(0, 99999)  # 輸入可以超過500
        max_input.setSuffix(t("ms", " ms"))
        max_input.setValue(default_max)
        max_input.setToolTip(f"{name}的最大值（可超過500）")
        
        max_slider = QSlider(Qt.Horizontal)
        max_slider.setRange(0, 500)
        max_slider.setValue(min(default_max, 500))
        max_slider.setToolTip(f"{name}最大值滑條（0~500）")
        
        # 連接最大值的輸入框和滑條
        def on_max_input_changed(value):
            # 限制滑條範圍在0~500
            if value <= 500:
                max_slider.setValue(value)
            # 確保最大值不小於最小值
            if value < min_input.value():
                min_input.setValue(value)
            callback(min_input.value(), max_input.value())
        
        def on_max_slider_changed(value):
            max_input.setValue(value)
            callback(min_input.value(), max_input.value())
        
        max_input.valueChanged.connect(on_max_input_changed)
        max_slider.valueChanged.connect(on_max_slider_changed)
        
        max_row.addWidget(max_label)
        max_row.addWidget(max_input)
        max_row.addWidget(max_slider)
        max_row.addStretch()
        
        layout.addLayout(min_row)
        layout.addLayout(max_row)
        
        return {
            'container': container,
            'min_input': min_input,
            'min_slider': min_slider,
            'max_input': max_input,
            'max_slider': max_slider
        }

    def create_monitor_panel(self):
        """創建監控面板 (右欄)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 1. 檢測狀態 (視覺化)
        status_group = QGroupBox(t("system_status", "系統狀態"))
        status_layout = QVBoxLayout()
        
        self.detection_status_label = QLabel(t("not_started", "未啟動"))
        self.detection_status_label.setObjectName("DetectionStatus")
        self.detection_status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.detection_status_label.setAlignment(Qt.AlignCenter)
        self.detection_status_label.setMinimumHeight(60)
        status_layout.addWidget(self.detection_status_label)
        
        self.cooldown_label = QLabel(t("ready", "準備就緒"))
        self.cooldown_label.setAlignment(Qt.AlignCenter)
        self.cooldown_label.setStyleSheet("color: #888; font-size: 10pt;")
        status_layout.addWidget(self.cooldown_label)
        
        self.stats_label = QLabel(t("waiting_for_data", "等待連接..."))
        self.stats_label.setObjectName("StatusLabel")
        self.stats_label.setFont(QFont("Consolas", 9))
        self.stats_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.stats_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 2. 滑鼠控制
        mouse_group = QGroupBox(t("mouse_control", "滑鼠控制"))
        mouse_layout = QVBoxLayout()
        
        # 狀態顯示
        self.mouse_status_label = QLabel(t("not_connected", "未連接"))
        self.mouse_status_label.setStyleSheet("color: #ff5555; font-weight: bold; font-size: 11pt;")
        self.mouse_status_label.setAlignment(Qt.AlignCenter)
        mouse_layout.addWidget(self.mouse_status_label)
        
        # 測試按鈕 (並排)
        test_btn_layout = QHBoxLayout()
        self.move_test_btn = QPushButton(t("test_move", "測試移動"))
        self.move_test_btn.clicked.connect(self.test_move)
        self.click_test_btn = QPushButton(t("test_click", "測試點擊"))
        self.click_test_btn.clicked.connect(self.test_click)
        test_btn_layout.addWidget(self.move_test_btn)
        test_btn_layout.addWidget(self.click_test_btn)
        mouse_layout.addLayout(test_btn_layout)
        
        self.switch_4m_btn = QPushButton(t("switch_4m", "切換 4M 波特率"))
        self.switch_4m_btn.clicked.connect(self.switch_to_4m)
        mouse_layout.addWidget(self.switch_4m_btn)
        
        mouse_group.setLayout(mouse_layout)
        layout.addWidget(mouse_group)
        
        # 3. 調試窗口
        debug_group = QGroupBox(t("debug_tools", "調試工具"))
        debug_layout = QVBoxLayout()
        
        self.debug_window_checkbox = QCheckBox(t("enable_debug_window", "開啟即時畫面預覽 (調試窗口)"))
        self.debug_window_checkbox.setStyleSheet("font-weight: bold; color: #00E5FF;")
        self.debug_window_checkbox.stateChanged.connect(self.toggle_debug_window)
        debug_layout.addWidget(self.debug_window_checkbox)
        
        # 調試選項 (並排)
        debug_opts_layout = QHBoxLayout()
        self.always_on_top_checkbox = QCheckBox(t("always_on_top", "窗口置頂"))
        self.always_on_top_checkbox.stateChanged.connect(self.toggle_always_on_top)
        debug_opts_layout.addWidget(self.always_on_top_checkbox)
        
        self.show_text_info_checkbox = QCheckBox(t("show_params", "顯示參數"))
        self.show_text_info_checkbox.setChecked(True)
        self.show_text_info_checkbox.stateChanged.connect(self.toggle_text_info)
        debug_opts_layout.addWidget(self.show_text_info_checkbox)
        
        debug_layout.addLayout(debug_opts_layout)
        
        # 詳細信息設置 (隱藏式)
        self.text_info_detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.text_info_detail_widget)
        detail_layout.setContentsMargins(10, 0, 0, 0)
        
        # 使用 Grid 佈局來節省空間
        grid_layout = QGridLayout()
        self.info_fps_checkbox = QCheckBox("FPS")
        self.info_fps_checkbox.setChecked(True)
        self.info_fps_checkbox.stateChanged.connect(lambda: self.update_info_item('fps', self.info_fps_checkbox.isChecked()))
        
        self.info_resolution_checkbox = QCheckBox("解析度")
        self.info_resolution_checkbox.setChecked(True)
        self.info_resolution_checkbox.stateChanged.connect(lambda: self.update_info_item('resolution', self.info_resolution_checkbox.isChecked()))
        
        self.info_detection_size_checkbox = QCheckBox("區域大小")
        self.info_detection_size_checkbox.setChecked(True)
        self.info_detection_size_checkbox.stateChanged.connect(lambda: self.update_info_item('detection_size', self.info_detection_size_checkbox.isChecked()))
        
        self.info_state_checkbox = QCheckBox(t("detection_state_info", "檢測狀態"))
        self.info_state_checkbox.setChecked(True)
        self.info_state_checkbox.stateChanged.connect(lambda: self.update_info_item('state', self.info_state_checkbox.isChecked()))
        
        self.info_hotkeys_checkbox = QCheckBox(t("hotkeys_info", "快捷鍵"))
        self.info_hotkeys_checkbox.setChecked(True)
        self.info_hotkeys_checkbox.stateChanged.connect(lambda: self.update_info_item('hotkeys', self.info_hotkeys_checkbox.isChecked()))
        
        grid_layout.addWidget(self.info_fps_checkbox, 0, 0)
        grid_layout.addWidget(self.info_resolution_checkbox, 0, 1)
        grid_layout.addWidget(self.info_detection_size_checkbox, 1, 0)
        grid_layout.addWidget(self.info_state_checkbox, 1, 1)
        grid_layout.addWidget(self.info_hotkeys_checkbox, 2, 0)
        
        detail_layout.addLayout(grid_layout)
        debug_layout.addWidget(self.text_info_detail_widget)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        return panel

    def create_log_panel(self):
        """創建底部日誌面板"""
        panel = QGroupBox(t("system_log", "系統日誌"))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: 'Consolas'; font-size: 9pt; background-color: #1a1a1a; border: none;")
        layout.addWidget(self.log_text)
        
        return panel
    
    def load_settings_from_config(self):
        """從配置檔案載入設置"""
        self.ip_input.setText(self.config_manager.get("udp_ip", "127.0.0.1"))
        self.port_input.setValue(self.config_manager.get("udp_port", 1234))
        # 載入擷取模式
        capture_mode = self.config_manager.get("capture_mode", "udp")
        bettercam_mode = self.config_manager.get("bettercam_mode", "cpu")
        
        # 設置擷取模式選擇器
        mode_text = capture_mode
        if capture_mode == "bettercam":
            mode_text = f"bettercam_{bettercam_mode}"
        elif capture_mode == "bettercam_cpu" or capture_mode == "bettercam_gpu":
            mode_text = capture_mode
        
        for i in range(self.capture_mode_combo.count()):
            if self.capture_mode_combo.itemData(i) == mode_text:
                self.capture_mode_combo.setCurrentIndex(i)
                break
        
        # 載入UDP設置
        self.ip_input.setText(self.config_manager.get("udp_ip", "127.0.0.1"))
        self.port_input.setValue(self.config_manager.get("udp_port", 1234))
        self.udp_fps_input.setValue(self.config_manager.get("target_fps", 60))
        
        # 載入 TCP 設置
        if hasattr(self, 'tcp_ip_input'):
            self.tcp_ip_input.setText(self.config_manager.get("tcp_ip", "192.168.0.1"))
            self.tcp_port_input.setValue(self.config_manager.get("tcp_port", 1234))
            self.tcp_fps_input.setValue(self.config_manager.get("tcp_fps", 60))
            self.tcp_server_mode_checkbox.setChecked(self.config_manager.get("tcp_server_mode", False))
        
        # 載入 SRT 設置
        if hasattr(self, 'srt_ip_input'):
            self.srt_ip_input.setText(self.config_manager.get("srt_ip", "192.168.0.1"))
            self.srt_port_input.setValue(self.config_manager.get("srt_port", 1234))
            self.srt_fps_input.setValue(self.config_manager.get("srt_fps", 60))
            self.srt_listener_mode_checkbox.setChecked(self.config_manager.get("srt_listener_mode", False))
        
        # 載入Capture Card設置
        self.capture_device_index_input.setValue(self.config_manager.get("capture_device_index", 0))
        self.capture_width_input.setValue(self.config_manager.get("capture_width", 1920))
        self.capture_height_input.setValue(self.config_manager.get("capture_height", 1080))
        self.capture_fps_input.setValue(self.config_manager.get("capture_fps", 240))
        self.capture_range_x_input.setValue(self.config_manager.get("capture_range_x", 0))
        self.capture_range_y_input.setValue(self.config_manager.get("capture_range_y", 0))
        self.capture_offset_x_input.setValue(self.config_manager.get("capture_offset_x", 0))
        self.capture_offset_y_input.setValue(self.config_manager.get("capture_offset_y", 0))
        
        # 載入MSS設置
        self.mss_range_x_input.setValue(self.config_manager.get("mss_range_x", 0))
        self.mss_range_y_input.setValue(self.config_manager.get("mss_range_y", 0))
        self.mss_offset_x_input.setValue(self.config_manager.get("mss_offset_x", 0))
        self.mss_offset_y_input.setValue(self.config_manager.get("mss_offset_y", 0))
        self.mss_trigger_offset_x_input.setValue(self.config_manager.get("mss_trigger_offset_x", 0))
        self.mss_trigger_offset_y_input.setValue(self.config_manager.get("mss_trigger_offset_y", 0))
        
        # 載入BetterCam設置
        self.bettercam_range_x_input.setValue(self.config_manager.get("bettercam_range_x", 0))
        self.bettercam_range_y_input.setValue(self.config_manager.get("bettercam_range_y", 0))
        self.bettercam_offset_x_input.setValue(self.config_manager.get("bettercam_offset_x", 0))
        self.bettercam_offset_y_input.setValue(self.config_manager.get("bettercam_offset_y", 0))
        self.bettercam_trigger_offset_x_input.setValue(self.config_manager.get("bettercam_trigger_offset_x", 0))
        self.bettercam_trigger_offset_y_input.setValue(self.config_manager.get("bettercam_trigger_offset_y", 0))
        self.bettercam_fps_input.setValue(self.config_manager.get("bettercam_target_fps", 0))
        
        # 載入DXGI設置
        self.dxgi_range_x_input.setValue(self.config_manager.get("dxgi_range_x", 0))
        self.dxgi_range_y_input.setValue(self.config_manager.get("dxgi_range_y", 0))
        self.dxgi_offset_x_input.setValue(self.config_manager.get("dxgi_offset_x", 0))
        self.dxgi_offset_y_input.setValue(self.config_manager.get("dxgi_offset_y", 0))
        self.dxgi_trigger_offset_x_input.setValue(self.config_manager.get("dxgi_trigger_offset_x", 0))
        self.dxgi_trigger_offset_y_input.setValue(self.config_manager.get("dxgi_trigger_offset_y", 0))
        self.dxgi_fps_input.setValue(self.config_manager.get("dxgi_target_fps", 0))
        
        mode = self.config_manager.get("detection_mode", 1)
        if mode == 1:
            self.mode1_radio.setChecked(True)
            self.mode1_group.setVisible(True)
            self.mode2_group.setVisible(False)
        else:
            self.mode2_radio.setChecked(True)
            self.mode1_group.setVisible(False)
            self.mode2_group.setVisible(True)
        
        self.color_from_r.setValue(self.config_manager.get("color_from_r", 206))
        self.color_from_g.setValue(self.config_manager.get("color_from_g", 38))
        self.color_from_b.setValue(self.config_manager.get("color_from_b", 54))
        self._update_color_preview('from')
        
        self.color_to_r.setValue(self.config_manager.get("color_to_r", 75))
        self.color_to_g.setValue(self.config_manager.get("color_to_g", 219))
        self.color_to_b.setValue(self.config_manager.get("color_to_b", 106))
        self._update_color_preview('to')
        
        self.target_color_r.setValue(self.config_manager.get("target_color_r", 206))
        self.target_color_g.setValue(self.config_manager.get("target_color_g", 38))
        self.target_color_b.setValue(self.config_manager.get("target_color_b", 54))
        self._update_color_preview('target')
        
        self.tolerance_input.setValue(self.config_manager.get("tolerance", 30))
        
        # 載入延遲範圍（向後兼容單一值）
        press_delay_min = self.config_manager.get("press_delay_min", self.config_manager.get("press_delay", 0))
        press_delay_max = self.config_manager.get("press_delay_max", self.config_manager.get("press_delay", 0))
        self.press_delay_min_input.setValue(press_delay_min)
        self.press_delay_max_input.setValue(press_delay_max)
        
        release_delay_min = self.config_manager.get("release_delay_min", self.config_manager.get("release_delay", 50))
        release_delay_max = self.config_manager.get("release_delay_max", self.config_manager.get("release_delay", 50))
        self.release_delay_min_input.setValue(release_delay_min)
        self.release_delay_max_input.setValue(release_delay_max)
        
        cooldown_min = self.config_manager.get("trigger_cooldown_min", self.config_manager.get("trigger_cooldown", 100))
        cooldown_max = self.config_manager.get("trigger_cooldown_max", self.config_manager.get("trigger_cooldown", 100))
        self.cooldown_min_input.setValue(cooldown_min)
        self.cooldown_max_input.setValue(cooldown_max)
        
        self.detection_size_input.setValue(self.config_manager.get("detection_size", 10))
    
    def on_capture_mode_changed(self, index):
        """擷取模式切換處理"""
        mode_data = self.capture_mode_combo.itemData(index)
        if not mode_data:
            return
        
        # 解析模式
        if mode_data.startswith("bettercam_"):
            mode = "bettercam"
            bettercam_mode = mode_data.split("_")[1]
        else:
            mode = mode_data
            bettercam_mode = "cpu"
        
        # 強制停止所有當前的擷取模式
        self._stop_all_capture_modes()
        
        self.current_capture_mode = mode
        
        # 顯示/隱藏對應的設置面板
        self.udp_settings_group.setVisible(mode == "udp")
        self.tcp_settings_group.setVisible(mode == "tcp")
        self.srt_settings_group.setVisible(mode == "srt")
        self.capture_card_settings_group.setVisible(mode == "capture_card")
        self.mss_settings_group.setVisible(mode == "mss")
        self.bettercam_settings_group.setVisible(mode == "bettercam" or mode == "bettercam_cpu" or mode == "bettercam_gpu")
        self.dxgi_settings_group.setVisible(mode == "dxgi")
        self.ndi_settings_group.setVisible(mode == "ndi")
        
        # 如果正在運行檢測，先停止
        if self.is_running:
            self.toggle_detection()
        
        self.log(t("switched_to_capture_mode", "切換到擷取模式: {mode}").format(mode=self.capture_mode_combo.itemText(index)))
        
        # 更新連接按鈕文字
        if mode == "udp" or mode == "tcp" or mode == "srt":
            self.connect_btn.setText(t("connect_obs", "連接 OBS"))
        else:
            self.connect_btn.setText(t("connect", "連接"))
        
        # 重置連接狀態
        self.connect_btn.setStyleSheet("")
        self.start_btn.setEnabled(False)
        self.stats_label.setText(t("disconnected_status", "已斷開連接"))
        self._update_connection_info()
    
    def _stop_all_capture_modes(self):
        """強制停止所有擷取模式"""
        # 停止 UDP
        if self.udp_receiver and self.udp_receiver.is_connected:
            try:
                self.udp_receiver.disconnect()
                self.udp_receiver = None
                self.log(t("udp_disconnected", "已停止 UDP 擷取"))
                log_connection_event("UDP 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 UDP 擷取", additional_info={
                    "擷取模式": "UDP",
                    "連接狀態": self.udp_receiver.is_connected if self.udp_receiver else "None"
                })
                logger.error(f"停止 UDP 時出錯: {e}")
        
        # 停止 TCP
        if self.tcp_receiver and self.tcp_receiver.is_connected:
            try:
                self.tcp_receiver.disconnect()
                self.tcp_receiver = None
                self.log(t("tcp_disconnected", "已停止 TCP 擷取"))
                log_connection_event("TCP 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 TCP 擷取", additional_info={
                    "擷取模式": "TCP",
                    "連接狀態": self.tcp_receiver.is_connected if self.tcp_receiver else "None"
                })
                logger.error(f"停止 TCP 時出錯: {e}")
        
        # 停止 SRT
        if self.srt_receiver and self.srt_receiver.is_connected:
            try:
                self.srt_receiver.disconnect()
                self.srt_receiver = None
                self.log(t("srt_disconnected", "已停止 SRT 擷取"))
                log_connection_event("SRT 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 SRT 擷取", additional_info={
                    "擷取模式": "SRT",
                    "連接狀態": self.srt_receiver.is_connected if self.srt_receiver else "None"
                })
                logger.error(f"停止 SRT 時出錯: {e}")
        
        # 停止 Capture Card
        if self.capture_card_camera:
            try:
                self.capture_card_camera.stop()
                self.capture_card_camera = None
                self.log(t("capture_card_disconnected", "已停止 Capture Card 擷取"))
                log_connection_event("Capture Card 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 Capture Card 擷取", additional_info={
                    "擷取模式": "Capture Card",
                    "相機對象": str(type(self.capture_card_camera))
                })
                logger.error(f"停止 Capture Card 時出錯: {e}")
        
        # 停止 BetterCam
        if self.bettercam_camera:
            try:
                self.bettercam_camera.stop()
                self.bettercam_camera = None
                self.log(t("bettercam_disconnected", "已停止 BetterCam 擷取"))
                log_connection_event("BetterCam 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 BetterCam 擷取", additional_info={
                    "擷取模式": "BetterCam",
                    "相機對象": str(type(self.bettercam_camera))
                })
                logger.error(f"停止 BetterCam 時出錯: {e}")
        
        # 停止 MSS
        if self.mss_capture:
            try:
                self.mss_capture.stop()
                self.mss_capture = None
                self.log(t("mss_disconnected", "已停止 MSS 擷取"))
                log_connection_event("MSS 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 MSS 擷取", additional_info={
                    "擷取模式": "MSS",
                    "擷取對象": str(type(self.mss_capture))
                })
                logger.error(f"停止 MSS 時出錯: {e}")
        
        # 停止 DXGI
        if self.dxgi_capture:
            try:
                self.dxgi_capture.stop()
                self.dxgi_capture = None
                self.log(t("dxgi_disconnected", "已停止 DXGI 擷取"))
                log_connection_event("DXGI 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 DXGI 擷取", additional_info={
                    "擷取模式": "DXGI",
                    "擷取對象": str(type(self.dxgi_capture))
                })
                logger.error(f"停止 DXGI 時出錯: {e}")
        
        # 停止 NDI
        if self.ndi_capture:
            try:
                self.ndi_capture.stop()
                self.ndi_capture = None
                self.log(t("ndi_disconnected", "已停止 NDI 擷取"))
                log_connection_event("NDI 停止", {"狀態": "成功"})
            except Exception as e:
                log_exception(e, context="停止 NDI 擷取", additional_info={
                    "擷取模式": "NDI",
                    "擷取對象": str(type(self.ndi_capture))
                })
                logger.error(f"停止 NDI 時出錯: {e}")
    
    def save_current_config(self):
        """保存當前配置"""
        # 獲取當前擷取模式
        mode_data = self.capture_mode_combo.currentData()
        if mode_data and mode_data.startswith("bettercam_"):
            capture_mode = "bettercam"
            bettercam_mode = mode_data.split("_")[1]
        elif mode_data:
            capture_mode = mode_data
            bettercam_mode = "cpu"
        else:
            capture_mode = "udp"
            bettercam_mode = "cpu"
        
        config_data = {
            "capture_mode": capture_mode,
            "bettercam_mode": bettercam_mode,
            "udp_ip": self.ip_input.text(),
            "udp_port": self.port_input.value(),
            "target_fps": self.udp_fps_input.value(),
            "tcp_ip": self.tcp_ip_input.text() if hasattr(self, 'tcp_ip_input') else "192.168.0.1",
            "tcp_port": self.tcp_port_input.value() if hasattr(self, 'tcp_port_input') else 1234,
            "tcp_fps": self.tcp_fps_input.value() if hasattr(self, 'tcp_fps_input') else 60,
            "tcp_server_mode": self.tcp_server_mode_checkbox.isChecked() if hasattr(self, 'tcp_server_mode_checkbox') else False,
            "srt_ip": self.srt_ip_input.text() if hasattr(self, 'srt_ip_input') else "192.168.0.1",
            "srt_port": self.srt_port_input.value() if hasattr(self, 'srt_port_input') else 1234,
            "srt_fps": self.srt_fps_input.value() if hasattr(self, 'srt_fps_input') else 60,
            "srt_listener_mode": self.srt_listener_mode_checkbox.isChecked() if hasattr(self, 'srt_listener_mode_checkbox') else False,
            "capture_device_index": self.capture_device_index_input.value(),
            "capture_width": self.capture_width_input.value(),
            "capture_height": self.capture_height_input.value(),
            "capture_fps": self.capture_fps_input.value(),
            "capture_range_x": self.capture_range_x_input.value(),
            "capture_range_y": self.capture_range_y_input.value(),
            "capture_offset_x": self.capture_offset_x_input.value(),
            "capture_offset_y": self.capture_offset_y_input.value(),
            "mss_range_x": self.mss_range_x_input.value(),
            "mss_range_y": self.mss_range_y_input.value(),
            "mss_offset_x": self.mss_offset_x_input.value(),
            "mss_offset_y": self.mss_offset_y_input.value(),
            "mss_trigger_offset_x": self.mss_trigger_offset_x_input.value(),
            "mss_trigger_offset_y": self.mss_trigger_offset_y_input.value(),
            "bettercam_range_x": self.bettercam_range_x_input.value(),
            "bettercam_range_y": self.bettercam_range_y_input.value(),
            "bettercam_offset_x": self.bettercam_offset_x_input.value(),
            "bettercam_offset_y": self.bettercam_offset_y_input.value(),
            "bettercam_trigger_offset_x": self.bettercam_trigger_offset_x_input.value(),
            "bettercam_trigger_offset_y": self.bettercam_trigger_offset_y_input.value(),
            "bettercam_target_fps": self.bettercam_fps_input.value(),
            "dxgi_range_x": self.dxgi_range_x_input.value(),
            "dxgi_range_y": self.dxgi_range_y_input.value(),
            "dxgi_offset_x": self.dxgi_offset_x_input.value(),
            "dxgi_offset_y": self.dxgi_offset_y_input.value(),
            "dxgi_trigger_offset_x": self.dxgi_trigger_offset_x_input.value(),
            "dxgi_trigger_offset_y": self.dxgi_trigger_offset_y_input.value(),
            "dxgi_target_fps": self.dxgi_fps_input.value(),
            "detection_mode": self.mode_button_group.checkedId(),
            "color_from_r": self.color_from_r.value(),
            "color_from_g": self.color_from_g.value(),
            "color_from_b": self.color_from_b.value(),
            "color_to_r": self.color_to_r.value(),
            "color_to_g": self.color_to_g.value(),
            "color_to_b": self.color_to_b.value(),
            "target_color_r": self.target_color_r.value(),
            "target_color_g": self.target_color_g.value(),
            "target_color_b": self.target_color_b.value(),
            "tolerance": self.tolerance_input.value(),
            "press_delay_min": self.press_delay_min_input.value(),
            "press_delay_max": self.press_delay_max_input.value(),
            "release_delay_min": self.release_delay_min_input.value(),
            "release_delay_max": self.release_delay_max_input.value(),
            "trigger_cooldown_min": self.cooldown_min_input.value(),
            "trigger_cooldown_max": self.cooldown_max_input.value(),
            "detection_size": self.detection_size_input.value()
        }
        if self.config_manager.save(config_data):
            self.log(t("config_saved", "✓ 配置已保存到 config.json"))
        else:
            self.log(t("config_save_failed", "✗ 配置保存失敗"), error=True)
    
    def reload_config(self):
        """重新載入配置"""
        self.config_manager.load()
        self.load_settings_from_config()
        self.log(t("config_reloaded", "✓ 配置已重新載入"))
    
    def on_language_changed(self, index):
        """語言切換處理"""
        lang_code = self.language_combo.itemData(index)
        if lang_code and self.language_manager.load_language(lang_code):
            # 保存語言設置
            self.config_manager.set("language", lang_code)
            self.config_manager.save()
            
            # 更新所有 UI 文字
            self.update_ui_texts()
            self.update_window_title()
            
            self.log(t("language_changed", f"語言已切換為: {self.language_combo.itemText(index)}"))
    
    def update_window_title(self):
        """更新窗口標題"""
        base_title = t("window_title", "顏色檢測自動點擊程式 v1.2")
        self.setWindowTitle(f"{base_title}  -  made by asenyeroao")
    
    def update_ui_texts(self):
        """更新所有 UI 文字"""
        # 頂部按鈕
        self.connect_btn.setText(t("connect_obs", "連接 OBS"))
        self.start_btn.setText(t("start_detection", "啟動檢測"))
        self.save_config_btn.setText(t("save_config", "保存配置"))
        self.load_config_btn.setText(t("reload_config", "重載配置"))
        
        # 設置面板標題
        if hasattr(self, 'udp_settings_group'):
            self.udp_settings_group.setTitle(t("udp_settings", "UDP 設置"))
        if hasattr(self, 'capture_card_settings_group'):
            self.capture_card_settings_group.setTitle(t("capture_card_settings", "Capture Card 設置"))
        if hasattr(self, 'mss_settings_group'):
            self.mss_settings_group.setTitle(t("mss_settings", "MSS 設置"))
        if hasattr(self, 'bettercam_settings_group'):
            self.bettercam_settings_group.setTitle(t("bettercam_settings", "BetterCam 設置"))
        if hasattr(self, 'dxgi_settings_group'):
            self.dxgi_settings_group.setTitle(t("dxgi_settings", "DXGI 設置"))
        if hasattr(self, 'ndi_settings_group'):
            self.ndi_settings_group.setTitle(t("ndi_settings", "NDI 設置"))
        
        # 更新 FPS 顯示標籤
        if hasattr(self, 'fps_label'):
            self.fps_label.setText(t("ui_fps_display", "UI FPS: {ui_fps:.1f} | 擷取FPS: {capture_fps:.1f}").format(
                ui_fps=self.ui_fps,
                capture_fps=self.capture_fps
            ))
        
        # 更新擷取模式選項
        if hasattr(self, 'capture_mode_combo'):
            current_data = self.capture_mode_combo.currentData()
            self.capture_mode_combo.clear()
            self.capture_mode_combo.addItem(t("udp", "UDP"), "udp")
            if TCP_AVAILABLE:
                self.capture_mode_combo.addItem(t("tcp", "TCP"), "tcp")
            else:
                self.capture_mode_combo.addItem(t("tcp", "TCP") + " " + t("tcp_not_installed", "[未安裝]"), "tcp")
            if SRT_AVAILABLE:
                self.capture_mode_combo.addItem(t("srt", "SRT"), "srt")
            else:
                self.capture_mode_combo.addItem(t("srt", "SRT") + " " + t("srt_not_installed", "[未安裝]"), "srt")
            self.capture_mode_combo.addItem(t("capture_card", "Capture Card"), "capture_card")
            if BETTERCAM_AVAILABLE:
                self.capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)"), "bettercam_cpu")
                self.capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)"), "bettercam_gpu")
            else:
                self.capture_mode_combo.addItem(t("bettercam_cpu", "BetterCam (CPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_cpu")
                self.capture_mode_combo.addItem(t("bettercam_gpu", "BetterCam (GPU)") + " " + t("bettercam_not_installed", "[未安裝]"), "bettercam_gpu")
            if MSS_AVAILABLE:
                self.capture_mode_combo.addItem(t("mss", "MSS"), "mss")
            else:
                self.capture_mode_combo.addItem(t("mss", "MSS") + " " + t("mss_not_installed", "[未安裝]"), "mss")
            if DXGI_AVAILABLE:
                self.capture_mode_combo.addItem(t("dxgi", "DXGI"), "dxgi")
            else:
                self.capture_mode_combo.addItem(t("dxgi", "DXGI") + " " + t("dxgi_not_installed", "[未安裝]"), "dxgi")
            if NDI_AVAILABLE:
                self.capture_mode_combo.addItem(t("ndi", "OBS NDI"), "ndi")
            else:
                self.capture_mode_combo.addItem(t("ndi", "OBS NDI") + " " + t("ndi_not_installed", "[未安裝]"), "ndi")
            # 恢復之前的選擇
            if current_data:
                index = self.capture_mode_combo.findData(current_data)
                if index >= 0:
                    self.capture_mode_combo.setCurrentIndex(index)
        
        # 更新檢測模式
        if hasattr(self, 'mode1_radio'):
            self.mode1_radio.setText(t("mode_1", "模式 1 (變色)"))
            self.mode2_radio.setText(t("mode_2", "模式 2 (單色)"))
        
        # 更新按鈕文字
        if hasattr(self, 'move_test_btn'):
            self.move_test_btn.setText(t("test_move", "測試移動"))
            self.click_test_btn.setText(t("test_click", "測試點擊"))
            self.switch_4m_btn.setText(t("switch_4m", "切換 4M 波特率"))
        
        # 更新 CheckBox 文字
        if hasattr(self, 'debug_window_checkbox'):
            self.debug_window_checkbox.setText(t("enable_debug_window", "開啟即時畫面預覽 (調試窗口)"))
            self.always_on_top_checkbox.setText(t("always_on_top", "窗口置頂"))
            self.show_text_info_checkbox.setText(t("show_params", "顯示參數"))
        
        # 更新調試工具中的 CheckBox
        if hasattr(self, 'info_fps_checkbox'):
            self.info_fps_checkbox.setText(t("fps_info", "FPS"))
            self.info_resolution_checkbox.setText(t("resolution_info", "解析度"))
            self.info_detection_size_checkbox.setText(t("detection_area_info", "區域大小"))
            self.info_state_checkbox.setText(t("detection_state_info", "檢測狀態"))
            self.info_hotkeys_checkbox.setText(t("hotkeys_info", "快捷鍵"))
        
        # 更新系統狀態標題
        if hasattr(self, 'detection_status_label'):
            if not self.is_running:
                self.detection_status_label.setText(t("not_started", "未啟動"))
        
        # 更新滑鼠狀態標題
        if hasattr(self, 'mouse_status_label'):
            if not mouse_module.is_connected:
                self.mouse_status_label.setText(t("not_connected", "未連接"))
        
        # 更新連接按鈕文字（根據當前模式）
        if hasattr(self, 'capture_mode_combo'):
            mode_data = self.capture_mode_combo.currentData()
            if mode_data == "udp":
                if hasattr(self, 'udp_receiver') and self.udp_receiver and self.udp_receiver.is_connected:
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                else:
                    self.connect_btn.setText(t("connect_obs", "連接 OBS"))
            elif mode_data == "tcp":
                if hasattr(self, 'tcp_receiver') and self.tcp_receiver and self.tcp_receiver.is_connected:
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                else:
                    self.connect_btn.setText(t("connect_obs", "連接 OBS"))
            elif mode_data == "srt":
                if hasattr(self, 'srt_receiver') and self.srt_receiver and self.srt_receiver.is_connected:
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                else:
                    self.connect_btn.setText(t("connect_obs", "連接 OBS"))
            else:
                is_connected = False
                if mode_data == "capture_card" and hasattr(self, 'capture_card_camera') and self.capture_card_camera:
                    is_connected = self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
                elif mode_data and mode_data.startswith("bettercam") and hasattr(self, 'bettercam_camera') and self.bettercam_camera:
                    is_connected = self.bettercam_camera.running
                elif mode_data == "mss" and hasattr(self, 'mss_capture') and self.mss_capture:
                    is_connected = self.mss_capture.running
                
                if is_connected:
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                else:
                    self.connect_btn.setText(t("connect", "連接"))
        
        # 更新所有標籤文字（需要遍歷所有 QLabel）
        self._update_all_labels()
    
    def _update_all_labels(self):
        """更新所有表單標籤和其他標籤的文字"""
        # 更新系統狀態標籤
        if hasattr(self, 'detection_status_label'):
            if not self.is_running:
                self.detection_status_label.setText(t("not_started", "未啟動"))
        
        if hasattr(self, 'stats_label'):
            mode_data = self.capture_mode_combo.currentData() if hasattr(self, 'capture_mode_combo') else None
            is_connected = False
            if mode_data == "udp":
                is_connected = hasattr(self, 'udp_receiver') and self.udp_receiver and self.udp_receiver.is_connected
            elif mode_data == "tcp":
                is_connected = hasattr(self, 'tcp_receiver') and self.tcp_receiver and self.tcp_receiver.is_connected
            elif mode_data == "srt":
                is_connected = hasattr(self, 'srt_receiver') and self.srt_receiver and self.srt_receiver.is_connected
            
            if not is_connected and (mode_data == "udp" or mode_data == "tcp" or mode_data == "srt"):
                if not hasattr(self, 'bettercam_camera') or not self.bettercam_camera or not self.bettercam_camera.running:
                    if not hasattr(self, 'mss_capture') or not self.mss_capture or not self.mss_capture.running:
                        if not hasattr(self, 'capture_card_camera') or not self.capture_card_camera:
                            self.stats_label.setText(t("waiting_for_data", "等待畫面數據..."))
        
        if hasattr(self, 'cooldown_label'):
            self.cooldown_label.setText(t("ready", "準備就緒"))
        
        # 更新擷取模式標籤
        if hasattr(self, 'capture_mode_label'):
            self.capture_mode_label.setText(t("capture_mode", "擷取模式") + ":")
        
        # 更新檢測模式標籤
        if hasattr(self, 'detection_mode_label'):
            self.detection_mode_label.setText(t("detection_mode", "檢測模式") + ":")
    
    def on_mode_changed(self):
        """模式切換處理"""
        mode = self.mode_button_group.checkedId()
        self.mode1_group.setVisible(mode == 1)
        self.mode2_group.setVisible(mode == 2)
        self.color_detector.set_mode(mode)
        self.log(t("mode_switched", f"切換到模式 {mode}"))
    
    def toggle_connection(self):
        """切換擷取連接狀態"""
        mode_data = self.capture_mode_combo.currentData()
        if not mode_data:
            return
        
        # 解析模式
        if mode_data.startswith("bettercam_"):
            mode = "bettercam"
            bettercam_mode = mode_data.split("_")[1]
        else:
            mode = mode_data
            bettercam_mode = "cpu"
        
        is_connected = False
        if mode == "udp":
            is_connected = self.udp_receiver is not None and self.udp_receiver.is_connected
        elif mode == "capture_card":
            is_connected = self.capture_card_camera is not None and self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
        elif mode == "bettercam":
            is_connected = self.bettercam_camera is not None and self.bettercam_camera.running
        elif mode == "mss":
            is_connected = self.mss_capture is not None and self.mss_capture.running
        elif mode == "dxgi":
            is_connected = self.dxgi_capture is not None and self.dxgi_capture.running
        elif mode == "ndi":
            is_connected = self.ndi_capture is not None and self.ndi_capture.is_connected()
        elif mode == "tcp":
            is_connected = self.tcp_receiver is not None and self.tcp_receiver.is_connected
        elif mode == "srt":
            is_connected = self.srt_receiver is not None and self.srt_receiver.is_connected
        
        if not is_connected:
            # 連接
            if mode == "udp":
                ip = self.ip_input.text()
                port = self.port_input.value()
                fps = self.udp_fps_input.value()
                
                self.log(t("connecting_to_udp", "正在連接到 UDP {ip}:{port}...").format(ip=ip, port=port))
                try:
                    self.udp_receiver = OBS_UDP_Receiver(ip, port, fps, max_workers=4)
                    self.udp_receiver.set_frame_callback(self.on_frame_received)
                    
                    if self.udp_receiver.connect():
                        self.log(t("udp_connected_success", "✓ 成功連接到 OBS UDP 流"))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("waiting_for_frame_data", "等待畫面數據..."))
                        self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        QTimer.singleShot(100, self._update_connection_info)
                    else:
                        self.log(t("connection_failed", "✗ 連接失敗"), error=True)
                        self.udp_receiver = None
                        self._update_connection_info()
                except Exception as e:
                    log_exception(e, context="UDP 連接", additional_info={
                        "IP": self.ip_input.text(),
                        "端口": self.port_input.value(),
                        "目標 FPS": self.udp_fps_input.value()
                    })
                    self.log(t("connection_failed_error", "✗ 連接失敗: {error}").format(error=str(e)), error=True)
                    self.udp_receiver = None
            
            elif mode == "tcp":
                if not TCP_AVAILABLE:
                    self.log(t("tcp_not_installed", "✗ TCP 模組未安裝"), error=True)
                    return
                
                ip = self.tcp_ip_input.text()
                port = self.tcp_port_input.value()
                fps = self.tcp_fps_input.value()
                is_server = self.tcp_server_mode_checkbox.isChecked()
                
                self.log(t("connecting_to_tcp", "正在連接到 TCP {ip}:{port}...").format(ip=ip, port=port))
                try:
                    self.tcp_receiver = OBS_TCP_Receiver(ip, port, fps, is_server=is_server, max_workers=4)
                    self.tcp_receiver.set_frame_callback(self.on_frame_received)
                    
                    if self.tcp_receiver.connect():
                        self.log(t("tcp_connected_success", "✓ 成功連接到 OBS TCP 流"))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("waiting_for_frame_data", "等待畫面數據..."))
                        self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        QTimer.singleShot(100, self._update_connection_info)
                    else:
                        self.log(t("connection_failed", "✗ 連接失敗"), error=True)
                        self.tcp_receiver = None
                        self._update_connection_info()
                except Exception as e:
                    log_exception(e, context="TCP 連接", additional_info={
                        "IP": self.tcp_ip_input.text(),
                        "端口": self.tcp_port_input.value(),
                        "目標 FPS": self.tcp_fps_input.value(),
                        "伺服器模式": self.tcp_server_mode_checkbox.isChecked()
                    })
                    self.log(t("connection_failed_error", "✗ 連接失敗: {error}").format(error=str(e)), error=True)
                    self.tcp_receiver = None
            
            elif mode == "srt":
                if not SRT_AVAILABLE:
                    self.log(t("srt_not_installed", "✗ SRT 模組未安裝"), error=True)
                    return
                
                ip = self.srt_ip_input.text()
                port = self.srt_port_input.value()
                fps = self.srt_fps_input.value()
                is_listener = self.srt_listener_mode_checkbox.isChecked()
                
                self.log(t("connecting_to_srt", "正在連接到 SRT {ip}:{port}...").format(ip=ip, port=port))
                try:
                    self.srt_receiver = OBS_SRT_Receiver(ip, port, fps, is_listener=is_listener, max_workers=4)
                    self.srt_receiver.set_frame_callback(self.on_frame_received)
                    
                    if self.srt_receiver.connect():
                        self.log(t("srt_connected_success", "✓ 成功連接到 OBS SRT 流"))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("waiting_for_frame_data", "等待畫面數據..."))
                        self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        QTimer.singleShot(100, self._update_connection_info)
                    else:
                        self.log(t("connection_failed", "✗ 連接失敗"), error=True)
                        self.srt_receiver = None
                        self._update_connection_info()
                except Exception as e:
                    log_exception(e, context="SRT 連接", additional_info={
                        "IP": self.srt_ip_input.text(),
                        "端口": self.srt_port_input.value(),
                        "目標 FPS": self.srt_fps_input.value(),
                        "監聽模式": self.srt_listener_mode_checkbox.isChecked()
                    })
                    self.log(t("connection_failed_error", "✗ 連接失敗: {error}").format(error=str(e)), error=True)
                    self.srt_receiver = None
    
            elif mode == "capture_card":
                self.log(t("connecting_capture_card", "正在連接 Capture Card..."))
                try:
                    # 更新config對象
                    self.config_manager.set("capture_device_index", self.capture_device_index_input.value())
                    self.config_manager.set("capture_width", self.capture_width_input.value())
                    self.config_manager.set("capture_height", self.capture_height_input.value())
                    self.config_manager.set("capture_fps", self.capture_fps_input.value())
                    self.config_manager.set("capture_range_x", self.capture_range_x_input.value())
                    self.config_manager.set("capture_range_y", self.capture_range_y_input.value())
                    self.config_manager.set("capture_offset_x", self.capture_offset_x_input.value())
                    self.config_manager.set("capture_offset_y", self.capture_offset_y_input.value())
                    
                    # 創建一個臨時配置對象
                    class TempConfig:
                        pass
                    temp_config = TempConfig()
                    for key in ["capture_device_index", "capture_width", "capture_height", "capture_fps",
                               "capture_range_x", "capture_range_y", "capture_offset_x", "capture_offset_y",
                               "region_size"]:
                        setattr(temp_config, key, self.config_manager.get(key, 0))
                    
                    self.capture_card_camera = create_capture_card_camera(temp_config)
                    self.log(t("capture_card_connected", "✓ 成功連接到 Capture Card"))
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                    self.connect_btn.setStyleSheet("background-color: #ff5555;")
                    self.start_btn.setEnabled(True)
                    self.stats_label.setText(t("capture_card_connected", "Capture Card 已連接"))
                    # 使用線程安全的方式重置計數器
                    if hasattr(self, '_frame_count_lock'):
                        with self._frame_count_lock:
                            self.frame_count = 0
                    else:
                        self.frame_count = 0
                    self.frame_count_start_time = time.time()
                    # 啟動幀獲取線程
                    self._start_capture_card_thread()
                except Exception as e:
                    log_exception(e, context="Capture Card 連接", additional_info={
                        "設備索引": self.capture_device_index_input.value(),
                        "寬度": self.capture_width_input.value(),
                        "高度": self.capture_height_input.value(),
                        "FPS": self.capture_fps_input.value()
                    })
                    self.log(t("capture_card_connection_failed", "✗ Capture Card 連接失敗: {error}").format(error=str(e)), error=True)
                    self.capture_card_camera = None
    
            elif mode == "bettercam":
                if not BETTERCAM_AVAILABLE:
                    self.log(t("bettercam_not_installed", "✗ BetterCam 未安裝，請先安裝: pip install bettercam"), error=True)
                    return
                
                self.log(t("starting_bettercam", "正在啟動 BetterCam ({mode})...").format(mode=bettercam_mode.upper()))
                try:
                    # 更新config對象
                    self.config_manager.set("bettercam_range_x", self.bettercam_range_x_input.value())
                    self.config_manager.set("bettercam_range_y", self.bettercam_range_y_input.value())
                    self.config_manager.set("bettercam_offset_x", self.bettercam_offset_x_input.value())
                    self.config_manager.set("bettercam_offset_y", self.bettercam_offset_y_input.value())
                    self.config_manager.set("bettercam_trigger_offset_x", self.bettercam_trigger_offset_x_input.value())
                    self.config_manager.set("bettercam_trigger_offset_y", self.bettercam_trigger_offset_y_input.value())
                    
                    # 創建一個臨時配置對象
                    class TempConfig:
                        pass
                    temp_config = TempConfig()
                    for key in ["bettercam_range_x", "bettercam_range_y", "bettercam_offset_x", "bettercam_offset_y",
                               "bettercam_trigger_offset_x", "bettercam_trigger_offset_y"]:
                        setattr(temp_config, key, self.config_manager.get(key, 0))
                    
                    # 獲取屏幕分辨率（如果配置中沒有，使用 Windows API）
                    screen_width = self.config_manager.get("screen_width", 0)
                    screen_height = self.config_manager.get("screen_height", 0)
                    if screen_width <= 0 or screen_height <= 0:
                        try:
                            import ctypes
                            user32 = ctypes.windll.user32
                            screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                            screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                        except:
                            screen_width = 1920
                            screen_height = 1080
                    setattr(temp_config, "screen_width", screen_width)
                    setattr(temp_config, "screen_height", screen_height)
                    
                    use_gpu = (bettercam_mode == "gpu")
                    # 讀取目標 FPS 設置
                    target_fps = self.config_manager.get("bettercam_target_fps", 0)
                    self.bettercam_camera = create_bettercam_capture(temp_config, device_idx=0, output_idx=0, use_gpu=use_gpu, target_fps=target_fps)
                    
                    if self.bettercam_camera.start():
                        self.log(t("bettercam_started", "✓ BetterCam ({mode}) 已啟動").format(mode=bettercam_mode.upper()))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("bettercam_connected", "BetterCam 已連接"))
                        # 使用線程安全的方式重置計數器
                        if hasattr(self, '_frame_count_lock'):
                            with self._frame_count_lock:
                                self.frame_count = 0
                        else:
                            self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        # 啟動幀獲取線程
                        self._start_bettercam_thread()
                    else:
                        self.log(t("bettercam_start_failed", "✗ BetterCam 啟動失敗"), error=True)
                        self.bettercam_camera = None
                except Exception as e:
                    log_exception(e, context="BetterCam 啟動", additional_info={
                        "模式": bettercam_mode,
                        "範圍": f"{self.bettercam_range_x_input.value()}x{self.bettercam_range_y_input.value()}",
                        "偏移": f"({self.bettercam_offset_x_input.value()}, {self.bettercam_offset_y_input.value()})"
                    })
                    self.log(t("bettercam_start_failed", "✗ BetterCam 啟動失敗: {error}").format(error=str(e)), error=True)
                    self.bettercam_camera = None
                    
            elif mode == "mss":
                if not MSS_AVAILABLE:
                    self.log(t("mss_not_installed_msg", "✗ MSS 未安裝，請先安裝: pip install mss"), error=True)
                    return
                
                self.log(t("starting_mss", "正在啟動 MSS..."))
                try:
                    # 更新config對象
                    self.config_manager.set("mss_range_x", self.mss_range_x_input.value())
                    self.config_manager.set("mss_range_y", self.mss_range_y_input.value())
                    self.config_manager.set("mss_offset_x", self.mss_offset_x_input.value())
                    self.config_manager.set("mss_offset_y", self.mss_offset_y_input.value())
                    self.config_manager.set("mss_trigger_offset_x", self.mss_trigger_offset_x_input.value())
                    self.config_manager.set("mss_trigger_offset_y", self.mss_trigger_offset_y_input.value())
                    
                    # 創建一個臨時配置對象
                    class TempConfig:
                        pass
                    temp_config = TempConfig()
                    for key in ["mss_range_x", "mss_range_y", "mss_offset_x", "mss_offset_y",
                               "mss_trigger_offset_x", "mss_trigger_offset_y"]:
                        setattr(temp_config, key, self.config_manager.get(key, 0))
                    
                    # MSS 會自動檢測屏幕分辨率，但我們也可以設置
                    # 如果配置中沒有，MSS 會自動從 monitor 獲取
                    screen_width = self.config_manager.get("screen_width", 0)
                    screen_height = self.config_manager.get("screen_height", 0)
                    if screen_width <= 0 or screen_height <= 0:
                        # MSS 會自動檢測，這裡設置為 0 讓它自動檢測
                        screen_width = 0
                        screen_height = 0
                    setattr(temp_config, "screen_width", screen_width)
                    setattr(temp_config, "screen_height", screen_height)
                    
                    self.mss_capture = create_mss_capture(temp_config)
                    self.log(t("mss_started", "✓ MSS 已啟動"))
                    self.connect_btn.setText(t("disconnect", "斷開連接"))
                    self.connect_btn.setStyleSheet("background-color: #ff5555;")
                    self.start_btn.setEnabled(True)
                    self.stats_label.setText(t("mss_connected", "MSS 已連接"))
                    # 使用線程安全的方式重置計數器
                    if hasattr(self, '_frame_count_lock'):
                        with self._frame_count_lock:
                            self.frame_count = 0
                    else:
                        self.frame_count = 0
                    self.frame_count_start_time = time.time()
                    # 啟動幀獲取線程
                    self._start_mss_thread()
                except Exception as e:
                    log_exception(e, context="MSS 啟動", additional_info={
                        "範圍": f"{self.mss_range_x_input.value()}x{self.mss_range_y_input.value()}",
                        "偏移": f"({self.mss_offset_x_input.value()}, {self.mss_offset_y_input.value()})"
                    })
                    self.log(t("mss_start_failed", "✗ MSS 啟動失敗: {error}").format(error=str(e)), error=True)
                    self.mss_capture = None
            elif mode == "dxgi":
                if not DXGI_AVAILABLE:
                    self.log(t("dxgi_not_installed_msg", "✗ DXGI (dxcam) 未安裝，請先安裝: pip install dxcam"), error=True)
                    return
                
                self.log(t("starting_dxgi", "正在啟動 DXGI..."))
                try:
                    # 更新config對象
                    self.config_manager.set("dxgi_range_x", self.dxgi_range_x_input.value())
                    self.config_manager.set("dxgi_range_y", self.dxgi_range_y_input.value())
                    self.config_manager.set("dxgi_offset_x", self.dxgi_offset_x_input.value())
                    self.config_manager.set("dxgi_offset_y", self.dxgi_offset_y_input.value())
                    self.config_manager.set("dxgi_trigger_offset_x", self.dxgi_trigger_offset_x_input.value())
                    self.config_manager.set("dxgi_trigger_offset_y", self.dxgi_trigger_offset_y_input.value())
                    self.config_manager.set("dxgi_target_fps", self.dxgi_fps_input.value())
                    
                    # 創建一個臨時配置對象
                    class TempConfig:
                        pass
                    temp_config = TempConfig()
                    for key in ["dxgi_range_x", "dxgi_range_y", "dxgi_offset_x", "dxgi_offset_y",
                               "dxgi_trigger_offset_x", "dxgi_trigger_offset_y", "dxgi_target_fps"]:
                        setattr(temp_config, key, self.config_manager.get(key, 0))
                    
                    # 獲取屏幕分辨率（如果配置中沒有，使用 Windows API）
                    screen_width = self.config_manager.get("screen_width", 0)
                    screen_height = self.config_manager.get("screen_height", 0)
                    if screen_width <= 0 or screen_height <= 0:
                        try:
                            import ctypes
                            user32 = ctypes.windll.user32
                            screen_width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
                            screen_height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
                        except:
                            screen_width = 1920
                            screen_height = 1080
                    setattr(temp_config, "screen_width", screen_width)
                    setattr(temp_config, "screen_height", screen_height)
                    
                    target_fps = self.dxgi_fps_input.value()
                    self.dxgi_capture = create_dxgi_capture(temp_config, output_idx=0, target_fps=target_fps)
                    
                    if self.dxgi_capture.start():
                        self.log(t("dxgi_started", "✓ DXGI 已啟動"))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("dxgi_connected", "DXGI 已連接"))
                        # 使用線程安全的方式重置計數器
                        if hasattr(self, '_frame_count_lock'):
                            with self._frame_count_lock:
                                self.frame_count = 0
                        else:
                            self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        # 啟動幀獲取線程
                        self._start_dxgi_thread()
                    else:
                        self.log(t("dxgi_start_failed", "✗ DXGI 啟動失敗"), error=True)
                        self.dxgi_capture = None
                except Exception as e:
                    log_exception(e, context="DXGI 啟動", additional_info={
                        "範圍": f"{self.dxgi_range_x_input.value()}x{self.dxgi_range_y_input.value()}",
                        "偏移": f"({self.dxgi_offset_x_input.value()}, {self.dxgi_offset_y_input.value()})",
                        "目標 FPS": self.dxgi_fps_input.value()
                    })
                    self.log(t("dxgi_start_failed", "✗ DXGI 啟動失敗: {error}").format(error=str(e)), error=True)
                    self.dxgi_capture = None
            
            elif mode == "ndi":
                if not NDI_AVAILABLE:
                    self.log(t("ndi_not_installed_msg", "✗ NDI 未安裝，請先安裝: pip install cyndilib"), error=True)
                    return
                
                self.log(t("starting_ndi", "正在啟動 NDI..."))
                try:
                    # 獲取 NDI 源選擇
                    source_name = self.ndi_source_combo.currentText().strip()
                    source_index = self.ndi_source_index_input.value()
                    
                    # 如果源名稱不為空，使用名稱；否則使用索引
                    if source_name:
                        source_name_or_index = source_name
                    else:
                        source_name_or_index = source_index
                    
                    # 創建臨時配置對象
                    class TempConfig:
                        pass
                    temp_config = TempConfig()
                    temp_config.ndi_width = 0  # 將由 NDI 自動檢測
                    temp_config.ndi_height = 0  # 將由 NDI 自動檢測
                    
                    self.ndi_capture = create_ndi_capture(config=temp_config, source_name_or_index=source_name_or_index)
                    
                    if self.ndi_capture.start():
                        self.log(t("ndi_started", "✓ NDI 已啟動"))
                        self.connect_btn.setText(t("disconnect", "斷開連接"))
                        self.connect_btn.setStyleSheet("background-color: #ff5555;")
                        self.start_btn.setEnabled(True)
                        self.stats_label.setText(t("ndi_connected", "NDI 已連接"))
                        # 使用線程安全的方式重置計數器
                        if hasattr(self, '_frame_count_lock'):
                            with self._frame_count_lock:
                                self.frame_count = 0
                        else:
                            self.frame_count = 0
                        self.frame_count_start_time = time.time()
                        # 啟動幀獲取線程
                        self._start_ndi_thread()
                    else:
                        self.log(t("ndi_start_failed", "✗ NDI 啟動失敗，請檢查 NDI 源是否可用"), error=True)
                        self.ndi_capture = None
                except Exception as e:
                    log_exception(e, context="NDI 啟動", additional_info={
                        "源名稱": self.ndi_source_combo.currentText().strip(),
                        "源索引": self.ndi_source_index_input.value()
                    })
                    self.log(t("ndi_start_failed", "✗ NDI 啟動失敗: {error}").format(error=str(e)), error=True)
                    self.ndi_capture = None
        else:
            # 斷開
            self.log(t("disconnecting", "正在斷開連接..."))
            if self.is_running:
                self.toggle_detection()
            
            if mode == "udp" and self.udp_receiver:
                self.udp_receiver.disconnect()
                self.udp_receiver = None
            elif mode == "tcp" and self.tcp_receiver:
                self.tcp_receiver.disconnect()
                self.tcp_receiver = None
            elif mode == "srt" and self.srt_receiver:
                self.srt_receiver.disconnect()
                self.srt_receiver = None
            elif mode == "capture_card" and self.capture_card_camera:
                self.capture_card_camera.stop()
                self.capture_card_camera = None
            elif mode == "bettercam" and self.bettercam_camera:
                try:
                    self.bettercam_camera.stop()
                except Exception as e:
                    log_exception(e, context="關閉時停止 BetterCam", additional_info={
                        "擷取模式": "BetterCam"
                    })
                    logger.error(f"停止 BetterCam 時出錯: {e}")
                finally:
                    self.bettercam_camera = None
            elif mode == "mss" and self.mss_capture:
                self.mss_capture.stop()
                self.mss_capture = None
            elif mode == "dxgi" and self.dxgi_capture:
                try:
                    self.dxgi_capture.stop()
                except Exception as e:
                    log_exception(e, context="關閉時停止 DXGI", additional_info={
                        "擷取模式": "DXGI"
                    })
                    logger.error(f"停止 DXGI 時出錯: {e}")
                finally:
                    self.dxgi_capture = None
            elif mode == "ndi" and self.ndi_capture:
                try:
                    self.ndi_capture.stop()
                except Exception as e:
                    log_exception(e, context="關閉時停止 NDI", additional_info={
                        "擷取模式": "NDI"
                    })
                    logger.error(f"停止 NDI 時出錯: {e}")
                finally:
                    self.ndi_capture = None
            
            self.connect_btn.setText(t("connect", "連接"))
            self.connect_btn.setStyleSheet("")
            self.start_btn.setEnabled(False)
            self.stats_label.setText(t("disconnected_status", "已斷開連接"))
            self._update_connection_info()
    
    def toggle_debug_window(self, state):
        """切換調試窗口"""
        if state == Qt.Checked:
            # 開啟調試窗口
            mode_data = self.capture_mode_combo.currentData()
            is_connected = False
            
            if mode_data == "udp":
                is_connected = self.udp_receiver is not None and self.udp_receiver.is_connected
            elif mode_data == "capture_card":
                is_connected = self.capture_card_camera is not None and self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
            elif mode_data and mode_data.startswith("bettercam"):
                is_connected = self.bettercam_camera is not None and self.bettercam_camera.running
            elif mode_data == "mss":
                is_connected = self.mss_capture is not None and self.mss_capture.running
            elif mode_data == "dxgi":
                is_connected = self.dxgi_capture is not None and self.dxgi_capture.running
            elif mode_data == "ndi":
                is_connected = self.ndi_capture is not None and self.ndi_capture.is_connected()
            
            if not is_connected:
                self.log(t("please_connect_capture_first", "✗ 請先連接擷取源"), error=True)
                self.debug_window_checkbox.setChecked(False)
                return
            
            try:
                self.debug_window = DebugWindowManager.create_window("Color Detection Debug Window")
                
                # 應用設置
                self.debug_window.set_always_on_top(self.always_on_top_checkbox.isChecked())
                self.debug_window.show_info = self.show_text_info_checkbox.isChecked()
                
                # 應用詳細信息設置
                self.debug_window.set_info_item('fps', self.info_fps_checkbox.isChecked())
                self.debug_window.set_info_item('resolution', self.info_resolution_checkbox.isChecked())
                self.debug_window.set_info_item('detection_size', self.info_detection_size_checkbox.isChecked())
                self.debug_window.set_info_item('state', self.info_state_checkbox.isChecked())
                self.debug_window.set_info_item('hotkeys', self.info_hotkeys_checkbox.isChecked())
                
                self.debug_window.start()
                self.log("✓ 調試窗口已開啟")
            except Exception as e:
                self.log(f"✗ 無法開啟調試窗口: {e}", error=True)
                self.debug_window_checkbox.setChecked(False)
                self.debug_window = None
        else:
            # 關閉調試窗口
            if self.debug_window:
                try:
                    DebugWindowManager.destroy_window()
                    self.debug_window = None
                    self.log("調試窗口已關閉")
                except Exception as e:
                    self.log(f"關閉調試窗口時出錯: {e}", error=True)
    
    def toggle_always_on_top(self, state):
        """切換窗口置頂"""
        if self.debug_window:
            self.debug_window.set_always_on_top(state == Qt.Checked)
            status = "已啟用" if state == Qt.Checked else "已停用"
            self.log(f"窗口置頂 {status}")
    
    def toggle_text_info(self, state):
        """切換文字資訊顯示"""
        show_info = state == Qt.Checked
        
        # 切換詳細設置區域的可見性
        self.text_info_detail_widget.setVisible(show_info)
        
        if self.debug_window:
            self.debug_window.show_info = show_info
            status = "已顯示" if show_info else "已隱藏"
            self.log(f"文字資訊 {status}")
    
    def update_info_item(self, item: str, visible: bool):
        """更新信息項目的可見性"""
        if self.debug_window:
            self.debug_window.set_info_item(item, visible)
            item_names = {
                'fps': 'FPS',
                'resolution': '解析度',
                'detection_size': '檢測區域',
                'state': '檢測狀態',
                'hotkeys': '快捷鍵提示'
            }
            status = "顯示" if visible else "隱藏"
            self.log(f"{item_names.get(item, item)} {status}")
    
    def on_tolerance_changed(self, value):
        """顏色容差改變時"""
        self.log(f"顏色容差設置為: {value}")
        # 如果檢測正在運行，立即更新
        if self.is_running:
            self.color_detector.set_tolerance(value)
            self.log(f"✓ 已應用新的顏色容差")
    
    def on_press_delay_range_changed(self, min_val: int, max_val: int):
        """按下延遲範圍改變時"""
        self.log(f"按下延遲範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.click_controller.set_press_delay_range(min_val, max_val)
        # 保存配置
        self.config_manager.set("press_delay_min", min_val)
        self.config_manager.set("press_delay_max", max_val)
        self.config_manager.save()
        if self.is_running:
            self.log(f"✓ 已應用新的按下延遲範圍")
    
    def on_release_delay_range_changed(self, min_val: int, max_val: int):
        """釋放延遲範圍改變時"""
        self.log(f"釋放延遲範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.click_controller.set_release_delay_range(min_val, max_val)
        # 保存配置
        self.config_manager.set("release_delay_min", min_val)
        self.config_manager.set("release_delay_max", max_val)
        self.config_manager.save()
        if self.is_running:
            self.log(f"✓ 已應用新的釋放延遲範圍")
    
    def on_cooldown_range_changed(self, min_val: int, max_val: int):
        """觸發冷卻範圍改變時"""
        self.log(f"觸發冷卻範圍設置為: {min_val}~{max_val} ms")
        # 立即更新控制器
        self.click_controller.set_cooldown_range(min_val, max_val)
        # 保存配置
        self.config_manager.set("trigger_cooldown_min", min_val)
        self.config_manager.set("trigger_cooldown_max", max_val)
        self.config_manager.save()
        if self.is_running:
            self.log(f"✓ 已應用新的觸發冷卻範圍")
    
    def on_detection_size_changed(self, value):
        """檢測區域改變時"""
        self.log(f"檢測區域大小設置為: {value} px")
        # 立即更新檢測器
        self.color_detector.detection_size = value
        # 更新調試窗口
        if self.debug_window:
            self.debug_window.set_detection_size(value)
        # 如果檢測正在運行，通知用戶
        if self.is_running:
            self.log(f"✓ 已應用新的檢測區域大小")
    
    def on_mss_range_changed(self):
        """MSS 範圍或偏移改變時"""
        range_x = self.mss_range_x_input.value()
        range_y = self.mss_range_y_input.value()
        offset_x = self.mss_offset_x_input.value()
        offset_y = self.mss_offset_y_input.value()
        
        # 確保範圍至少為 1x1
        if range_x < 1:
            range_x = 1
            self.mss_range_x_input.setValue(1)
        if range_y < 1:
            range_y = 1
            self.mss_range_y_input.setValue(1)
        
        # 更新配置
        self.config_manager.set("mss_range_x", range_x)
        self.config_manager.set("mss_range_y", range_y)
        self.config_manager.set("mss_offset_x", offset_x)
        self.config_manager.set("mss_offset_y", offset_y)
        
        # 如果正在運行，MSS 會自動從 config 讀取，無需重啟
        # 更新 debug window 顯示並調整大小
        if self.debug_window and self.mss_capture:
            # 計算實際擷取區域
            screen_w = self.mss_capture.screen_width
            screen_h = self.mss_capture.screen_height
            capture_w = range_x
            capture_h = range_y
            center_x = screen_w // 2
            center_y = screen_h // 2
            left = center_x - capture_w // 2 + offset_x
            top = center_y - capture_h // 2 + offset_y
            
            # 設置擷取區域信息到 debug window 並調整窗口大小
            if hasattr(self.debug_window, 'set_capture_region'):
                self.debug_window.set_capture_region((left, top, left + capture_w, top + capture_h))
            if hasattr(self.debug_window, 'set_target_size'):
                self.debug_window.set_target_size((capture_w, capture_h))
        
        self.log(f"MSS 範圍: {range_x}x{range_y}, 偏移: ({offset_x}, {offset_y})")
    
    def on_bettercam_range_changed(self):
        """BetterCam 範圍或偏移改變時"""
        range_x = self.bettercam_range_x_input.value()
        range_y = self.bettercam_range_y_input.value()
        offset_x = self.bettercam_offset_x_input.value()
        offset_y = self.bettercam_offset_y_input.value()
        
        # 確保範圍至少為 1x1
        if range_x < 1:
            range_x = 1
            self.bettercam_range_x_input.setValue(1)
        if range_y < 1:
            range_y = 1
            self.bettercam_range_y_input.setValue(1)
        
        # 更新配置
        self.config_manager.set("bettercam_range_x", range_x)
        self.config_manager.set("bettercam_range_y", range_y)
        self.config_manager.set("bettercam_offset_x", offset_x)
        self.config_manager.set("bettercam_offset_y", offset_y)
        
        # 如果正在運行，需要重新啟動 BetterCam
        if self.bettercam_camera and self.bettercam_camera.running:
            self.log("重新啟動 BetterCam 以應用新的範圍設置...")
            if self.bettercam_camera.restart():
                self.log("✓ BetterCam 已重新啟動")
            else:
                self.log("✗ BetterCam 重新啟動失敗", error=True)
        
        # 更新 debug window 顯示並調整大小
        if self.debug_window and self.bettercam_camera:
            # 計算實際擷取區域
            screen_w = self.bettercam_camera.screen_width
            screen_h = self.bettercam_camera.screen_height
            capture_w = range_x
            capture_h = range_y
            center_x = screen_w // 2
            center_y = screen_h // 2
            left = center_x - capture_w // 2 + offset_x
            top = center_y - capture_h // 2 + offset_y
            
            # 設置擷取區域信息到 debug window 並調整窗口大小
            if hasattr(self.debug_window, 'set_capture_region'):
                self.debug_window.set_capture_region((left, top, left + capture_w, top + capture_h))
            if hasattr(self.debug_window, 'set_target_size'):
                self.debug_window.set_target_size((capture_w, capture_h))
        
        self.log(f"BetterCam 範圍: {range_x}x{range_y}, 偏移: ({offset_x}, {offset_y})")
    
    def on_dxgi_range_changed(self):
        """DXGI 範圍或偏移改變時的處理"""
        # 更新配置
        self.config_manager.set("dxgi_range_x", self.dxgi_range_x_input.value())
        self.config_manager.set("dxgi_range_y", self.dxgi_range_y_input.value())
        self.config_manager.set("dxgi_offset_x", self.dxgi_offset_x_input.value())
        self.config_manager.set("dxgi_offset_y", self.dxgi_offset_y_input.value())
        
        # 如果 DXGI 正在運行，重新啟動以應用新設置
        if self.dxgi_capture and self.dxgi_capture.running:
            self.log("重新啟動 DXGI 以應用新的範圍設置...")
            if self.dxgi_capture.restart():
                self.log("✓ DXGI 已重新啟動")
            else:
                self.log("✗ DXGI 重新啟動失敗", error=True)
        
        # 更新調試窗口的擷取區域
        if self.debug_window and self.dxgi_capture:
            # 計算實際擷取區域
            range_x = self.dxgi_range_x_input.value()
            range_y = self.dxgi_range_y_input.value()
            offset_x = self.dxgi_offset_x_input.value()
            offset_y = self.dxgi_offset_y_input.value()
            
            # 獲取屏幕分辨率
            screen_width = self.config_manager.get("screen_width", 1920)
            screen_height = self.config_manager.get("screen_height", 1080)
            if screen_width <= 0 or screen_height <= 0:
                try:
                    import ctypes
                    user32 = ctypes.windll.user32
                    screen_width = user32.GetSystemMetrics(0)
                    screen_height = user32.GetSystemMetrics(1)
                except:
                    screen_width = 1920
                    screen_height = 1080
            
            # 計算擷取區域
            capture_width = max(1, range_x) if range_x > 0 else screen_width
            capture_height = max(1, range_y) if range_y > 0 else screen_height
            center_x = screen_width // 2
            center_y = screen_height // 2
            left = center_x - capture_width // 2 + offset_x
            top = center_y - capture_height // 2 + offset_y
            right = min(left + capture_width, screen_width)
            bottom = min(top + capture_height, screen_height)
            
            self.debug_window.set_capture_region((left, top, right, bottom))
    
    def on_dxgi_fps_changed(self):
        """DXGI FPS 改變時的處理"""
        # 更新配置
        self.config_manager.set("dxgi_target_fps", self.dxgi_fps_input.value())
        
        # 如果 DXGI 正在運行，重新啟動以應用新設置
        if self.dxgi_capture and self.dxgi_capture.running:
            self.log("重新啟動 DXGI 以應用新的 FPS 設置...")
            if self.dxgi_capture.restart():
                self.log("✓ DXGI 已重新啟動")
            else:
                self.log("✗ DXGI 重新啟動失敗", error=True)
    
    def _update_local_ip_display(self):
        """更新本機IP顯示"""
        try:
            local_ips = self._get_local_ips()
            if local_ips:
                ip_text = "\n".join(local_ips)
                self.local_ip_label.setText(ip_text)
            else:
                self.local_ip_label.setText("無法獲取")
        except Exception as e:
            logger.error(f"獲取本機IP失敗: {e}")
            self.local_ip_label.setText("獲取失敗")
    
    def _get_local_ips(self) -> list:
        """
        獲取本機所有IP地址
        
        Returns:
            IP地址列表
        """
        ips = []
        try:
            # 獲取主機名
            hostname = socket.gethostname()
            
            # 獲取主機名對應的IP
            try:
                host_ip = socket.gethostbyname(hostname)
                if host_ip and host_ip != "127.0.0.1":
                    ips.append(f"{hostname}: {host_ip}")
            except:
                pass
            
            # 獲取所有網絡接口的IP
            import platform
            if platform.system() == "Windows":
                # Windows 系統
                try:
                    import subprocess
                    result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk', errors='ignore')
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'IPv4' in line or 'IP Address' in line:
                            parts = line.split(':')
                            if len(parts) > 1:
                                ip = parts[-1].strip()
                                if ip and ip != "127.0.0.1" and not ip.startswith("169.254"):
                                    if ip not in [i.split(': ')[-1] if ': ' in i else i for i in ips]:
                                        ips.append(ip)
                except:
                    pass
            
            # 使用 socket 獲取所有接口
            try:
                # 連接到外部地址以獲取本機IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # 連接到一個不存在的地址，不會實際發送數據
                    s.connect(('8.8.8.8', 80))
                    local_ip = s.getsockname()[0]
                    if local_ip and local_ip not in ips:
                        ips.insert(0, local_ip)
                except:
                    pass
                finally:
                    s.close()
            except:
                pass
            
            # 如果沒有找到，至少顯示 localhost
            if not ips:
                ips.append("127.0.0.1 (localhost)")
            
        except Exception as e:
            logger.error(f"獲取本機IP時出錯: {e}")
            ips = ["無法獲取"]
        
        return ips[:5]  # 最多顯示5個IP
    
    def _update_connection_info(self):
        """更新連接信息顯示"""
        mode_data = self.capture_mode_combo.currentData() if hasattr(self, 'capture_mode_combo') else None
        
        # UDP 連接信息
        if mode_data == "udp" and self.udp_receiver and self.udp_receiver.is_connected and self.udp_receiver.socket:
            try:
                sockname = self.udp_receiver.socket.getsockname()
                bound_ip = sockname[0]
                bound_port = sockname[1]
                self.current_connection_ip = bound_ip
                self.current_connection_port = bound_port
                info_text = f"{bound_ip}:{bound_port}"
                if bound_ip == "0.0.0.0":
                    info_text += " (監聽所有接口)"
                self.connection_info_label.setText(info_text)
                self.connection_info_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
            except Exception as e:
                logger.error(f"獲取 UDP 連接信息失敗: {e}")
                self.connection_info_label.setText(t("get_connection_info_failed", "獲取失敗"))
                self.connection_info_label.setStyleSheet("color: #FF5555; font-size: 9pt;")
        elif mode_data == "udp":
            self.connection_info_label.setText(t("not_connected", "未連接"))
            self.connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        # TCP 連接信息
        elif mode_data == "tcp" and self.tcp_receiver and self.tcp_receiver.is_connected and self.tcp_receiver.socket:
            try:
                if self.tcp_receiver.is_server and self.tcp_receiver.socket:
                    sockname = self.tcp_receiver.socket.getsockname()
                    bound_ip = sockname[0]
                    bound_port = sockname[1]
                    info_text = f"{bound_ip}:{bound_port} (伺服器模式)"
                    if bound_ip == "0.0.0.0":
                        info_text += " (監聽所有接口)"
                elif self.tcp_receiver.socket:
                    sockname = self.tcp_receiver.socket.getsockname()
                    bound_ip = sockname[0]
                    bound_port = sockname[1]
                    info_text = f"{bound_ip}:{bound_port} (客戶端)"
                else:
                    info_text = f"{self.tcp_receiver.ip}:{self.tcp_receiver.port}"
                self.tcp_connection_info_label.setText(info_text)
                self.tcp_connection_info_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
            except Exception as e:
                logger.error(f"獲取 TCP 連接信息失敗: {e}")
                self.tcp_connection_info_label.setText(t("get_connection_info_failed", "獲取失敗"))
                self.tcp_connection_info_label.setStyleSheet("color: #FF5555; font-size: 9pt;")
        elif mode_data == "tcp":
            self.tcp_connection_info_label.setText(t("not_connected", "未連接"))
            self.tcp_connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        # SRT 連接信息
        elif mode_data == "srt" and self.srt_receiver and self.srt_receiver.is_connected and self.srt_receiver.socket:
            try:
                if self.srt_receiver.is_listener and self.srt_receiver.socket:
                    sockname = self.srt_receiver.socket.getsockname()
                    bound_ip = sockname[0]
                    bound_port = sockname[1]
                    info_text = f"{bound_ip}:{bound_port} (監聽模式)"
                    if bound_ip == "0.0.0.0":
                        info_text += " (監聽所有接口)"
                elif self.srt_receiver.socket:
                    sockname = self.srt_receiver.socket.getsockname()
                    bound_ip = sockname[0]
                    bound_port = sockname[1]
                    info_text = f"{bound_ip}:{bound_port} (呼叫模式)"
                else:
                    info_text = f"{self.srt_receiver.ip}:{self.srt_receiver.port}"
                self.srt_connection_info_label.setText(info_text)
                self.srt_connection_info_label.setStyleSheet("color: #00E5FF; font-size: 9pt;")
            except Exception as e:
                logger.error(f"獲取 SRT 連接信息失敗: {e}")
                self.srt_connection_info_label.setText(t("get_connection_info_failed", "獲取失敗"))
                self.srt_connection_info_label.setStyleSheet("color: #FF5555; font-size: 9pt;")
        elif mode_data == "srt":
            self.srt_connection_info_label.setText(t("not_connected", "未連接"))
            self.srt_connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        else:
            self.connection_info_label.setText(t("not_connected", "未連接"))
            self.connection_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
            self.current_connection_ip = None
            self.current_connection_port = None
    
    def _update_color_preview(self, color_type: str):
        """
        更新顏色預覽框
        
        Args:
            color_type: 'from', 'to', 'target'
        """
        if color_type == 'from':
            r = self.color_from_r.value()
            g = self.color_from_g.value()
            b = self.color_from_b.value()
            preview = self.color_from_preview
        elif color_type == 'to':
            r = self.color_to_r.value()
            g = self.color_to_g.value()
            b = self.color_to_b.value()
            preview = self.color_to_preview
        elif color_type == 'target':
            r = self.target_color_r.value()
            g = self.target_color_g.value()
            b = self.target_color_b.value()
            preview = self.target_color_preview
        else:
            return
        
        # 創建顏色樣式（注意：Qt 使用 RGB，而 OpenCV 使用 BGR）
        style = f"background-color: rgb({r}, {g}, {b}); border: 2px solid #555; border-radius: 4px;"
        preview.setStyleSheet(style)
    
    def _start_color_picker(self, color_type: str):
        """
        啟動顏色選擇器
        
        Args:
            color_type: 'from', 'to', 'target'
        """
        if not self.debug_window or not self.debug_window.is_running:
            self.log("請先開啟調試窗口", error=True)
            return
        
        self.color_picker_active = True
        self.color_picker_target = color_type
        
        # 更新預覽框樣式，顯示正在選擇
        if color_type == 'from':
            preview = self.color_from_preview
            name = "起始顏色"
        elif color_type == 'to':
            preview = self.color_to_preview
            name = "目標顏色"
        else:
            preview = self.target_color_preview
            name = "目標顏色"
        
        # 添加閃爍效果提示
        preview.setStyleSheet(
            preview.styleSheet() + 
            " border: 3px solid #00E5FF; animation: none;"
        )
        
        # 設置調試窗口的顏色選擇回調
        self.debug_window.set_color_picker_callback(self._on_color_picked)
        
        self.log(t("color_picker_started", "顏色選擇模式已啟動：請在調試窗口中點擊來選擇 {name}").format(name=name))
    
    def _on_color_picked(self, bgr_color: tuple):
        """
        顏色選擇回調（可能在非主線程中調用，需要使用 QTimer 確保在主線程執行）
        
        Args:
            bgr_color: OpenCV 格式的顏色 (B, G, R)
        """
        # 使用 QTimer.singleShot 確保在主線程執行
        QTimer.singleShot(0, lambda: self._on_color_picked_main_thread(bgr_color))
    
    def _on_color_picked_main_thread(self, bgr_color: tuple):
        """
        顏色選擇回調（主線程版本）
        
        Args:
            bgr_color: OpenCV 格式的顏色 (B, G, R)
        """
        if not self.color_picker_active or not self.color_picker_target:
            return
        
        # 轉換 BGR 到 RGB
        b, g, r = bgr_color
        
        # 保存目標類型用於更新預覽
        target_type = self.color_picker_target
        name = ""
        
        # 更新對應的 RGB 輸入框
        if self.color_picker_target == 'from':
            self.color_from_r.setValue(int(r))
            self.color_from_g.setValue(int(g))
            self.color_from_b.setValue(int(b))
            name = "起始顏色"
        elif self.color_picker_target == 'to':
            self.color_to_r.setValue(int(r))
            self.color_to_g.setValue(int(g))
            self.color_to_b.setValue(int(b))
            name = "目標顏色"
        else:
            self.target_color_r.setValue(int(r))
            self.target_color_g.setValue(int(g))
            self.target_color_b.setValue(int(b))
            name = "目標顏色"
        
        # 關閉顏色選擇模式
        self.color_picker_active = False
        self.color_picker_target = None
        
        # 清除調試窗口的回調
        if self.debug_window:
            self.debug_window.set_color_picker_callback(None)
        
        # 更新顏色預覽
        self._update_color_preview(target_type)
        
        self.log(f"✓ 已選擇 {name}: RGB({r}, {g}, {b})")
    
    def on_frame_received(self, frame):
        """
        幀接收回調（在後台線程中調用）
        將幀放入處理隊列，由異步線程處理
        """
        self._process_frame(frame)
    
    def _process_frame(self, frame):
        """
        處理接收到的幀（通用方法）
        優化：只負責快速將幀放入隊列，不進行其他處理，提升擷取線程性能
        """
        if frame is None:
            return
        
        # 使用線程安全的計數器（使用原子操作）
        # 創建專用的計數器鎖（如果不存在）
        if not hasattr(self, '_frame_count_lock'):
            self._frame_count_lock = threading.Lock()
        with self._frame_count_lock:
            self.frame_count += 1
        
        # 將幀放入處理隊列（如果隊列滿了，丟棄最舊的幀，保持低延遲）
        # 使用 frame.copy() 確保線程安全
        try:
            if self.frame_processing_queue.full():
                try:
                    self.frame_processing_queue.get_nowait()  # 丟棄最舊的幀
                except Empty:
                    pass
            # 只在隊列中存儲時複製，避免不必要的內存操作
            self.frame_processing_queue.put_nowait((frame.copy(), time.time()))
        except Exception as e:
            logger.debug(f"Frame queue error: {e}")
        
        # 更新顯示用幀（用於調試窗口和 UI 顯示）
        # 優化：只在需要時複製，減少內存開銷
        # 使用非阻塞方式更新，避免阻塞擷取線程
        try:
            with self.frame_lock:
                # 只在調試窗口開啟時才複製，否則直接引用（減少內存複製）
                if self.debug_window and self.debug_window.is_running:
                    self.current_display_frame = frame.copy()
                else:
                    self.current_display_frame = frame
        except:
            pass  # 如果鎖被佔用，跳過更新，不阻塞擷取線程
        
        # 如果調試窗口開啟，降低更新頻率以提升性能
        if self.debug_window and self.debug_window.is_running:
            # 使用簡單的計數器來控制更新頻率（每 N 幀更新一次）
            if not hasattr(self, '_debug_update_counter'):
                self._debug_update_counter = 0
            self._debug_update_counter += 1
            # 每 2 幀更新一次調試窗口（約 72 FPS 顯示，足夠流暢且不影響性能）
            if self._debug_update_counter >= 2:
                try:
                    self.debug_window.update_frame(frame)
                except:
                    pass  # 如果更新失敗，不阻塞擷取線程
                self._debug_update_counter = 0
    
    def _start_capture_card_thread(self):
        """啟動 Capture Card 幀獲取線程"""
        def capture_loop():
            while self.capture_card_camera and self.capture_card_camera.running:
                try:
                    frame = self.capture_card_camera.get_latest_frame()
                    if frame is not None and frame.size > 0:
                        # Capture Card 返回的是 BGR 格式，直接使用
                        self._process_frame(frame)
                    time.sleep(1.0 / self.capture_fps_input.value() if self.capture_fps_input.value() > 0 else 0.01)
                except Exception as e:
                    log_exception(e, context="Capture Card 擷取線程", additional_info={
                        "線程": "CaptureCardThread",
                        "相機運行狀態": self.capture_card_camera.running if self.capture_card_camera else False
                    })
                    logger.error(f"Capture Card error: {e}")
                    time.sleep(0.01)
        
        thread = threading.Thread(target=capture_loop, daemon=True, name="CaptureCardThread")
        thread.start()
    
    def _start_bettercam_thread(self):
        """啟動 BetterCam 幀獲取線程"""
        def capture_loop():
            # 只在第一次設置調試窗口區域
            debug_region_set = False
            while self.bettercam_camera and self.bettercam_camera.running:
                try:
                    frame = self.bettercam_camera.get_latest_frame()
                    if frame is not None and frame.size > 0:
                        # BetterCam 模組已經返回 BGR 格式
                        # 只在第一次或調試窗口開啟時更新區域信息（減少開銷）
                        if not debug_region_set and self.debug_window and self.bettercam_camera:
                            if hasattr(self.debug_window, 'set_capture_region'):
                                h, w = frame.shape[:2]
                                self.debug_window.set_capture_region((0, 0, w, h))
                                debug_region_set = True
                        self._process_frame(frame)
                    # 不添加延遲，讓 BetterCam 以最快速度獲取幀
                    # BetterCam 的 get_latest_frame() 會阻塞等待新幀，所以不需要額外延遲
                except Exception as e:
                    log_exception(e, context="BetterCam 擷取線程", additional_info={
                        "線程": "BetterCamThread",
                        "相機運行狀態": self.bettercam_camera.running if self.bettercam_camera else False
                    })
                    logger.error(f"BetterCam error: {e}")
                    time.sleep(0.01)  # 只在錯誤時稍作延遲
        
        thread = threading.Thread(target=capture_loop, daemon=True, name="BetterCamThread")
        thread.start()
    
    def _start_mss_thread(self):
        """啟動 MSS 幀獲取線程"""
        def capture_loop():
            while self.mss_capture and self.mss_capture.running:
                try:
                    frame = self.mss_capture.get_latest_frame()
                    if frame is not None and frame.size > 0:
                        # MSS 模組已經返回 BGR 格式
                        self._process_frame(frame)
                    # 移除延遲，讓 MSS 以最快速度獲取幀
                    # 如果隊列滿了，_process_frame 會自動丟棄舊幀，保持低延遲
                except Exception as e:
                    log_exception(e, context="MSS 擷取線程", additional_info={
                        "線程": "MSSThread",
                        "擷取運行狀態": self.mss_capture.running if self.mss_capture else False
                    })
                    logger.error(f"MSS error: {e}")
                    time.sleep(0.01)  # 只在錯誤時稍作延遲
        
        thread = threading.Thread(target=capture_loop, daemon=True, name="MSSThread")
        thread.start()
    
    def _start_dxgi_thread(self):
        """啟動 DXGI 幀獲取線程"""
        def capture_loop():
            # 只在第一次設置調試窗口區域
            debug_region_set = False
            while self.dxgi_capture and self.dxgi_capture.running:
                try:
                    frame = self.dxgi_capture.get_latest_frame()
                    if frame is not None and frame.size > 0:
                        # DXGI 模組已經返回 BGR 格式
                        # 只在第一次或調試窗口開啟時更新區域信息（減少開銷）
                        if not debug_region_set and self.debug_window and self.dxgi_capture:
                            if hasattr(self.debug_window, 'set_capture_region'):
                                h, w = frame.shape[:2]
                                self.debug_window.set_capture_region((0, 0, w, h))
                                debug_region_set = True
                        self._process_frame(frame)
                    # 不添加延遲，讓 DXGI 以最快速度獲取幀
                    # DXGI 的 get_latest_frame() 會阻塞等待新幀，所以不需要額外延遲
                except Exception as e:
                    log_exception(e, context="DXGI 擷取線程", additional_info={
                        "線程": "DXGIThread",
                        "擷取運行狀態": self.dxgi_capture.running if self.dxgi_capture else False
                    })
                    logger.error(f"DXGI error: {e}")
                    time.sleep(0.01)  # 只在錯誤時稍作延遲
        
        thread = threading.Thread(target=capture_loop, daemon=True, name="DXGIThread")
        thread.start()
    
    def _start_ndi_thread(self):
        """啟動 NDI 幀獲取線程"""
        def capture_loop():
            # 只在第一次設置調試窗口區域
            debug_region_set = False
            while self.ndi_capture and self.ndi_capture.is_connected():
                try:
                    frame = self.ndi_capture.get_latest_frame()
                    if frame is not None and frame.size > 0:
                        # NDI 模組已經返回 BGR 格式
                        # 只在第一次或調試窗口開啟時更新區域信息（減少開銷）
                        if not debug_region_set and self.debug_window and self.ndi_capture:
                            if hasattr(self.debug_window, 'set_capture_region'):
                                h, w = frame.shape[:2]
                                self.debug_window.set_capture_region((0, 0, w, h))
                                debug_region_set = True
                        self._process_frame(frame)
                    # 添加小延遲以避免過度佔用 CPU
                    time.sleep(0.001)  # 1ms 延遲
                except Exception as e:
                    log_exception(e, context="NDI 擷取線程", additional_info={
                        "線程": "NDIThread",
                        "連接狀態": self.ndi_capture.is_connected() if self.ndi_capture else False
                    })
                    logger.error(f"NDI error: {e}")
                    time.sleep(0.01)  # 只在錯誤時稍作延遲
        
        thread = threading.Thread(target=capture_loop, daemon=True, name="NDIThread")
        thread.start()
    
    def refresh_ndi_sources(self):
        """刷新 NDI 源列表"""
        if not NDI_AVAILABLE:
            self.log(t("ndi_not_installed_msg", "✗ NDI 未安裝，請先安裝: pip install cyndilib"), error=True)
            return
        
        try:
            # 如果已經有 NDI 接收器，使用它來獲取源列表
            if self.ndi_capture and self.ndi_capture.receiver:
                sources = self.ndi_capture.list_sources()
            else:
                # 創建臨時接收器來獲取源列表
                from capture.obs_ndi import NDI_Receiver
                temp_receiver = NDI_Receiver()
                sources = temp_receiver.list_sources(refresh=True)
                temp_receiver.disconnect()
            
            # 更新下拉框
            self.ndi_source_combo.clear()
            if sources:
                for source in sources:
                    self.ndi_source_combo.addItem(source)
                self.log(t("ndi_sources_refreshed", "✓ 已刷新 NDI 源列表，找到 {count} 個源").format(count=len(sources)))
            else:
                self.log(t("ndi_no_sources", "未找到可用的 NDI 源，請確保 NDI 源正在運行"), error=True)
        except Exception as e:
            self.log(t("ndi_refresh_failed", "✗ 刷新 NDI 源列表失敗: {error}").format(error=str(e)), error=True)
    
    def _frame_processor_loop(self):
        """
        異步幀處理循環（多線程並行處理）
        從隊列獲取幀，提交到檢測線程池進行並行處理
        多個線程並行處理，提升高 FPS 下的處理能力
        """
        thread_name = threading.current_thread().name
        logger.info(f"Frame processor loop started: {thread_name}")
        
        while True:
            try:
                # 從隊列獲取幀（非阻塞，快速獲取）
                try:
                    frame, receive_time = self.frame_processing_queue.get(timeout=0.01)
                except Empty:
                    continue
                
                # 如果檢測未啟動，跳過處理
                if not self.is_running:
                    continue
                
                # 提交到檢測線程池進行異步處理
                # 不等待結果，立即處理下一個幀
                self.detection_executor.submit(self._detect_frame_async, frame, receive_time)
                
            except Exception as e:
                log_exception(e, context=f"幀處理器錯誤 ({thread_name})", additional_info={
                    "線程名稱": thread_name,
                    "隊列大小": self.frame_processing_queue.qsize() if hasattr(self, 'frame_processing_queue') else "N/A"
                })
                logger.error(f"Frame processor error ({thread_name}): {e}", exc_info=True)
                time.sleep(0.001)  # 減少錯誤時的延遲
    
    def _detect_frame_async(self, frame: np.ndarray, receive_time: float):
        """
        異步顏色檢測（在線程池中執行）
        
        Args:
            frame: 要檢測的幀
            receive_time: 接收時間戳
        """
        try:
            with self.detection_lock:
                # 執行顏色檢測
                triggered, color_present = self.color_detector.detect(frame)
                
                # 獲取檢測狀態信息
                detection_info = {
                    'triggered': triggered,
                    'color_present': color_present,
                    'frame_time': receive_time,
                    'mode': self.color_detector.mode,
                    'state': self.color_detector.last_color_state if self.color_detector.mode == 1 else None
                }
                
                # 將結果放入結果隊列
                try:
                    if self.detection_result_queue.full():
                        try:
                            self.detection_result_queue.get_nowait()  # 丟棄最舊的結果
                        except Empty:
                            pass
                    self.detection_result_queue.put_nowait(detection_info)
                except Exception as e:
                    logger.debug(f"Result queue error: {e}")
                    
        except Exception as e:
            log_exception(e, context="顏色檢測錯誤", additional_info={
                "檢測模式": self.color_detector.mode if hasattr(self, 'color_detector') and self.color_detector else "N/A"
            })
            logger.error(f"Detection error: {e}", exc_info=True)
    
    def _result_processor_loop(self):
        """
        異步結果處理循環
        從結果隊列獲取檢測結果，觸發點擊等操作
        """
        logger.info("Result processor loop started")
        
        while True:
            try:
                # 從隊列獲取檢測結果
                try:
                    result = self.detection_result_queue.get(timeout=0.1)
                except Empty:
                    continue
                
                # 處理檢測結果
                if result['triggered']:
                    # 觸發點擊（異步執行）
                    if self.click_controller.can_trigger():
                        message = ""
                        if result['mode'] == 1:
                            message = "顏色變化: 紅色 -> 綠色"
                        else:
                            message = f"檢測到目標顏色"
                        
                        # 使用信號或直接調用（異步）
                        # 由於點擊已經是異步的，這裡可以直接調用
                        if self.click_controller.execute_click(self.mouse, blocking=False):
                            # 使用 QTimer 在主線程中更新 UI（線程安全）
                            QTimer.singleShot(0, lambda: self.log(f"✓ {message}"))
                        else:
                            if not mouse_module.is_connected:
                                QTimer.singleShot(0, lambda: self.log("滑鼠未連接，無法發送點擊", error=True))
                
            except Exception as e:
                log_exception(e, context="結果處理器錯誤", additional_info={
                    "結果隊列大小": self.detection_result_queue.qsize() if hasattr(self, 'detection_result_queue') else "N/A"
                })
                logger.error(f"Result processor error: {e}", exc_info=True)
                time.sleep(0.01)
    
    def test_move(self):
        """測試滑鼠移動"""
        if not mouse_module.is_connected:
            self.log("✗ 滑鼠未連接", error=True)
            return
        
        try:
            if self.mouse is None:
                self.mouse = Mouse()
            
            self.log("測試移動: (100, 100)")
            self.mouse.move(100, 100)
            self.log("✓ 移動命令已發送")
        except Exception as e:
            self.log(f"✗ 移動測試失敗: {e}", error=True)
    
    def test_click(self):
        """測試滑鼠點擊"""
        if not mouse_module.is_connected:
            self.log("✗ 滑鼠未連接", error=True)
            return
        
        try:
            if self.mouse is None:
                self.mouse = Mouse()
            
            self.log("開始點擊測試...")
            if self.click_controller.test_click(self.mouse):
                pass # Controller 已經有日誌了
            else:
                self.log(t("click_test_failed", "✗ 點擊測試失敗"), error=True)
        except Exception as e:
            self.log(t("click_test_error", "✗ 點擊測試異常: {error}").format(error=str(e)), error=True)
    
    def auto_connect_mouse(self):
        """自動連接 MAKCU 設備"""
        self.log(t("auto_connecting_makcu", "正在自動連接 MAKCU 設備..."))
        try:
            if self.mouse is None:
                self.mouse = Mouse()
            
            # 等待一小段時間讓連接完成
            QTimer.singleShot(200, self.check_mouse_connection)
        except Exception as e:
            self.log(t("auto_connect_failed", "✗ 自動連接失敗: {error}").format(error=str(e)), error=True)
    
    def check_mouse_connection(self):
        """檢查滑鼠連接狀態（延遲檢查）"""
        if mouse_module.is_connected:
            self.log(t("makcu_auto_connected", "✓ MAKCU 設備已自動連接"))
        else:
            self.log(t("makcu_not_found", "✗ 未找到 MAKCU 設備"), error=True)
    
    def switch_to_4m(self):
        """切換 MAKCU 到 4M 波特率"""
        from utils.mouse import switch_to_4m
        self.log("正在切換到 4M 波特率...")
        if switch_to_4m():
            self.log("✓ 成功切換到 4M 波特率")
        else:
            self.log("✗ 切換失敗或保持原波特率", error=True)
    
    def toggle_detection(self):
        """切換檢測狀態"""
        if not self.is_running:
            # 啟動檢測
            self.is_running = True
            self.start_btn.setText("停止檢測")
            # 讓樣式表處理顏色，不需要行內樣式，或者只設置特定屬性
            
            # 初始化滑鼠
            if self.mouse is None:
                self.mouse = Mouse()
            
            # 更新檢測器設置
            mode = self.mode_button_group.checkedId()
            self.color_detector.set_mode(mode)
            
            if mode == 1:
                r1, g1, b1 = self.color_from_r.value(), self.color_from_g.value(), self.color_from_b.value()
                r2, g2, b2 = self.color_to_r.value(), self.color_to_g.value(), self.color_to_b.value()
                self.color_detector.set_color_from(r1, g1, b1)
                self.color_detector.set_color_to(r2, g2, b2)
                self.log(f"啟動模式 1: RGB({r1},{g1},{b1}) -> RGB({r2},{g2},{b2})")
            else:
                r, g, b = self.target_color_r.value(), self.target_color_g.value(), self.target_color_b.value()
                self.color_detector.set_target_color(r, g, b)
                self.log(f"啟動模式 2: 檢測 RGB({r},{g},{b})")
            
            # 應用所有設置
            tolerance = self.tolerance_input.value()
            detection_size = self.detection_size_input.value()
            
            # 使用範圍設置（已經在回調中設置，這裡確保同步）
            press_delay_min = self.press_delay_min_input.value()
            press_delay_max = self.press_delay_max_input.value()
            release_delay_min = self.release_delay_min_input.value()
            release_delay_max = self.release_delay_max_input.value()
            cooldown_min = self.cooldown_min_input.value()
            cooldown_max = self.cooldown_max_input.value()
            
            self.color_detector.set_tolerance(tolerance)
            self.color_detector.detection_size = detection_size
            self.click_controller.set_press_delay_range(press_delay_min, press_delay_max)
            self.click_controller.set_release_delay_range(release_delay_min, release_delay_max)
            self.click_controller.set_cooldown_range(cooldown_min, cooldown_max)
            self.color_detector.enabled = True
            
            # 記錄設置
            self.log(f"檢測設置: 容差={tolerance}, 區域={detection_size}px")
            self.log(f"點擊設置: 按下延遲={press_delay_min}~{press_delay_max}ms, 釋放延遲={release_delay_min}~{release_delay_max}ms, 冷卻={cooldown_min}~{cooldown_max}ms")
            
            # 連接信號
            self.color_detector.color_changed.connect(self.on_color_detected)
            
        else:
            # 停止檢測
            self.is_running = False
            self.start_btn.setText("啟動檢測")
            # 恢復預設樣式
            
            self.color_detector.enabled = False
            
            try:
                self.color_detector.color_changed.disconnect(self.on_color_detected)
            except:
                pass
            
            self.log(t("detection_stopped", "檢測已停止"))
    
    def on_color_detected(self, message: str):
        """
        顏色檢測觸發（已棄用，保留用於兼容性）
        現在檢測結果通過 _result_processor_loop 處理
        """
        # 這個方法現在主要用於信號連接，實際處理在結果處理線程中
        pass
    
    def update_display(self):
        """更新顯示（主線程）"""
        # 計算 UI FPS
        self.ui_update_count += 1
        ui_elapsed = time.time() - self.ui_update_start_time
        if ui_elapsed >= 1.0:  # 每秒更新一次
            self.ui_fps = self.ui_update_count / ui_elapsed
            self.ui_update_count = 0
            self.ui_update_start_time = time.time()
        
        # 更新滑鼠狀態
        if mouse_module.is_connected:
            self.mouse_status_label.setText(t("connected_status", "已連接"))
            self.mouse_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.mouse_status_label.setText(t("not_connected", "未連接"))
            self.mouse_status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # 檢查調試窗口是否被用戶關閉
        if self.debug_window and not self.debug_window.is_window_open():
            self.debug_window = None
            self.debug_window_checkbox.setChecked(False)
        
        # 更新畫面和統計
        mode_data = self.capture_mode_combo.currentData()
        is_connected = False
        
        if mode_data == "udp":
            is_connected = self.udp_receiver is not None and self.udp_receiver.is_connected
        elif mode_data == "capture_card":
            is_connected = self.capture_card_camera is not None and self.capture_card_camera.cap is not None and self.capture_card_camera.cap.isOpened()
        elif mode_data and mode_data.startswith("bettercam"):
            is_connected = self.bettercam_camera is not None and self.bettercam_camera.running
        elif mode_data == "mss":
            is_connected = self.mss_capture is not None and self.mss_capture.running
        elif mode_data == "dxgi":
            is_connected = self.dxgi_capture is not None and self.dxgi_capture.running
        
        if is_connected:
            # 從線程安全的顯示幀獲取（用於調試窗口）
            with self.frame_lock:
                display_frame = self.current_display_frame
            
            # 獲取最新的檢測結果（非阻塞，只取最新的）
            latest_result = None
            while True:
                try:
                    latest_result = self.detection_result_queue.get_nowait()
                except Empty:
                    break  # 獲取最新的結果後退出
            
            if display_frame is not None:
                # 更新檢測狀態顯示（基於異步檢測結果）
                if self.is_running and latest_result:
                    base_style = "padding: 20px; border-radius: 5px; color: #000; font-weight: bold;"
                    
                    if latest_result['mode'] == 1:
                        state = latest_result.get('state')
                        if state == "from":
                            self.detection_status_label.setText("檢測到起始顏色")
                            self.detection_status_label.setStyleSheet(
                                base_style + "background-color: #ff5555; color: white;")
                            if self.debug_window:
                                self.debug_window.set_detection_state("from")
                        elif state == "to":
                            self.detection_status_label.setText("檢測到目標顏色")
                            self.detection_status_label.setStyleSheet(
                                base_style + "background-color: #55ff55; color: black;")
                            if self.debug_window:
                                self.debug_window.set_detection_state("to")
                        else:
                            self.detection_status_label.setText("等待顏色變化...")
                            self.detection_status_label.setStyleSheet(
                                "padding: 20px; background-color: #2D2D2D; border: 1px solid #444; border-radius: 5px; color: #888;")
                            if self.debug_window:
                                self.debug_window.set_detection_state(None)
                    else:  # 模式 2
                        if latest_result.get('color_present', False):
                            self.detection_status_label.setText(t("target_color_present", "目標顏色存在"))
                            self.detection_status_label.setStyleSheet(
                                base_style + "background-color: #ffff55; color: black;")
                            if self.debug_window:
                                self.debug_window.set_detection_state("detected")
                        else:
                            self.detection_status_label.setText(t("waiting_for_target_color", "等待目標顏色..."))
                            self.detection_status_label.setStyleSheet(
                                "padding: 20px; background-color: #2D2D2D; border: 1px solid #444; border-radius: 5px; color: #888;")
                            if self.debug_window:
                                self.debug_window.set_detection_state(None)
                    
                    # 更新冷卻倒數
                    cooldown_remaining = self.click_controller.get_cooldown_remaining()
                    if cooldown_remaining > 0:
                        self.cooldown_label.setText(t("cooldown_remaining", "冷卻中: {seconds:.2f}秒").format(seconds=cooldown_remaining))
                    else:
                        self.cooldown_label.setText("")
                elif self.is_running:
                    # 檢測運行中但還沒有結果
                    self.detection_status_label.setText(t("detecting", "檢測中..."))
                    self.detection_status_label.setStyleSheet(
                        "padding: 20px; background-color: #2D2D2D; border: 1px solid #444; border-radius: 5px; color: #888;")
                else:
                    self.detection_status_label.setText("未啟動")
                    self.detection_status_label.setStyleSheet(
                        "padding: 20px; background-color: #1E1E1E; border: 1px dashed #444; border-radius: 5px; color: #666;")
                    self.cooldown_label.setText("")
                    if self.debug_window:
                        self.debug_window.set_detection_state(None)
                
                # 更新調試窗口設置
                if self.debug_window:
                    self.debug_window.set_detection_size(self.color_detector.detection_size)
                
                # 記錄幀時間
                self.last_frame_time = time.time()
            else:
                # 檢查是否長時間沒有收到幀
                if time.time() - self.last_frame_time > 3.0:
                    mode_text = self.capture_mode_combo.currentText()
                    self.stats_label.setText(t("waiting_for_frame_data", "等待畫面數據...") + "\n" + t("confirm_capture_providing", "請確認 {mode} 正在提供畫面").format(mode=mode_text))
            
            # 更新統計信息
            try:
                if mode_data == "udp" and self.udp_receiver:
                    stats = self.udp_receiver.get_performance_stats()
                elif mode_data == "tcp" and self.tcp_receiver:
                    stats = self.tcp_receiver.get_performance_stats()
                elif mode_data == "srt" and self.srt_receiver:
                    stats = self.srt_receiver.get_performance_stats()
                    # UDP 模式使用自己的 FPS 統計
                    self.capture_fps = stats['current_fps']
                    queue_info = f"{t('detection_queue', '檢測隊列')}: {self.frame_processing_queue.qsize()}/{self.frame_processing_queue.maxsize}"
                    stats_text = (f"{t('receive_fps', '接收 FPS')}: {stats['current_fps']:.1f} | "
                                f"{t('process_fps', '處理 FPS')}: {stats.get('processing_fps', stats['current_fps']):.1f} | "
                                f"{t('decode_fps', '解碼 FPS')}: {stats.get('decoding_fps', stats['current_fps']):.1f}\n"
                                f"{t('buffer', '緩衝')}: {stats.get('buffer_size_bytes', 0)}{t('bytes', ' bytes')} | "
                                f"{t('queue', '隊列')}: {stats.get('queue_size', 0)} | "
                                f"{t('delay', '延遲')}: {stats.get('receive_delay_ms', 0):.1f}ms | {queue_info}")
                elif mode_data == "tcp" and self.tcp_receiver:
                    stats = self.tcp_receiver.get_performance_stats()
                    # TCP 模式使用自己的 FPS 統計
                    self.capture_fps = stats['current_fps']
                    queue_info = f"{t('detection_queue', '檢測隊列')}: {self.frame_processing_queue.qsize()}/{self.frame_processing_queue.maxsize}"
                    stats_text = (f"{t('receive_fps', '接收 FPS')}: {stats['current_fps']:.1f} | "
                                f"{t('process_fps', '處理 FPS')}: {stats.get('processing_fps', stats['current_fps']):.1f} | "
                                f"{t('decode_fps', '解碼 FPS')}: {stats.get('decoding_fps', stats['current_fps']):.1f}\n"
                                f"{t('buffer', '緩衝')}: {stats.get('buffer_size_bytes', 0)}{t('bytes', ' bytes')} | "
                                f"{t('queue', '隊列')}: {stats.get('queue_size', 0)} | "
                                f"{t('delay', '延遲')}: {stats.get('receive_delay_ms', 0):.1f}ms | {queue_info}")
                elif mode_data == "srt" and self.srt_receiver:
                    stats = self.srt_receiver.get_performance_stats()
                    # SRT 模式使用自己的 FPS 統計
                    self.capture_fps = stats['current_fps']
                    queue_info = f"{t('detection_queue', '檢測隊列')}: {self.frame_processing_queue.qsize()}/{self.frame_processing_queue.maxsize}"
                    stats_text = (f"{t('receive_fps', '接收 FPS')}: {stats['current_fps']:.1f} | "
                                f"{t('process_fps', '處理 FPS')}: {stats.get('processing_fps', stats['current_fps']):.1f} | "
                                f"{t('decode_fps', '解碼 FPS')}: {stats.get('decoding_fps', stats['current_fps']):.1f}\n"
                                f"{t('buffer', '緩衝')}: {stats.get('buffer_size_bytes', 0)}{t('bytes', ' bytes')} | "
                                f"{t('queue', '隊列')}: {stats.get('queue_size', 0)} | "
                                f"{t('delay', '延遲')}: {stats.get('receive_delay_ms', 0):.1f}ms | {queue_info}")
                elif mode_data in ["capture_card", "bettercam", "mss", "dxgi"]:
                    # 其他模式的簡單統計
                    queue_info = f"{t('detection_queue', '檢測隊列')}: {self.frame_processing_queue.qsize()}/{self.frame_processing_queue.maxsize}"
                    elapsed = time.time() - self.frame_count_start_time
                    # 確保 elapsed 至少為 0.1 秒以避免除零錯誤和初始值問題
                    current_count = 0
                    fps = 0.0
                    if elapsed < 0.1:
                        fps = 0.0
                    else:
                        # 使用線程安全的方式讀取 frame_count
                        if hasattr(self, '_frame_count_lock'):
                            with self._frame_count_lock:
                                current_count = self.frame_count
                        else:
                            current_count = self.frame_count
                        # 計算 FPS，確保不為負數
                        fps = float(current_count) / elapsed if elapsed > 0 else 0.0
                        # 如果 frame_count 為 0 但已經過了較長時間，可能是沒有收到幀
                        if current_count == 0 and elapsed > 1.0:
                            fps = 0.0
                    # 更新擷取 FPS（強制更新，確保值正確）
                    self.capture_fps = max(0.0, fps)
                    # 調試：每 5 秒記錄一次 FPS（僅在開發時使用）
                    if not hasattr(self, '_last_fps_log_time'):
                        self._last_fps_log_time = time.time()
                    if time.time() - self._last_fps_log_time > 5.0:
                        logger.debug(f"FPS 計算: frame_count={current_count}, elapsed={elapsed:.2f}s, fps={fps:.1f}, capture_fps={self.capture_fps:.1f}")
                        self._last_fps_log_time = time.time()
                    stats_text = f"{t('capture_mode', '擷取模式')}: {self.capture_mode_combo.currentText()} | {queue_info}"
                    # 總是顯示 FPS，即使為 0
                    stats_text = f"FPS: {fps:.1f} | " + stats_text
                else:
                    # 默認統計
                    queue_info = f"{t('detection_queue', '檢測隊列')}: {self.frame_processing_queue.qsize()}/{self.frame_processing_queue.maxsize}"
                    stats_text = f"{t('capture_mode', '擷取模式')}: {self.capture_mode_combo.currentText()} | {queue_info}"
                self.stats_label.setText(stats_text)
            except Exception as e:
                logger.error(f"Failed to get stats: {e}")
        else:
            # 未連接時，設置 capture_fps 為 0
            self.capture_fps = 0.0
        
        # 更新頂部 FPS 顯示（無論是否連接都更新，強制刷新）
        if hasattr(self, 'fps_label'):
            try:
                # 確保值為浮點數且非負
                ui_fps_val = max(0.0, float(self.ui_fps)) if hasattr(self, 'ui_fps') else 0.0
                capture_fps_val = max(0.0, float(self.capture_fps)) if hasattr(self, 'capture_fps') else 0.0
                fps_text = t("ui_fps_display", "UI FPS: {ui_fps:.1f} | 擷取FPS: {capture_fps:.1f}").format(
                    ui_fps=ui_fps_val,
                    capture_fps=capture_fps_val
                )
                self.fps_label.setText(fps_text)
            except Exception as e:
                logger.debug(f"FPS label update error: {e}")
                # 即使出錯也嘗試更新
                try:
                    self.fps_label.setText(f"UI FPS: {self.ui_fps:.1f} | 擷取FPS: {self.capture_fps:.1f}")
                except:
                    pass
    
    def log(self, message: str, error: bool = False):
        """添加日誌"""
        timestamp = time.strftime("%H:%M:%S")
        color = "#ff5555" if error else "#00E5FF" # 使用適合暗黑模式的顏色 (紅/青)
        log_entry = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        self.log_text.append(log_entry)
        
        # 自動滾動到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """關閉窗口時清理資源"""
        # 自動保存配置
        self.save_current_config()
        
        if self.is_running:
            self.toggle_detection()
        
        # 關閉調試窗口
        if self.debug_window:
            DebugWindowManager.destroy_window()
            self.debug_window = None
        
        # 斷開所有連接
        if self.udp_receiver:
            self.udp_receiver.disconnect()
        if self.capture_card_camera:
            self.capture_card_camera.stop()
        if self.bettercam_camera:
            try:
                self.bettercam_camera.stop()
            except Exception as e:
                log_exception(e, context="關閉窗口時停止 BetterCam", additional_info={
                    "階段": "closeEvent"
                })
                logger.error(f"關閉 BetterCam 時出錯: {e}")
            finally:
                self.bettercam_camera = None
        if self.mss_capture:
            self.mss_capture.stop()
            self.mss_capture = None
        
        # 關閉線程池
        if hasattr(self, 'detection_executor') and self.detection_executor:
            self.detection_executor.shutdown(wait=False, cancel_futures=True)
        
        if self.mouse:
            Mouse.cleanup()
        
        event.accept()


def main():
    # 初始化日誌系統（在程序開始時）
    logger.info("=" * 80)
    logger.info("顏色檢測自動點擊程式 v1.2")
    logger.info("made by asenyeroao")
    logger.info("Discord: https://discord.gg/M6dVNKq8zP")
    logger.info("=" * 80)
    logger.info("正在初始化程式...")
    
    # 輸出啟動資訊到控制台
    print("=" * 50)
    print("顏色檢測自動點擊程式 v1.2")
    print("made by asenyeroao")
    print("Discord: https://discord.gg/M6dVNKq8zP")
    print("=" * 50)
    print("正在初始化程式...")
    print(f"詳細日誌將記錄到: debug.log")
    
    try:
        app = QApplication(sys.argv)
        logger.info("QApplication 創建成功")
        
        # 應用暗色科技風樣式
        app.setStyleSheet(MODERN_STYLESHEET)
        logger.info("樣式表已應用")
        
        # 設置應用程式字體（確保中文顯示正常）
        font = QFont("Microsoft YaHei UI", 9)
        app.setFont(font)
        logger.info("字體已設置: Microsoft YaHei UI, 9pt")
        
        print("正在載入主視窗...")
        logger.info("正在載入主視窗...")
        window = MainWindow()
        window.show()
        logger.info("主視窗已顯示")
        
        print("程式已啟動！")
        print("提示：關閉此視窗將關閉程式")
        print(f"詳細日誌已記錄到: {os.path.abspath('debug.log')}")
        print("-" * 50)
        logger.info("程式已啟動！")
        logger.info("=" * 80)
        
        exit_code = app.exec_()
        logger.info(f"程式退出，退出代碼: {exit_code}")
        return exit_code
        
    except Exception as e:
        log_exception(e, context="程序啟動", additional_info={
            "階段": "main()",
            "系統": "Windows"
        })
        print(f"程式啟動失敗: {e}")
        print(f"詳細錯誤已記錄到: debug.log")
        return 1


if __name__ == "__main__":
    main()
