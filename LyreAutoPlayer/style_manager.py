"""
Style Manager - 输入风格管理模块

从 main.py 抽取的风格系统，现在使用插件化的 StyleRegistry：
1. InputStyle - 基础输入风格参数 (从 styles.registry 导入)
2. INPUT_STYLES - 预设风格字典 (从 registry 动态获取)
3. EightBarStyle - 八小节变奏参数
4. EIGHT_BAR_PRESETS - 八小节预设

Author: LyreAutoPlayer Refactor
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List

# Import from plugin system
from styles.registry import InputStyle, StyleRegistry
from styles.loader import get_default_registry


# ============================================================================
# Registry-backed Style Access
# ============================================================================

def _get_registry() -> StyleRegistry:
    """Get the global style registry (lazy initialization)."""
    return get_default_registry()


# Legacy compatibility: INPUT_STYLES as a property-like accessor
class _StylesProxy:
    """Proxy object that makes registry look like a dict for backward compatibility."""

    def get(self, name: str, default=None):
        """Get style by name, with optional default value (like dict.get)."""
        result = _get_registry().get(name)
        return result if result is not None else default

    def keys(self):
        return _get_registry().get_names()

    def values(self):
        return [_get_registry().get(n) for n in _get_registry().get_names()]

    def items(self):
        reg = _get_registry()
        return [(n, reg.get(n)) for n in reg.get_names()]

    def __getitem__(self, name: str) -> InputStyle:
        style = _get_registry().get(name)
        if style is None:
            raise KeyError(name)
        return style

    def __setitem__(self, name: str, style: InputStyle):
        """Support INPUT_STYLES[name] = style assignment."""
        _get_registry().register(style)

    def __delitem__(self, name: str):
        """Support del INPUT_STYLES[name]."""
        if not _get_registry().unregister(name):
            raise KeyError(name)

    def __contains__(self, name: str) -> bool:
        return name in _get_registry()

    def __iter__(self):
        return iter(_get_registry().get_names())

    def __len__(self):
        return len(_get_registry())


# Backward compatible INPUT_STYLES (now backed by registry)
INPUT_STYLES = _StylesProxy()


# ============================================================================
# Eight-Bar Style System (八小节风格变奏)
# ============================================================================

# Random variation applied to selected 8-bar sections
# Selection patterns: skip N bars, then apply variation to 1 bar

@dataclass
class EightBarStyle:
    """Eight-bar section style variation settings."""
    enabled: bool = False

    # Variation mode:
    # "warp" = Tempo Warp (time compression/stretch, sections shift in time) - PRIORITY
    # "beat_lock" = Beat-Lock Micro Timing (beat grid stays fixed, only intervals change)
    mode: str = "warp"

    # Selection pattern: how frequently to apply variation
    # "skip3_pick1": skip 3 sections, vary 1 (every 4th section)
    # "skip2_pick1": skip 2 sections, vary 1 (every 3rd section)
    # "skip1_pick1": skip 1 section, vary 1 (every 2nd section)
    # "continuous": apply variation to every section
    selection_pattern: str = "skip2_pick1"

    # Speed multiplier range (relative to current speed, not absolute)
    # e.g., (0.9, 1.1) means 90% to 110% of current speed
    speed_mult_min: float = 0.95
    speed_mult_max: float = 1.05

    # Timing offset multiplier range (applies to press timing)
    # e.g., (0.9, 1.1) means timing offsets are scaled 90%-110%
    timing_mult_min: float = 0.9
    timing_mult_max: float = 1.1

    # Duration multiplier range (affects note hold duration)
    # e.g., (0.8, 1.2) means 80%-120% of original duration
    duration_mult_min: float = 0.9
    duration_mult_max: float = 1.1

    # Global clamp for variation multipliers
    clamp_enabled: bool = False
    clamp_min: float = 0.85
    clamp_max: float = 1.15

    # Whether to show indicator when 8-bar variation is active
    show_indicator: bool = True


EIGHT_BAR_PRESETS: Dict[str, EightBarStyle] = {
    "subtle": EightBarStyle(
        enabled=True,
        selection_pattern="skip2_pick1",
        speed_mult_min=0.97, speed_mult_max=1.03,
        timing_mult_min=0.95, timing_mult_max=1.05,
        duration_mult_min=0.95, duration_mult_max=1.05,
    ),
    "moderate": EightBarStyle(
        enabled=True,
        selection_pattern="skip1_pick1",
        speed_mult_min=0.93, speed_mult_max=1.07,
        timing_mult_min=0.9, timing_mult_max=1.1,
        duration_mult_min=0.9, duration_mult_max=1.1,
    ),
    "dramatic": EightBarStyle(
        enabled=True,
        selection_pattern="skip1_pick1",
        speed_mult_min=0.88, speed_mult_max=1.12,
        timing_mult_min=0.85, timing_mult_max=1.15,
        duration_mult_min=0.85, duration_mult_max=1.15,
    ),
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_style(name: str) -> Optional[InputStyle]:
    """获取指定名称的输入风格"""
    return _get_registry().get(name)


def get_style_names() -> List[str]:
    """获取所有可用风格名称（按注册顺序）"""
    return _get_registry().get_names()


def get_sorted_style_names() -> List[str]:
    """获取所有可用风格名称（按字母排序）"""
    return _get_registry().get_sorted_names()


def register_style(style: InputStyle) -> bool:
    """注册一个新风格"""
    return _get_registry().register(style)


def unregister_style(name: str) -> bool:
    """取消注册一个风格（内置风格不可删除）"""
    return _get_registry().unregister(name)


def get_eight_bar_preset(name: str) -> Optional[EightBarStyle]:
    """获取指定名称的八小节预设"""
    return EIGHT_BAR_PRESETS.get(name)


def get_eight_bar_preset_names() -> List[str]:
    """获取所有八小节预设名称"""
    return sorted(EIGHT_BAR_PRESETS.keys())


# ============================================================================
# Plugin Management
# ============================================================================

def reload_style_plugins() -> List[str]:
    """重新加载所有风格插件（开发用）"""
    from styles.loader import reload_plugins
    return reload_plugins()


def get_plugin_styles() -> List[str]:
    """获取所有插件风格名称（非内置）"""
    reg = _get_registry()
    return [name for name in reg.get_names()
            if not reg.get(name).builtin]
