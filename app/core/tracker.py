"""
Core window tracking and idle detection logic.
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, AsyncGenerator, List

import pygetwindow as gw
from pynput import mouse, keyboard

from app.core.models import WindowEvent
from app.core.database import save_event, get_active_event, close_active_event


@dataclass
class TrackerState:
    """Current state of the tracker."""
    current_window: Optional[WindowEvent] = None
    is_idle: bool = False
    idle_start_time: Optional[float] = None
    last_input_time: float = field(default_factory=time.time)


class WindowTracker:
    """
    Tracks the active foreground window and detects idle state.
    
    Designed to run in a background task without blocking the UI event loop.
    """
    
    def __init__(self, idle_threshold: float = 60.0):
        """
        Initialize the window tracker.
        
        Args:
            idle_threshold: Seconds of no input before considered idle.
        """
        self.idle_threshold = idle_threshold
        self.state = TrackerState()
        self._running = False
        self._poll_interval = 1.0  # Check every 1 second
        self._input_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
    def start_input_monitoring(self):
        """Start monitoring mouse and keyboard input for idle detection."""
        def on_input_event(*args, **kwargs):
            """Callback for any input event - updates last input time."""
            self.state.last_input_time = time.time()
        
        # Start mouse listener
        self._input_listener = mouse.Listener(
            on_move=on_input_event,
            on_click=on_input_event,
            on_scroll=on_input_event
        )
        self._input_listener.start()
        
        # Start keyboard listener
        self._keyboard_listener = keyboard.Listener(
            on_press=on_input_event,
            on_release=on_input_event
        )
        self._keyboard_listener.start()
        
    def stop_input_monitoring(self):
        """Stop monitoring input."""
        if self._input_listener:
            self._input_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
    
    def get_foreground_window(self) -> Optional[WindowEvent]:
        """
        Get the current foreground window information.
        
        Returns:
            WindowEvent with current window info, or None if no window found.
        """
        try:
            window = gw.getActiveWindow()
            if window is None:
                return None
            
            # Get process info from window title
            # pygetwindow doesn't directly provide process name, so we use the title
            # For more detailed process info, we'd need to use psutil
            return WindowEvent(
                process_name=self._extract_process_name(window.title),
                window_title=window.title,
                process_id=hash(window.title),  # Use hash as pseudo-ID
                start_time=time.time()
            )
        except Exception:
            # Handle cases where window access is restricted
            return None
    
    def _extract_process_name(self, window_title: str) -> str:
        """
        Extract a process name from window title.
        
        This is a simplified approach; production would use psutil for accuracy.
        """
        # Common patterns: "App - Document", "App Window", etc.
        if " - " in window_title:
            return window_title.split(" - ")[-1].strip()
        return window_title[:50].strip() if window_title else "Unknown"
    
    def check_idle(self) -> bool:
        """
        Check if the user is currently idle.
        
        Returns:
            True if no input detected within idle_threshold.
        """
        elapsed = time.time() - self.state.last_input_time
        return elapsed >= self.idle_threshold
    
    async def track(self, on_event_callback: Optional[Callable] = None) -> AsyncGenerator[Optional[WindowEvent], None]:
        """
        Main tracking loop - runs as a background task.
        
        Args:
            on_event_callback: Optional callback when an event is completed and saved.
        
        Yields:
            WindowEvent when the active window changes or idle state changes.
        """
        self._running = True
        self.start_input_monitoring()
        
        try:
            while self._running:
                current_window = self.get_foreground_window()
                is_idle = self.check_idle()
                
                # Handle idle state transition
                if is_idle and not self.state.is_idle:
                    # Just became idle - close current window event
                    if self.state.current_window:
                        self.state.current_window.end_time = time.time()
                        # Save to database
                        await save_event(self.state.current_window)
                        if on_event_callback:
                            await on_event_callback(self.state.current_window)
                        yield self.state.current_window
                    
                    self.state.is_idle = True
                    self.state.idle_start_time = time.time()
                    
                    # Yield idle event (don't save yet, wait for resume)
                    idle_event = WindowEvent(
                        process_name="IDLE",
                        window_title="User Idle",
                        process_id=0,
                        start_time=time.time(),
                        is_idle=True
                    )
                    self.state.current_window = idle_event
                    yield idle_event
                    
                elif not is_idle and self.state.is_idle:
                    # Just resumed from idle
                    self.state.is_idle = False
                    self.state.idle_start_time = None
                    
                    # Close and save idle event
                    if self.state.current_window and self.state.current_window.is_idle:
                        self.state.current_window.end_time = time.time()
                        await save_event(self.state.current_window)
                        if on_event_callback:
                            await on_event_callback(self.state.current_window)
                        yield self.state.current_window
                    
                    # Start tracking current window
                    if current_window:
                        self.state.current_window = current_window
                        yield current_window
                        
                elif not is_idle and current_window:
                    # Check if window changed
                    if (self.state.current_window is None or 
                        current_window.window_title != self.state.current_window.window_title):
                        # Close and save previous window event
                        if self.state.current_window and not self.state.current_window.is_idle:
                            self.state.current_window.end_time = time.time()
                            await save_event(self.state.current_window)
                            if on_event_callback:
                                await on_event_callback(self.state.current_window)
                            yield self.state.current_window
                        
                        # Start new window event
                        self.state.current_window = current_window
                        yield current_window
                
                await asyncio.sleep(self._poll_interval)
                
        finally:
            self._running = False
            self.stop_input_monitoring()
            # Save any active event on shutdown
            if self.state.current_window and not self.state.current_window.is_idle:
                self.state.current_window.end_time = time.time()
                await save_event(self.state.current_window)
    
    def stop(self):
        """Stop the tracking loop."""
        self._running = False
        
    def get_current_state(self) -> dict:
        """
        Get the current tracker state for UI display.
        
        Returns:
            Dictionary with current window and idle info.
        """
        return {
            "current_window": self.state.current_window.window_title if self.state.current_window else None,
            "current_app": self.state.current_window.process_name if self.state.current_window else None,
            "is_idle": self.state.is_idle,
            "idle_duration": time.time() - self.state.idle_start_time if self.state.idle_start_time else 0,
        }
