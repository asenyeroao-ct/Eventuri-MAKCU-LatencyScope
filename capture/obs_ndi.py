"""
OBS NDI Receiver Module
Provides NDI (Network Device Interface) stream receiving functionality
Similar structure to OBS_UDP.pyx for consistency
"""

import time
import numpy as np
import cv2
import logging
from typing import Optional, List, Callable

# NDI imports
from cyndilib.wrapper.ndi_recv import RecvColorFormat, RecvBandwidth
from cyndilib.finder import Finder
from cyndilib.receiver import Receiver
from cyndilib.video_frame import VideoFrameSync
from cyndilib.audio_frame import AudioFrameSync

logger = logging.getLogger(__name__)


class NDI_Receiver:
    """
    NDI receiver for receiving video stream from NDI sources
    Supports auto-discovery, source selection, and frame capture
    """
    
    def __init__(self, config=None):
        """
        Initialize NDI receiver
        
        Args:
            config: Optional config object for accessing ndi_width, ndi_height
        """
        self.config = config
        
        # Initialize NDI components
        self.finder = Finder()
        self.finder.set_change_callback(self.on_finder_change)
        self.finder.open()
        
        self.receiver = Receiver(
            color_format=RecvColorFormat.RGBX_RGBA,
            bandwidth=RecvBandwidth.highest,
        )
        self.video_frame = VideoFrameSync()
        self.audio_frame = AudioFrameSync()
        self.receiver.frame_sync.set_video_frame(self.video_frame)
        self.receiver.frame_sync.set_audio_frame(self.audio_frame)
        
        # Connection state
        self.available_sources = []
        self.desired_source_name = None
        self._pending_index = None
        self._pending_connect = False
        self._last_connect_try = 0.0
        self._retry_interval = 0.5
        
        self.connected = False
        self.is_receiving = False
        self._source_name = None
        self._size_checked = False
        self._allowed_sizes = {128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 480, 512, 544, 576, 608, 640}
        
        # Frame callback
        self.frame_callback = None
        
        # Statistics
        self.total_frames_received = 0
        self.current_fps = 0.0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        
        # Prime the initial list so select_source(0) works immediately
        try:
            self.available_sources = self.finder.get_source_names() or []
        except Exception:
            self.available_sources = []
        
        logger.info("NDI_Receiver initialized")
    
    def set_frame_callback(self, callback: Optional[Callable]):
        """Set callback function for frame processing"""
        self.frame_callback = callback
    
    def on_finder_change(self):
        """Callback when NDI sources change"""
        self.available_sources = self.finder.get_source_names() or []
        logger.info(f"[NDI] Found sources: {self.available_sources}")
        
        if self._pending_index is not None and 0 <= self._pending_index < len(self.available_sources):
            self.desired_source_name = self.available_sources[self._pending_index]
        
        if self._pending_connect and not self.connected and self.desired_source_name in self.available_sources:
            self._try_connect_throttled()
    
    def select_source(self, name_or_index):
        """
        Select NDI source by name or index
        
        Args:
            name_or_index: Source name (str) or index (int)
        """
        # Guard against early calls
        if self.available_sources is None:
            self.available_sources = []
        
        self._pending_connect = True
        if isinstance(name_or_index, int):
            self._pending_index = name_or_index
            if 0 <= name_or_index < len(self.available_sources):
                self.desired_source_name = self.available_sources[name_or_index]
            else:
                logger.info(f"[NDI] Will connect to index {name_or_index} when sources are ready.")
                return
        else:
            self.desired_source_name = str(name_or_index)
        
        if self.desired_source_name in self.available_sources:
            self._try_connect_throttled()
    
    def _try_connect_throttled(self):
        """Throttled connection attempt to avoid excessive retries"""
        now = time.time()
        if now - self._last_connect_try < self._retry_interval:
            return
        self._last_connect_try = now
        if self.desired_source_name:
            self.connect_to_source(self.desired_source_name)
    
    def connect_to_source(self, source_name: str) -> bool:
        """
        Connect to a specific NDI source
        
        Args:
            source_name: Name of the NDI source to connect to
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        source = self.finder.get_source(source_name)
        if not source:
            logger.warning(f"[NDI] Source '{source_name}' not available (get_source returned None).")
            return False
        
        self.receiver.set_source(source)
        self._source_name = source.name
        logger.info(f"[NDI] set_source -> {self._source_name}")
        
        # Wait for connection with timeout
        for _ in range(200):
            if self.receiver.is_connected():
                self.connected = True
                self.is_receiving = True
                self._pending_connect = False
                logger.info("[NDI] Receiver reports CONNECTED.")
                self._size_checked = False
                return True
            time.sleep(0.01)
        else:
            logger.warning("[NDI] Timeout: receiver never reported connected.")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from NDI source and cleanup resources"""
        try:
            self.connected = False
            self.is_receiving = False
            
            # Detach first so sender-side frees up immediately
            try:
                self.receiver.set_source(None)
            except Exception:
                pass
            
            self.finder.close()
            logger.info("[NDI] Disconnected from NDI source")
            
        except Exception as e:
            logger.error(f"[NDI] Error during disconnect: {e}")
    
    def get_current_frame(self):
        """
        Get current frame from NDI stream
        
        Returns:
            numpy.ndarray or None: Current frame or None if not available
        """
        if not self.receiver.is_connected():
            return None
        
        self.receiver.frame_sync.capture_video()
        if min(self.video_frame.xres, self.video_frame.yres) == 0:
            return None
        
        # Update config dimensions if config is available
        if self.config:
            self.config.ndi_width = self.video_frame.xres
            self.config.ndi_height = self.video_frame.yres
        
        # One-time verdict/log about resolution
        self._log_size_verdict_once(self.video_frame.xres, self.video_frame.yres)
        
        # Copy frame to own memory to avoid "cannot write with view active"
        frame = np.frombuffer(self.video_frame, dtype=np.uint8).copy()
        frame = frame.reshape((self.video_frame.yres, self.video_frame.xres, 4))
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        
        # Update statistics
        self._update_fps_counters()
        self.total_frames_received += 1
        
        # Trigger callback if set
        if self.frame_callback:
            try:
                self.frame_callback(frame)
            except Exception as e:
                logger.error(f"Error in frame callback: {e}")
        
        return frame
    
    def _log_size_verdict_once(self, w: int, h: int):
        """Log resolution verdict once per connection"""
        if self._size_checked:
            return
        self._size_checked = True
        
        name = self._source_name or "NDI Source"
        if w == h and w in self._allowed_sizes:
            logger.info(f"[NDI] Source {name}: {w}x{h} ✔ allowed (no resize).")
            return
        
        target = min(w, h)
        allowed = sorted(self._allowed_sizes)
        down = max((s for s in allowed if s <= target), default=None)
        up = min((s for s in allowed if s >= target), default=None)
        
        if down is None and up is None:
            suggest = 640
        elif down is None:
            suggest = up
        elif up is None:
            suggest = down
        else:
            suggest = down if (target - down) <= (up - target) else up
        
        if w != h:
            logger.warning(
                f"[NDI][FOV WARNING] Source {name}: input {w}x{h} is not square. "
                f"Nearest allowed square: {suggest}x{suggest}. "
                f"Consider a center crop to {suggest}x{suggest} for stable colors & model sizing."
            )
        else:
            logger.warning(
                f"[NDI][FOV WARNING] Source {name}: {w}x{h} not in allowed set. "
                f"Nearest allowed: {suggest}x{suggest}. "
                f"Consider a center ROI of {suggest}x{suggest} to avoid interpolation artifacts."
            )
    
    def list_sources(self, refresh: bool = True) -> List[str]:
        """
        Return a list of NDI source names
        
        Args:
            refresh: If True, query the Finder for latest sources
            
        Returns:
            List[str]: List of available NDI source names
        """
        if refresh:
            try:
                self.available_sources = self.finder.get_source_names() or []
            except Exception:
                # Keep whatever we had, but make sure it's a list
                self.available_sources = self.available_sources or []
        return list(self.available_sources)
    
    def maintain_connection(self):
        """Maintain connection and attempt reconnection if needed"""
        if self.connected and not self.receiver.is_connected():
            self.connected = False
            self.is_receiving = False
            self._pending_connect = True
        
        # Try reconnect if source is present
        if self._pending_connect and self.desired_source_name in self.available_sources:
            self._try_connect_throttled()
    
    def switch_source(self, name_or_index):
        """
        Switch to a different NDI source
        
        Args:
            name_or_index: Source name (str) or index (int)
        """
        self.connected = False
        self.is_receiving = False
        self._pending_connect = True
        self.select_source(name_or_index)
    
    def _update_fps_counters(self):
        """Update FPS counters for monitoring"""
        current_time = time.time()
        self.fps_counter += 1
        
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.last_fps_time)
            self.fps_counter = 0
            self.last_fps_time = current_time
    
    def get_performance_stats(self):
        """
        Get comprehensive performance statistics
        
        Returns:
            dict: Performance statistics
        """
        return {
            'current_fps': self.current_fps,
            'is_connected': self.connected,
            'is_receiving': self.is_receiving,
            'total_frames_received': self.total_frames_received,
            'current_source': self._source_name,
            'available_sources_count': len(self.available_sources),
            'desired_source': self.desired_source_name
        }
    
    def stop(self):
        """Stop NDI receiver and cleanup resources"""
        self.disconnect()


class NDI_Manager:
    """
    Manager class for NDI connections
    Provides high-level interface for NDI stream management
    """
    
    def __init__(self, config=None):
        """
        Initialize NDI manager
        
        Args:
            config: Optional config object
        """
        self.receiver = None
        self.config = config
        self.is_connected = False
    
    def create_receiver(self, config=None):
        """
        Create new NDI receiver
        
        Args:
            config: Optional config object
            
        Returns:
            NDI_Receiver: New receiver instance
        """
        self.config = config or self.config
        self.receiver = NDI_Receiver(config=self.config)
        return self.receiver
    
    def connect(self, source_name_or_index, config=None) -> bool:
        """
        Connect to NDI stream
        
        Args:
            source_name_or_index: Source name (str) or index (int)
            config: Optional config object
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self.receiver:
            self.receiver.disconnect()
        
        self.config = config or self.config
        self.receiver = NDI_Receiver(config=self.config)
        self.receiver.select_source(source_name_or_index)
        
        # Wait a bit for connection
        time.sleep(0.1)
        self.is_connected = self.receiver.connected
        return self.is_connected
    
    def disconnect(self):
        """Disconnect from NDI stream"""
        if self.receiver:
            self.receiver.disconnect()
            self.receiver = None
        self.is_connected = False
    
    def get_receiver(self):
        """Get current receiver instance"""
        return self.receiver
    
    def is_stream_active(self) -> bool:
        """Check if stream is active"""
        return self.is_connected and self.receiver and self.receiver.is_receiving

