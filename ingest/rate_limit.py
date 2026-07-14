from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import time

from shared.config import get_settings


@dataclass
class RateLimiter:
    limit_per_minute: int
    _events: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: Lock = field(default_factory=Lock)

    def allow(self, key: str) -> bool:
        now = time()
        window_start = now - 60.0

        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self.limit_per_minute:
                return False

            bucket.append(now)
            return True


_rate_limiter = RateLimiter(limit_per_minute=get_settings().ingest_rate_limit_per_minute)


def check_rate_limit(org_id: str) -> bool:
    return _rate_limiter.allow(org_id)


def reset_rate_limiter() -> None:
    global _rate_limiter
    get_settings.cache_clear()
    _rate_limiter = RateLimiter(limit_per_minute=get_settings().ingest_rate_limit_per_minute)
