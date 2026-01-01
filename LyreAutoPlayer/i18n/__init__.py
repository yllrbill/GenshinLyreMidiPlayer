# -*- coding: utf-8 -*-
"""
i18n module for LyreAutoPlayer.

Provides translation support with tr() function.

Usage:
    from i18n import tr, LANG_EN, LANG_ZH

    text = tr("window_title", LANG_ZH)  # Returns "里拉琴自动演奏器 (21/36键)"
"""

from .translations import (
    TRANSLATIONS,
    LANG_EN,
    LANG_ZH,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)

# Current language state (can be changed at runtime)
_current_language = DEFAULT_LANGUAGE


def tr(key: str, lang: str = None) -> str:
    """
    Get translated string for the given key.

    Args:
        key: Translation key (e.g., "window_title")
        lang: Language code (LANG_EN or LANG_ZH).
              If None, uses current language.

    Returns:
        Translated string, or the key itself if not found.
    """
    if lang is None:
        lang = _current_language
    return TRANSLATIONS.get(key, {}).get(lang, key)


def set_language(lang: str) -> None:
    """
    Set the current language for tr() calls without explicit lang parameter.

    Args:
        lang: Language code (LANG_EN or LANG_ZH)
    """
    global _current_language
    if lang in SUPPORTED_LANGUAGES:
        _current_language = lang


def get_language() -> str:
    """
    Get the current language.

    Returns:
        Current language code
    """
    return _current_language


def get_all_keys() -> list:
    """
    Get all available translation keys.

    Returns:
        List of translation keys
    """
    return list(TRANSLATIONS.keys())


__all__ = [
    'tr',
    'set_language',
    'get_language',
    'get_all_keys',
    'TRANSLATIONS',
    'LANG_EN',
    'LANG_ZH',
    'SUPPORTED_LANGUAGES',
    'DEFAULT_LANGUAGE',
]
