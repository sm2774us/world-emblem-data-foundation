"""Failure recovery primitives: bounded exponential backoff with jitter-free determinism for tests."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class TransientError(Exception):
    """Raised by extractors for retryable failures (timeouts, 429, 5xx)."""


def retry(
    fn: Callable[[], T],
    attempts: int = 4,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[T, int]:
    last: Exception | None = None
    for n in range(1, attempts + 1):
        try:
            return fn(), n
        except TransientError as exc:
            last = exc
            if n < attempts:
                sleep(base_delay * 2 ** (n - 1))
    raise TransientError(f"gave up after {attempts} attempts: {last}")
