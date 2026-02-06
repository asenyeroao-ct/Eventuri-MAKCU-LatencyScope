"""
詳細的調試日誌系統
提供文件日誌、控制台日誌和詳細的錯誤追蹤功能
支持多語言
"""

import logging
import sys
import os
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Any

# 延遲導入語言管理器，避免循環依賴
_language_manager = None


def _get_translation(key: str, default: Optional[str] = None) -> str:
    """獲取翻譯文本（延遲加載）"""
    global _language_manager
    if _language_manager is None:
        try:
            from ui.language_manager import get_language_manager
            _language_manager = get_language_manager()
        except Exception:
            # 如果無法載入語言管理器，返回默認值
            return default if default is not None else key
    
    try:
        return _language_manager.get(key, default if default is not None else key)
    except Exception:
        return default if default is not None else key


class DetailedFormatter(logging.Formatter):
    """詳細的日誌格式化器，包含更多調試信息"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日誌記錄"""
        # 基本格式：時間戳 | 級別 | 模組:行號 | 函數 | 訊息
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # 獲取調用堆棧信息
        frame = sys._getframe(6)  # 獲取調用者的幀
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name
        
        # 構建詳細的日誌格式
        log_format = (
            f"[{timestamp}] "
            f"[{record.levelname:8s}] "
            f"[{filename}:{lineno}] "
            f"[{func_name}] "
            f"{record.getMessage()}"
        )
        
        # 如果有異常信息，添加詳細的堆棧追蹤
        if record.exc_info:
            log_format += "\n" + self.formatException(record.exc_info)
        
        return log_format


class DebugLogger:
    """調試日誌管理器"""
    
    _instance: Optional['DebugLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.log_file = "debug.log"
        self.max_bytes = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5  # 保留5個備份文件
        self.logger: Optional[logging.Logger] = None
        self._setup_logger()
        DebugLogger._initialized = True
    
    def _setup_logger(self):
        """設置日誌記錄器"""
        # 創建根日誌記錄器
        self.logger = logging.getLogger('HumanBenchmark')
        self.logger.setLevel(logging.DEBUG)
        
        # 清除現有的處理器
        self.logger.handlers.clear()
        
        # 防止日誌向上傳播到根日誌記錄器
        self.logger.propagate = False
        
        # 1. 文件處理器 - 記錄所有級別的日誌到 debug.log
        try:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = DetailedFormatter()
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            warning_msg = _get_translation("debug_warning_cannot_create_file_handler", "警告：無法創建文件日誌處理器")
            print(f"{warning_msg}: {e}")
        
        # 2. 控制台處理器 - 只顯示 INFO 及以上級別
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 記錄初始化信息（使用翻譯）
        self.logger.info("=" * 80)
        self.logger.info(_get_translation("debug_log_system_initialized", "日誌系統初始化完成"))
        self.logger.info(f"{_get_translation('debug_log_file', '日誌文件')}: {os.path.abspath(self.log_file)}")
        self.logger.info(f"{_get_translation('debug_max_file_size', '最大文件大小')}: {self.max_bytes / 1024 / 1024:.1f} MB")
        self.logger.info(f"{_get_translation('debug_backup_count', '備份文件數量')}: {self.backup_count}")
        self.logger.info("=" * 80)
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """獲取日誌記錄器"""
        if name:
            return self.logger.getChild(name)
        return self.logger
    
    def log_exception(self, 
                     exception: Exception, 
                     context: Optional[str] = None,
                     additional_info: Optional[dict] = None):
        """記錄異常的詳細信息"""
        if not self.logger:
            return
        
        error_msg = _get_translation("debug_exception_occurred", "發生異常")
        if context:
            context_label = _get_translation("debug_context", "上下文")
            error_msg += f" ({context_label}: {context})"
        
        self.logger.error(error_msg, exc_info=True)
        
        # 記錄額外的上下文信息
        if additional_info:
            additional_label = _get_translation("debug_additional_info", "額外信息")
            info_str = "\n".join([f"  {k}: {v}" for k, v in additional_info.items()])
            self.logger.error(f"{additional_label}:\n{info_str}")
        
        # 記錄完整的堆棧追蹤
        stack_trace = traceback.format_exc()
        stack_trace_label = _get_translation("debug_full_stack_trace", "完整堆棧追蹤")
        self.logger.debug(f"{stack_trace_label}:\n{stack_trace}")
    
    def log_function_call(self, 
                         func_name: str,
                         args: Optional[tuple] = None,
                         kwargs: Optional[dict] = None):
        """記錄函數調用"""
        if not self.logger:
            return
        
        call_info = f"{_get_translation('debug_calling_function', '調用函數')}: {func_name}"
        if args:
            args_label = _get_translation("debug_arguments", "參數")
            call_info += f" | {args_label}: {args}"
        if kwargs:
            kwargs_label = _get_translation("debug_keyword_arguments", "關鍵字參數")
            call_info += f" | {kwargs_label}: {kwargs}"
        
        self.logger.debug(call_info)
    
    def log_performance(self, operation: str, duration: float, details: Optional[dict] = None):
        """記錄性能信息"""
        if not self.logger:
            return
        
        duration_label = _get_translation("debug_duration", "耗時")
        seconds_label = _get_translation("debug_seconds", "秒")
        perf_msg = f"{_get_translation('debug_performance', '性能')}: {operation} {duration_label} {duration:.3f} {seconds_label}"
        if details:
            detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            perf_msg += f" | {detail_str}"
        
        self.logger.debug(perf_msg)
    
    def log_state_change(self, component: str, old_state: Any, new_state: Any):
        """記錄狀態變化"""
        if not self.logger:
            return
        
        state_change_label = _get_translation("debug_state_change", "狀態變化")
        self.logger.info(f"{state_change_label} [{component}]: {old_state} -> {new_state}")
    
    def log_config_change(self, key: str, old_value: Any, new_value: Any):
        """記錄配置變化"""
        if not self.logger:
            return
        
        config_change_label = _get_translation("debug_config_change", "配置變化")
        self.logger.info(f"{config_change_label}: {key} = {old_value} -> {new_value}")
    
    def log_connection_event(self, event_type: str, details: Optional[dict] = None):
        """記錄連接事件"""
        if not self.logger:
            return
        
        connection_event_label = _get_translation("debug_connection_event", "連接事件")
        event_msg = f"{connection_event_label}: {event_type}"
        if details:
            detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            event_msg += f" | {detail_str}"
        
        self.logger.info(event_msg)
    
    def log_detection_event(self, event_type: str, details: Optional[dict] = None):
        """記錄檢測事件"""
        if not self.logger:
            return
        
        detection_event_label = _get_translation("debug_detection_event", "檢測事件")
        event_msg = f"{detection_event_label}: {event_type}"
        if details:
            detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            event_msg += f" | {detail_str}"
        
        self.logger.debug(event_msg)
    
    def flush(self):
        """刷新所有日誌處理器"""
        if self.logger:
            for handler in self.logger.handlers:
                handler.flush()


# 全局日誌管理器實例
_debug_logger: Optional[DebugLogger] = None


def get_debug_logger() -> DebugLogger:
    """獲取全局日誌管理器實例"""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """獲取日誌記錄器（便捷函數）"""
    return get_debug_logger().get_logger(name)


def log_exception(exception: Exception, 
                 context: Optional[str] = None,
                 additional_info: Optional[dict] = None):
    """記錄異常（便捷函數）"""
    get_debug_logger().log_exception(exception, context, additional_info)


def log_function_call(func_name: str,
                     args: Optional[tuple] = None,
                     kwargs: Optional[dict] = None):
    """記錄函數調用（便捷函數）"""
    get_debug_logger().log_function_call(func_name, args, kwargs)


def log_performance(operation: str, duration: float, details: Optional[dict] = None):
    """記錄性能信息（便捷函數）"""
    get_debug_logger().log_performance(operation, duration, details)


def log_state_change(component: str, old_state: Any, new_state: Any):
    """記錄狀態變化（便捷函數）"""
    get_debug_logger().log_state_change(component, old_state, new_state)


def log_config_change(key: str, old_value: Any, new_value: Any):
    """記錄配置變化（便捷函數）"""
    get_debug_logger().log_config_change(key, old_value, new_value)


def log_connection_event(event_type: str, details: Optional[dict] = None):
    """記錄連接事件（便捷函數）"""
    get_debug_logger().log_connection_event(event_type, details)


def log_detection_event(event_type: str, details: Optional[dict] = None):
    """記錄檢測事件（便捷函數）"""
    get_debug_logger().log_detection_event(event_type, details)


# 導出主要接口
__all__ = [
    'DebugLogger',
    'get_debug_logger',
    'get_logger',
    'log_exception',
    'log_function_call',
    'log_performance',
    'log_state_change',
    'log_config_change',
    'log_connection_event',
    'log_detection_event',
]

