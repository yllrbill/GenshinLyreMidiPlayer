# -*- coding: utf-8 -*-
"""
Event scheduling with priority queue.
"""

from dataclasses import dataclass, field


@dataclass(order=True)
class KeyEvent:
    """
    Key press/release event for priority queue scheduling.

    Priority: lower number = higher priority
    For same time: release (1) before press (2) to avoid conflicts
    """
    time: float                           # Event time in seconds
    priority: int                         # 1=release, 2=press
    event_type: str = field(compare=False)  # "press" or "release"
    key: str = field(compare=False)       # Key character
    note: int = field(compare=False)      # MIDI note number (for sound)
    bar_index: int = field(compare=False, default=0)  # Original bar index for pause logic
