"""Exponential backoff with jitter for delivery retries."""
from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta


def compute_backoff(attempt: int) -> float:
    delay = min(10 * (2 ** (attempt - 1)), 3600) + random.uniform(0, 5)
    return delay


def next_attempt_at(attempt: int, retry_after: int | None = None) -> datetime:
    delay = compute_backoff(attempt)
    if retry_after is not None and retry_after > delay:
        delay = float(retry_after)
    return datetime.now(timezone.utc) + timedelta(seconds=delay)
