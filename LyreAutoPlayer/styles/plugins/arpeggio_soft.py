"""
Soft Arpeggio Style Plugin

Gentle chord staggering for a smooth, flowing sound.
"""

from styles.registry import InputStyle


def register(registry):
    """Register the soft arpeggio style."""
    registry.register(InputStyle(
        name="arpeggio_soft",
        timing_offset_ms=(-6, 8),
        stagger_ms=18,
        duration_variation=0.08,
        description_en="Soft arpeggio: gentle chord staggering",
        description_zh="柔和琶音化：和弦轻微错开",
    ))
