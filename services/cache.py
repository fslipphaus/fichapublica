"""Cache em memória simples, adequado ao MVP em uma instância Render."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: str, producer: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            cached = self._values.get(key)
            if cached and cached[0] > now:
                return cached[1]
        value = producer()
        with self._lock:
            self._values[key] = (now + self.ttl_seconds, value)
        return value

