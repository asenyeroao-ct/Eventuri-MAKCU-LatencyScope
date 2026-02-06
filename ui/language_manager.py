"""
語言管理模組
負責載入、管理和切換應用程式的語言
"""

import json
import os
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

LANG_DIR = "lang"
DEFAULT_LANG = "zh_CN"  # 默認語言：簡體中文


class LanguageManager:
    """語言管理器"""
    
    def __init__(self, lang_dir: str = LANG_DIR):
        """
        初始化語言管理器
        
        Args:
            lang_dir: 語言文件目錄
        """
        self.lang_dir = lang_dir
        self.current_lang = DEFAULT_LANG
        self.translations: Dict[str, str] = {}
        self.available_languages: List[Tuple[str, str]] = []  # [(lang_code, lang_name), ...]
        
        # 確保語言目錄存在
        if not os.path.exists(self.lang_dir):
            os.makedirs(self.lang_dir)
            logger.info(f"創建語言目錄: {self.lang_dir}")
        
        # 掃描可用的語言文件
        self._scan_languages()
        
        # 載入默認語言
        self.load_language(DEFAULT_LANG)
    
    def _scan_languages(self):
        """掃描 lang 目錄中的所有語言文件"""
        self.available_languages = []
        
        if not os.path.exists(self.lang_dir):
            return
        
        try:
            for filename in os.listdir(self.lang_dir):
                if filename.endswith('.json'):
                    lang_code = filename[:-5]  # 移除 .json 後綴
                    lang_file = os.path.join(self.lang_dir, filename)
                    
                    try:
                        # 讀取語言文件獲取語言名稱
                        with open(lang_file, 'r', encoding='utf-8') as f:
                            lang_data = json.load(f)
                            lang_name = lang_data.get('_language_name', lang_code)
                            self.available_languages.append((lang_code, lang_name))
                            logger.info(f"發現語言文件: {lang_code} - {lang_name}")
                    except Exception as e:
                        logger.error(f"讀取語言文件 {lang_file} 失敗: {e}")
        except Exception as e:
            logger.error(f"掃描語言目錄失敗: {e}")
        
        # 按語言名稱排序
        self.available_languages.sort(key=lambda x: x[1])
    
    def load_language(self, lang_code: str) -> bool:
        """
        載入指定語言
        
        Args:
            lang_code: 語言代碼（例如：zh_CN, zh_TW, en_US）
        
        Returns:
            bool: 是否成功載入
        """
        lang_file = os.path.join(self.lang_dir, f"{lang_code}.json")
        
        if not os.path.exists(lang_file):
            logger.warning(f"語言文件不存在: {lang_file}")
            # 如果找不到，嘗試載入默認語言
            if lang_code != DEFAULT_LANG:
                return self.load_language(DEFAULT_LANG)
            return False
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                lang_data = json.load(f)
                
                # 驗證語言文件格式
                if '_language_name' not in lang_data:
                    logger.warning(f"語言文件缺少 _language_name 字段: {lang_file}")
                
                # 載入翻譯
                self.translations = {}
                for key, value in lang_data.items():
                    if key != '_language_name':  # 跳過語言名稱字段
                        self.translations[key] = value
                
                self.current_lang = lang_code
                logger.info(f"成功載入語言: {lang_code} ({lang_data.get('_language_name', lang_code)})")
                return True
                
        except json.JSONDecodeError as e:
            logger.error(f"語言文件 JSON 格式錯誤: {lang_file}, {e}")
            return False
        except Exception as e:
            logger.error(f"載入語言文件失敗: {lang_file}, {e}")
            return False
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """
        獲取翻譯文本
        
        Args:
            key: 翻譯鍵
            default: 如果找不到翻譯時的默認值
        
        Returns:
            str: 翻譯後的文本
        """
        return self.translations.get(key, default if default is not None else key)
    
    def get_language_name(self, lang_code: str) -> str:
        """
        獲取語言名稱
        
        Args:
            lang_code: 語言代碼
        
        Returns:
            str: 語言名稱
        """
        lang_file = os.path.join(self.lang_dir, f"{lang_code}.json")
        
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    lang_data = json.load(f)
                    return lang_data.get('_language_name', lang_code)
            except:
                pass
        
        return lang_code
    
    def get_available_languages(self) -> List[Tuple[str, str]]:
        """
        獲取所有可用的語言列表
        
        Returns:
            List[Tuple[str, str]]: [(lang_code, lang_name), ...]
        """
        return self.available_languages.copy()
    
    def get_current_lang(self) -> str:
        """獲取當前語言代碼"""
        return self.current_lang


# 全局語言管理器實例
_language_manager: Optional[LanguageManager] = None


def get_language_manager() -> LanguageManager:
    """獲取全局語言管理器實例"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager


def t(key: str, default: Optional[str] = None) -> str:
    """
    快捷函數：獲取翻譯文本
    
    Args:
        key: 翻譯鍵
        default: 默認值
    
    Returns:
        str: 翻譯後的文本
    """
    return get_language_manager().get(key, default)

