"""
TikTok Rhythm Style Plugin

Punchy, catchy rhythm popular in short-form video content.
Emphasizes downbeats with quick, snappy note attacks.
"""

from styles.registry import InputStyle


def register(registry):
    """Register TikTok-style rhythm."""
    registry.register(InputStyle(
        name="tiktok_rhythm",
        timing_offset_ms=(0, 12),
        stagger_ms=5,
        duration_variation=-0.15,
        description_en="TikTok style: punchy, catchy rhythm",
        description_zh="抖音节奏：有力且洗脑的节拍",
    ))
