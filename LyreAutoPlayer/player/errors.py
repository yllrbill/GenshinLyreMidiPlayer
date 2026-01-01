# -*- coding: utf-8 -*-
"""
Error simulation for human-like mistakes.
"""

import random
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class ErrorType:
    """Extensible error type definition."""
    name: str                    # Internal name
    display_name_en: str         # English display name
    display_name_zh: str         # Chinese display name
    enabled: bool = True
    # Type-specific parameters
    offset_range: Tuple[int, int] = (0, 0)   # For wrong_note/extra_note: semitone offset
    pause_min_ms: int = 0                     # For pause: min duration
    pause_max_ms: int = 0                     # For pause: max duration


DEFAULT_ERROR_TYPES = {
    "wrong_note": ErrorType(
        name="wrong_note",
        display_name_en="Wrong Note",
        display_name_zh="错音",
        offset_range=(-1, 1),
    ),
    "miss_note": ErrorType(
        name="miss_note",
        display_name_en="Miss Note",
        display_name_zh="漏音",
    ),
    "extra_note": ErrorType(
        name="extra_note",
        display_name_en="Extra Note",
        display_name_zh="重音",
        offset_range=(-1, 1),
    ),
    "pause": ErrorType(
        name="pause",
        display_name_en="Pause",
        display_name_zh="断音",
        pause_min_ms=100,
        pause_max_ms=500,
    ),
}


@dataclass
class ErrorConfig:
    """Configuration for human-like mistakes."""
    enabled: bool = False

    # Error frequency (per 8 bars)
    errors_per_8bars: int = 1

    # Enabled error types (multi-select)
    wrong_note: bool = True      # Wrong note (adjacent key)
    miss_note: bool = True       # Miss note (skip)
    extra_note: bool = True      # Extra note (additional adjacent key)
    pause_error: bool = True     # Pause (interrupt playback)

    # Pause duration range (ms)
    pause_min_ms: int = 100
    pause_max_ms: int = 500


def plan_errors_for_group(error_config: ErrorConfig) -> List[Tuple[str, float]]:
    """
    Plan errors for an 8-bar group based on configuration.

    Args:
        error_config: ErrorConfig with enabled error types

    Returns:
        List of (error_type, relative_position) where relative_position is 0.0-1.0
        within the 8-bar group
    """
    if not error_config.enabled or error_config.errors_per_8bars <= 0:
        return []

    # Collect enabled error types
    enabled_types = []
    if error_config.wrong_note:
        enabled_types.append("wrong_note")
    if error_config.miss_note:
        enabled_types.append("miss_note")
    if error_config.extra_note:
        enabled_types.append("extra_note")
    if error_config.pause_error:
        enabled_types.append("pause")

    if not enabled_types:
        return []

    # Plan errors with random positions
    errors = []
    for _ in range(error_config.errors_per_8bars):
        error_type = random.choice(enabled_types)
        # Random position within 8-bar group (0.0 to 1.0)
        position = random.random()
        errors.append((error_type, position))

    # Sort by position for ordered application
    errors.sort(key=lambda x: x[1])
    return errors
