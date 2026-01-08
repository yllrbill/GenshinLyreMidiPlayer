# -*- coding: utf-8 -*-
"""
Event scheduling with priority queue and independent output scheduler thread.

The OutputScheduler runs key injection on a dedicated thread, preventing
playback timing from being affected by input latency or blocking.
"""

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Tuple


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
    token: int = field(compare=False, default=0)  # Press/release pairing token


class OutputScheduler:
    """
    Independent thread for executing key injection events.

    Features:
    - Thread-safe event queue with timing
    - Late-drop policy to skip stale events (prevents pile-up)
    - Pause/resume/stop support
    - Non-blocking release scheduling

    Usage:
        scheduler = OutputScheduler(input_manager, late_drop_ms=25)
        scheduler.start(playback_start_time)
        scheduler.enqueue(KeyEvent(...))
        # ... later ...
        scheduler.stop()
    """

    def __init__(
        self,
        press_fn: Callable[[str, Optional[int]], bool],
        release_fn: Callable[[str, Optional[int]], bool],
        late_drop_ms: float = 25.0,
        enable_late_drop: bool = True,
        log_fn: Optional[Callable[[str], None]] = None,
        event_log_fn: Optional[Callable[..., None]] = None,
        active_check_fn: Optional[Callable[[str], bool]] = None,
        retrigger_release_fn: Optional[Callable[[str, Optional[int]], bool]] = None,
        retrigger_gap_ms: float = 2.0,
    ):
        """
        Args:
            press_fn: Function to call for key press (key, note) -> success
            release_fn: Function to call for key release (key, note) -> success
            late_drop_ms: Drop events older than this (ms behind schedule)
            enable_late_drop: Whether to enable late-drop policy
            log_fn: Optional logging function
        """
        self._press_fn = press_fn
        self._release_fn = release_fn
        self._late_drop_ms = late_drop_ms
        self._enable_late_drop = enable_late_drop
        self._log_fn = log_fn or (lambda msg: None)
        self._event_log_fn = event_log_fn
        self._active_check_fn = active_check_fn
        self._retrigger_release_fn = retrigger_release_fn or release_fn
        self._retrigger_gap_ms = retrigger_gap_ms

        # Thread-safe event queue
        self._queue: List[KeyEvent] = []
        self._queue_lock = threading.Lock()
        self._queue_not_empty = threading.Condition(self._queue_lock)

        # State
        self._running = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially not paused
        self._stop_event = threading.Event()

        # Timing
        self._playback_start: float = 0.0
        self._total_pause_time: float = 0.0
        self._pause_start: float = 0.0

        # Thread
        self._thread: Optional[threading.Thread] = None

        # Stats
        self._stats = {
            "events_executed": 0,
            "events_dropped": 0,
            "max_late_ms": 0.0,
            "avg_late_ms": 0.0,
        }

    def start(self, playback_start_time: Optional[float] = None):
        """Start the scheduler thread."""
        if self._running:
            return

        self._playback_start = playback_start_time or time.perf_counter()
        self._total_pause_time = 0.0
        self._running = True
        self._stop_event.clear()
        self._pause_event.set()
        self._paused = False

        # Clear queue
        with self._queue_lock:
            self._queue.clear()

        # Reset stats
        self._stats = {
            "events_executed": 0,
            "events_dropped": 0,
            "max_late_ms": 0.0,
            "avg_late_ms": 0.0,
        }

        self._thread = threading.Thread(target=self._run, daemon=True, name="OutputScheduler")
        self._thread.start()

    def stop(self):
        """Stop the scheduler thread and release all keys."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        self._pause_event.set()  # Wake up if paused

        # Wake up the queue wait
        with self._queue_lock:
            self._queue_not_empty.notify_all()

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def pause(self):
        """Pause event execution."""
        if not self._paused:
            self._paused = True
            self._pause_start = time.perf_counter()
            self._pause_event.clear()

    def resume(self):
        """Resume event execution."""
        if self._paused:
            pause_duration = time.perf_counter() - self._pause_start
            self._total_pause_time += pause_duration
            self._paused = False
            self._pause_event.set()

    def is_paused(self) -> bool:
        return self._paused

    def is_running(self) -> bool:
        return self._running

    def enqueue(self, event: KeyEvent):
        """Add an event to the queue (thread-safe)."""
        with self._queue_lock:
            heapq.heappush(self._queue, event)
            self._queue_not_empty.notify()

    def enqueue_batch(self, events: List[KeyEvent]):
        """Add multiple events to the queue (thread-safe)."""
        with self._queue_lock:
            for event in events:
                heapq.heappush(self._queue, event)
            self._queue_not_empty.notify()

    def clear_queue(self):
        """Clear all pending events."""
        with self._queue_lock:
            self._queue.clear()

    def get_queue_size(self) -> int:
        with self._queue_lock:
            return len(self._queue)

    def get_stats(self) -> Dict:
        return dict(self._stats)

    def _get_current_playback_time(self) -> float:
        """Get current playback time (accounting for pauses)."""
        return time.perf_counter() - self._playback_start - self._total_pause_time

    def _run(self):
        """Main scheduler loop."""
        while self._running and not self._stop_event.is_set():
            # Wait if paused
            self._pause_event.wait()

            if self._stop_event.is_set():
                break

            # Get next event
            event = None
            with self._queue_lock:
                while not self._queue and self._running and not self._stop_event.is_set():
                    # Wait for events with timeout
                    self._queue_not_empty.wait(timeout=0.1)
                    if not self._running or self._stop_event.is_set():
                        break

                if self._queue and self._running:
                    event = self._queue[0]  # Peek

            if event is None or self._stop_event.is_set():
                continue

            # Wait until event time
            current_time = self._get_current_playback_time()
            wait_time = event.time - current_time

            if wait_time > 0:
                # Wait with interruptibility
                self._stop_event.wait(timeout=min(wait_time, 0.05))
                if self._stop_event.is_set():
                    break
                if self._paused:
                    continue
                # Recalculate after wait
                current_time = self._get_current_playback_time()
                wait_time = event.time - current_time
                if wait_time > 0.001:
                    continue  # Not yet time

            # Pop the event
            queue_size = 0
            with self._queue_lock:
                if self._queue and self._queue[0] == event:
                    heapq.heappop(self._queue)
                    queue_size = len(self._queue)
                else:
                    continue  # Event was removed or changed

            # Calculate lateness
            late_ms = (current_time - event.time) * 1000
            active_before = None
            if self._active_check_fn and event.key:
                try:
                    active_before = self._active_check_fn(event.key)
                except Exception:
                    active_before = None

            # Late-drop policy: only drop press events, never drop release (avoid stuck keys)
            if self._enable_late_drop and late_ms > self._late_drop_ms and event.event_type == "press":
                self._stats["events_dropped"] += 1
                self._log_fn(f"[LateDrop] press '{event.key}' dropped ({late_ms:.1f}ms late)")
                if self._event_log_fn:
                    self._event_log_fn(
                        event=event,
                        scheduled_time=event.time,
                        actual_time=current_time,
                        late_ms=late_ms,
                        queue_size=queue_size,
                        executed=False,
                        dropped=True,
                        success=False,
                        active_before=active_before,
                    )
                continue

            # Update late stats
            if late_ms > 0:
                self._stats["max_late_ms"] = max(self._stats["max_late_ms"], late_ms)
                # Exponential moving average
                self._stats["avg_late_ms"] = self._stats["avg_late_ms"] * 0.9 + late_ms * 0.1

            # Execute event
            try:
                if event.event_type == "press":
                    if active_before:
                        self._retrigger_release_fn(event.key, event.note)
                        if self._retrigger_gap_ms > 0:
                            time.sleep(self._retrigger_gap_ms / 1000.0)
                    success = self._press_fn(event.key, event.note)
                elif event.event_type == "release":
                    success = self._release_fn(event.key, event.note)
                else:
                    success = False
                self._stats["events_executed"] += 1
                if self._event_log_fn:
                    self._event_log_fn(
                        event=event,
                        scheduled_time=event.time,
                        actual_time=current_time,
                        late_ms=late_ms,
                        queue_size=queue_size,
                        executed=True,
                        dropped=False,
                        success=success,
                        active_before=active_before,
                    )
            except Exception as e:
                self._log_fn(f"[Scheduler] Error executing {event.event_type}: {e}")
