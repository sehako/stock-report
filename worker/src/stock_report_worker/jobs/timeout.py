"""Timeout boundary for external stock data calls."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import TypeVar

T = TypeVar("T")


class StockFetchTimeout(Exception):
    """Raised when an external stock fetch exceeds the configured timeout."""


class TimeoutRunner:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    def run(self, task: Callable[[], T]) -> T:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task)
        try:
            result = future.result(timeout=self._timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            raise StockFetchTimeout(
                f"stock fetch timed out after {self._timeout_seconds:g} seconds"
            ) from exc
        except Exception:
            executor.shutdown(wait=True)
            raise
        executor.shutdown(wait=True)
        return result
