"""
點擊控制模組
負責處理滑鼠點擊邏輯、延遲和冷卻管理
"""

import time
import logging
import threading
import random
from typing import Optional, Tuple
import utils.mouse as mouse_module

logger = logging.getLogger(__name__)


class ClickController:
    """點擊控制器 - 管理點擊時序和冷卻"""
    
    def __init__(self):
        # 點擊時序設置 (毫秒) - 支持範圍隨機
        self.press_delay_min = 0  # 按下延遲最小值
        self.press_delay_max = 0  # 按下延遲最大值
        self.release_delay_min = 50  # 釋放延遲最小值
        self.release_delay_max = 50  # 釋放延遲最大值
        
        # 冷卻管理 - 支持範圍隨機
        self.trigger_cooldown_min = 0.1  # 秒
        self.trigger_cooldown_max = 0.1  # 秒
        self.last_trigger_time = 0
        
        # 執行鎖（防止並發點擊）
        self._click_lock = threading.Lock()
        
        # 統計
        self.total_clicks = 0
        self.failed_clicks = 0
        
        logger.info("ClickController initialized")
    
    def set_press_delay(self, delay_ms: int):
        """設置按下延遲（毫秒）- 單一值（向後兼容）"""
        self.press_delay_min = delay_ms
        self.press_delay_max = delay_ms
        logger.info(f"Press delay set to: {delay_ms}ms")
    
    def set_press_delay_range(self, min_ms: int, max_ms: int):
        """設置按下延遲範圍（毫秒）"""
        self.press_delay_min = min(min_ms, max_ms)
        self.press_delay_max = max(min_ms, max_ms)
        logger.info(f"Press delay range set to: {self.press_delay_min}~{self.press_delay_max}ms")
    
    def get_random_press_delay(self) -> int:
        """獲取隨機按下延遲（毫秒）"""
        if self.press_delay_min == self.press_delay_max:
            return self.press_delay_min
        return random.randint(self.press_delay_min, self.press_delay_max)
    
    def set_release_delay(self, delay_ms: int):
        """設置釋放延遲（毫秒）- 單一值（向後兼容）"""
        self.release_delay_min = delay_ms
        self.release_delay_max = delay_ms
        logger.info(f"Release delay set to: {delay_ms}ms")
    
    def set_release_delay_range(self, min_ms: int, max_ms: int):
        """設置釋放延遲範圍（毫秒）"""
        self.release_delay_min = min(min_ms, max_ms)
        self.release_delay_max = max(min_ms, max_ms)
        logger.info(f"Release delay range set to: {self.release_delay_min}~{self.release_delay_max}ms")
    
    def get_random_release_delay(self) -> int:
        """獲取隨機釋放延遲（毫秒）"""
        if self.release_delay_min == self.release_delay_max:
            return self.release_delay_min
        return random.randint(self.release_delay_min, self.release_delay_max)
    
    def set_cooldown(self, cooldown_ms: int):
        """設置冷卻時間（毫秒）- 單一值（向後兼容）"""
        cooldown_sec = cooldown_ms / 1000.0
        self.trigger_cooldown_min = cooldown_sec
        self.trigger_cooldown_max = cooldown_sec
        logger.info(f"Trigger cooldown set to: {cooldown_ms}ms")
    
    def set_cooldown_range(self, min_ms: int, max_ms: int):
        """設置冷卻時間範圍（毫秒）"""
        self.trigger_cooldown_min = min(min_ms, max_ms) / 1000.0
        self.trigger_cooldown_max = max(min_ms, max_ms) / 1000.0
        logger.info(f"Trigger cooldown range set to: {self.trigger_cooldown_min*1000:.0f}~{self.trigger_cooldown_max*1000:.0f}ms")
    
    def get_random_cooldown(self) -> float:
        """獲取隨機冷卻時間（秒）"""
        if self.trigger_cooldown_min == self.trigger_cooldown_max:
            return self.trigger_cooldown_min
        return random.uniform(self.trigger_cooldown_min, self.trigger_cooldown_max)
    
    def can_trigger(self) -> bool:
        """檢查是否可以觸發（冷卻是否結束）"""
        current_time = time.time()
        # 使用最小冷卻時間進行檢查
        return (current_time - self.last_trigger_time) >= self.trigger_cooldown_min
    
    def get_cooldown_remaining(self) -> float:
        """獲取剩餘冷卻時間（秒）"""
        current_time = time.time()
        elapsed = current_time - self.last_trigger_time
        # 使用最小冷卻時間進行計算
        remaining = max(0, self.trigger_cooldown_min - elapsed)
        return remaining
    
    def execute_click(self, mouse_obj, blocking: bool = True) -> bool:
        """
        執行點擊操作
        
        Args:
            mouse_obj: Mouse 實例
            blocking: 是否阻塞執行（True=同步，False=異步）
            
        Returns:
            是否成功執行
        """
        # 檢查冷卻
        if not self.can_trigger():
            logger.debug(f"Click blocked by cooldown (remaining: {self.get_cooldown_remaining():.3f}s)")
            return False
        
        # 檢查滑鼠連接
        if not mouse_module.is_connected:
            logger.warning("Click failed: mouse not connected")
            self.failed_clicks += 1
            return False
        
        # 更新觸發時間
        self.last_trigger_time = time.time()
        
        if blocking:
            # 同步執行
            return self._perform_click(mouse_obj)
        else:
            # 異步執行
            click_thread = threading.Thread(
                target=self._perform_click,
                args=(mouse_obj,),
                daemon=True,
                name="ClickThread"
            )
            click_thread.start()
            return True
    
    def _perform_click(self, mouse_obj) -> bool:
        """
        實際執行點擊動作
        
        Args:
            mouse_obj: Mouse 實例
            
        Returns:
            是否成功
        """
        with self._click_lock:
            try:
                from utils.mouse import makcu, makcu_lock
                
                # 獲取隨機延遲值
                press_delay = self.get_random_press_delay()
                release_delay = self.get_random_release_delay()
                
                # 1. 等待按下延遲
                if press_delay > 0:
                    time.sleep(press_delay / 1000.0)
                
                # 2. 按下左鍵
                with makcu_lock:
                    makcu.write(b"km.left(1)\r")
                    makcu.flush()
                
                logger.debug(f"Mouse button pressed (after {press_delay}ms delay)")
                
                # 3. 等待釋放延遲
                if release_delay > 0:
                    time.sleep(release_delay / 1000.0)
                
                # 4. 釋放左鍵
                with makcu_lock:
                    makcu.write(b"km.left(0)\r")
                    makcu.flush()
                
                logger.debug(f"Mouse button released (after {release_delay}ms hold)")
                
                self.total_clicks += 1
                return True
                
            except Exception as e:
                logger.error(f"Click execution failed: {e}", exc_info=True)
                self.failed_clicks += 1
                return False
    
    def test_click(self, mouse_obj) -> bool:
        """
        測試點擊（不受冷卻限制）
        
        Args:
            mouse_obj: Mouse 實例
            
        Returns:
            是否成功
        """
        if not mouse_module.is_connected:
            logger.error("Test click failed: mouse not connected")
            return False
        
        try:
            from utils.mouse import makcu, makcu_lock
            
            # 獲取隨機延遲值用於測試
            press_delay = self.get_random_press_delay()
            release_delay = self.get_random_release_delay()
            
            logger.info(f"Testing click (press_delay={press_delay}ms, release_delay={release_delay}ms)")
            
            # 等待按下延遲
            if press_delay > 0:
                logger.info(f"→ Waiting {press_delay}ms before press...")
                time.sleep(press_delay / 1000.0)
            
            # 按下
            with makcu_lock:
                makcu.write(b"km.left(1)\r")
                makcu.flush()
            logger.info("→ Button pressed")
            
            # 等待釋放延遲
            if release_delay > 0:
                logger.info(f"→ Waiting {release_delay}ms before release...")
                time.sleep(release_delay / 1000.0)
            
            # 釋放
            with makcu_lock:
                makcu.write(b"km.left(0)\r")
                makcu.flush()
            logger.info("✓ Button released, test complete")
            
            return True
            
        except Exception as e:
            logger.error(f"Test click failed: {e}", exc_info=True)
            return False
    
    def get_stats(self) -> dict:
        """獲取統計信息"""
        return {
            'total_clicks': self.total_clicks,
            'failed_clicks': self.failed_clicks,
            'success_rate': (self.total_clicks / max(1, self.total_clicks + self.failed_clicks)) * 100,
            'cooldown_remaining': self.get_cooldown_remaining()
        }
    
    def reset_stats(self):
        """重置統計"""
        self.total_clicks = 0
        self.failed_clicks = 0
        logger.info("Click statistics reset")

