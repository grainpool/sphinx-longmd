# Copyright 2026 Grainpool Holdings LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

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
