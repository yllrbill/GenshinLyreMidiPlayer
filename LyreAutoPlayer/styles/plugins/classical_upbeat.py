"""
Classical Upbeat (Anacrusis) Style Plugin

Subtle timing adjustments that emphasize pickup notes,
common in classical and romantic period music.
"""

from styles.registry import InputStyle


def register(registry):
    """Register classical upbeat style."""
    registry.register(InputStyle(
        name="classical_upbeat",
        timing_offset_ms=(-10, 5),
        stagger_ms=22,
        duration_variation=0.18,
        description_en="Classical upbeat: subtle anacrusis emphasis",
        description_zh="古典弱起：强调前奏小节的细腻处理",
    ))
