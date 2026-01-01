# -*- coding: utf-8 -*-
"""
Event Bus Module.

Provides a publish/subscribe mechanism for decoupling components.

Usage:
    from core.events import EventBus, EventType, get_event_bus

    bus = get_event_bus()

    # Subscribe to events
    def on_play_start():
        print("Playback started!")

    bus.subscribe(EventType.PLAY_START, on_play_start)

    # Publish events
    bus.publish(EventType.PLAY_START)

    # Unsubscribe
    bus.unsubscribe(EventType.PLAY_START, on_play_start)
"""

from enum import Enum
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
import threading
import weakref


class EventType(Enum):
    """Event types for the application."""

    # Playback control
    PLAY_START = "play_start"
    PLAY_STOP = "play_stop"
    PLAY_PAUSE = "play_pause"
    PLAY_RESUME = "play_resume"
    PLAY_PROGRESS = "play_progress"  # (current, total)
    PLAY_FINISHED = "play_finished"

    # Configuration changes
    CONFIG_CHANGED = "config_changed"  # (domain, key, value)
    LANGUAGE_CHANGED = "language_changed"  # (new_lang)

    # Hotkeys
    HOTKEY_TRIGGERED = "hotkey_triggered"  # (action)

    # Logging
    LOG_MESSAGE = "log_message"  # (level, message)

    # UI
    UI_REFRESH = "ui_refresh"
    FLOATING_TOGGLE = "floating_toggle"

    # Error simulation
    ERROR_INJECTED = "error_injected"  # (error_type, note)

    # Eight-bar style
    BAR_START = "bar_start"  # (bar_number)
    BAR_END = "bar_end"  # (bar_number)


@dataclass
class Event:
    """Event data container."""
    type: EventType
    data: Dict[str, Any]
    source: Optional[str] = None


class EventBus:
    """
    Event Bus for publish/subscribe pattern.

    Thread-safe implementation with support for:
    - Multiple subscribers per event type
    - Weak references to prevent memory leaks
    - Async publishing (for Qt thread safety)
    """

    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to invoke when event is published.
                     Can accept *args, **kwargs matching publish() call.
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                    return True
                except ValueError:
                    pass
        return False

    def publish(self, event_type: EventType, *args, **kwargs) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event to publish
            *args: Positional arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers

        Returns:
            Number of handlers that were called
        """
        handlers = []
        with self._lock:
            if event_type in self._subscribers:
                handlers = self._subscribers[event_type].copy()

        count = 0
        for handler in handlers:
            try:
                handler(*args, **kwargs)
                count += 1
            except Exception as e:
                # Log error but don't break other handlers
                print(f"[EventBus] Error in handler for {event_type}: {e}")

        return count

    def publish_async(self, event_type: EventType, *args, **kwargs) -> None:
        """
        Publish an event asynchronously (in a separate thread).

        Useful for Qt thread safety when publishing from worker threads.

        Args:
            event_type: Type of event to publish
            *args: Positional arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        thread = threading.Thread(
            target=self.publish,
            args=(event_type,) + args,
            kwargs=kwargs,
            daemon=True
        )
        thread.start()

    def clear(self, event_type: EventType = None) -> None:
        """
        Clear all subscribers.

        Args:
            event_type: If provided, only clear subscribers for this type.
                       Otherwise, clear all subscribers.
        """
        with self._lock:
            if event_type is not None:
                self._subscribers.pop(event_type, None)
            else:
                self._subscribers.clear()

    def subscriber_count(self, event_type: EventType) -> int:
        """
        Get number of subscribers for an event type.

        Args:
            event_type: Type of event

        Returns:
            Number of subscribers
        """
        with self._lock:
            return len(self._subscribers.get(event_type, []))


# Convenience function
def get_event_bus() -> EventBus:
    """Get the global EventBus instance."""
    return EventBus.get_instance()


# Export all
__all__ = [
    'EventType',
    'EventBus',
    'Event',
    'get_event_bus',
]
