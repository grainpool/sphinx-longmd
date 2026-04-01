"""Timing, counters, and warning aggregation.

Lightweight build-local diagnostics written into the sidecar ``stats``
section.  No separate telemetry service.
"""

from __future__ import annotations

import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class Diagnostics:
    """Accumulates stats for one build run."""

    timers: dict[str, float] = field(default_factory=dict)
    counters: Counter[str] = field(default_factory=Counter)
    node_class_counts: Counter[str] = field(default_factory=Counter)

    _timer_starts: dict[str, float] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Timer helpers
    # ------------------------------------------------------------------

    def start_timer(self, name: str) -> None:
        self._timer_starts[name] = time.monotonic()

    def stop_timer(self, name: str) -> None:
        started = self._timer_starts.pop(name, None)
        if started is not None:
            elapsed = (time.monotonic() - started) * 1000  # ms
            self.timers[name] = self.timers.get(name, 0.0) + elapsed

    @contextmanager
    def timer(self, name: str) -> Generator[None, None, None]:
        self.start_timer(name)
        try:
            yield
        finally:
            self.stop_timer(name)

    # ------------------------------------------------------------------
    # Counter helpers
    # ------------------------------------------------------------------

    def inc(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def record_node(self, class_name: str) -> None:
        self.node_class_counts[class_name] += 1

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_stats_dict(self) -> dict[str, Any]:
        return {
            **{k: v for k, v in self.counters.items()},
            "node_class_counts": dict(self.node_class_counts),
            "timing_ms": {k: round(v, 2) for k, v in self.timers.items()},
        }
