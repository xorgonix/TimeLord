"""
Data models for the TimeLord application.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowEvent:
    """Represents a tracked window event."""
    process_name: str
    window_title: str
    process_id: int
    start_time: float
    end_time: Optional[float] = None
    is_idle: bool = False
