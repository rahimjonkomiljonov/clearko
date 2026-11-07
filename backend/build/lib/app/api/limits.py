"""Small in-memory sliding-window rate limiter (one process, no extra dependency)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    """`limits` is a list of (max_events, window_seconds). All of them must allow the request."""

    def __init__(
        self, limits: list[tuple[int, float]], clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limits = limits
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> float | None:
        """Record a request. Returns None if allowed, else seconds until it would be allowed."""
        now = self._clock()
        longest = max(w for _, w in self._limits)
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > longest:
                hits.popleft()
            wait = 0.0
            for max_events, window in self._limits:
                recent = [t for t in hits if now - t <= window]
                if len(recent) >= max_events:
                    wait = max(wait, window - (now - recent[0]))
            if wait > 0:
                return wait
            hits.append(now)
            if len(self._hits) > 10_000:  # forget clients that have gone quiet
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > longest]:
                    del self._hits[k]
            return None
