"""
Dreamy Style Plugin

Ethereal, floating timing with gentle sustains.
Perfect for ambient and relaxing music.
"""

from styles.registry import InputStyle


def register(registry):
    """Register dreamy style."""
    registry.register(InputStyle(
        name="dreamy",
        timing_offset_ms=(-18, 12),
        stagger_ms=28,
        duration_variation=0.22,
        description_en="Dreamy: ethereal, floating timing",
        description_zh="梦幻风格：飘渺轻柔的节奏",
    ))
