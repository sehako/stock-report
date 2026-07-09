"""Retry decision policy for stock processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class RetryDecision:
    status: str
    next_retry_at: datetime | None


class RetryPolicy:
    def __init__(self, *, max_retries: int, retry_interval: timedelta) -> None:
        self._max_attempts = 1 + max_retries
        self._retry_interval = retry_interval

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def retry_interval(self) -> timedelta:
        return self._retry_interval

    def decide(self, *, attempt_count: int, now: datetime) -> RetryDecision:
        if attempt_count < self._max_attempts:
            return RetryDecision("RETRYABLE", now + self._retry_interval)
        return RetryDecision("FAILED_PERMANENT", None)
