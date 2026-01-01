"""
Style Registry - Core style definitions and registry.

InputStyle dataclass defines humanization parameters.
StyleRegistry provides style registration and lookup.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Optional


@dataclass
class InputStyle:
    """
    Input style parameters for humanization.

    Attributes:
        name: Unique identifier for the style
        timing_offset_ms: (min, max) random timing offset in milliseconds
        stagger_ms: Milliseconds between simultaneous notes (chord staggering)
        duration_variation: Variation factor for note duration (0.0-0.3, negative for shorter)
        description_en: English description
        description_zh: Chinese description
    """
    name: str
    timing_offset_ms: Tuple[int, int] = (0, 0)
    stagger_ms: int = 0
    duration_variation: float = 0.0
    description_en: str = ""
    description_zh: str = ""

    # Whether this is a built-in style (cannot be deleted by user)
    builtin: bool = False


class StyleRegistry:
    """
    Registry for input styles.

    Manages both built-in and plugin styles.
    """

    def __init__(self):
        self._styles: Dict[str, InputStyle] = {}
        self._load_order: List[str] = []  # Track registration order

    def register(self, style: InputStyle) -> bool:
        """
        Register a style.

        Args:
            style: The InputStyle to register

        Returns:
            True if registered successfully, False if name already exists
        """
        if style.name in self._styles:
            # Allow overwriting non-builtin styles
            if self._styles[style.name].builtin:
                return False

        self._styles[style.name] = style
        if style.name not in self._load_order:
            self._load_order.append(style.name)
        return True

    def unregister(self, name: str) -> bool:
        """
        Unregister a style by name.

        Args:
            name: Style name to remove

        Returns:
            True if removed, False if not found or is builtin
        """
        if name not in self._styles:
            return False
        if self._styles[name].builtin:
            return False

        del self._styles[name]
        if name in self._load_order:
            self._load_order.remove(name)
        return True

    def get(self, name: str) -> Optional[InputStyle]:
        """Get a style by name."""
        return self._styles.get(name)

    def get_all(self) -> Dict[str, InputStyle]:
        """Get all registered styles."""
        return self._styles.copy()

    def get_names(self) -> List[str]:
        """Get all style names in registration order."""
        return self._load_order.copy()

    def get_sorted_names(self) -> List[str]:
        """Get all style names sorted alphabetically."""
        return sorted(self._styles.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._styles

    def __len__(self) -> int:
        return len(self._styles)


# ============== Built-in Styles ==============

# Technical background on humanization parameters:
# - Timing offset: +/-5-15ms micro-timing variation sounds natural
# - Stagger: 10-25ms per note in chords simulates finger rolling
# - Duration variation: +/-10-20% adds expressiveness

BUILTIN_STYLES: List[InputStyle] = [
    InputStyle(
        name="mechanical",
        timing_offset_ms=(0, 0),
        stagger_ms=0,
        duration_variation=0.0,
        description_en="Precise, robotic timing",
        description_zh="精确机械，无变化",
        builtin=True,
    ),
    InputStyle(
        name="natural",
        timing_offset_ms=(-8, 8),
        stagger_ms=15,
        duration_variation=0.10,
        description_en="Slight human-like variation",
        description_zh="轻微人性化变化",
        builtin=True,
    ),
    InputStyle(
        name="expressive",
        timing_offset_ms=(-15, 15),
        stagger_ms=25,
        duration_variation=0.20,
        description_en="More dynamic, emotional feel",
        description_zh="更多动态和情感表达",
        builtin=True,
    ),
    InputStyle(
        name="aggressive",
        timing_offset_ms=(-5, 20),
        stagger_ms=8,
        duration_variation=0.15,
        description_en="Fast attack, punchy rhythm",
        description_zh="快速有力，强节奏感",
        builtin=True,
    ),
    InputStyle(
        name="legato",
        timing_offset_ms=(-5, 5),
        stagger_ms=20,
        duration_variation=0.25,
        description_en="Smooth, connected notes",
        description_zh="连贯流畅，音符连接",
        builtin=True,
    ),
    InputStyle(
        name="staccato",
        timing_offset_ms=(-3, 3),
        stagger_ms=5,
        duration_variation=-0.30,
        description_en="Short, detached notes",
        description_zh="断奏短促，音符分离",
        builtin=True,
    ),
    InputStyle(
        name="swing",
        timing_offset_ms=(5, 25),
        stagger_ms=12,
        duration_variation=0.15,
        description_en="Jazz swing feel",
        description_zh="爵士摇摆节奏",
        builtin=True,
    ),
    InputStyle(
        name="rubato",
        timing_offset_ms=(-25, 25),
        stagger_ms=30,
        duration_variation=0.30,
        description_en="Free tempo, romantic expression",
        description_zh="自由速度，浪漫表达",
        builtin=True,
    ),
    InputStyle(
        name="ballad",
        timing_offset_ms=(-15, 5),
        stagger_ms=35,
        duration_variation=0.20,
        description_en="Slow, emotional ballad style",
        description_zh="慢速抒情，情感丰富",
        builtin=True,
    ),
    InputStyle(
        name="lazy",
        timing_offset_ms=(-20, -5),
        stagger_ms=18,
        duration_variation=0.12,
        description_en="Laid-back, behind the beat",
        description_zh="慵懒放松，节奏略后",
        builtin=True,
    ),
    InputStyle(
        name="rushed",
        timing_offset_ms=(5, 15),
        stagger_ms=6,
        duration_variation=0.08,
        description_en="Urgent, ahead of the beat",
        description_zh="紧迫急促，节奏略前",
        builtin=True,
    ),
]


def create_default_registry() -> StyleRegistry:
    """Create a new registry with all built-in styles."""
    reg = StyleRegistry()
    for style in BUILTIN_STYLES:
        reg.register(style)
    return reg
