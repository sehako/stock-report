"""Target stock provider boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class TargetStock:
    id: int


class TargetStockProvider(Protocol):
    def list_for(self, report_date: date) -> list[TargetStock]:
        """Return target stocks for the batch."""


class InMemoryTargetStockProvider:
    def __init__(self, stock_ids: list[int] | None = None) -> None:
        self._stock_ids = stock_ids or []

    def list_for(self, report_date: date) -> list[TargetStock]:
        return [TargetStock(id=stock_id) for stock_id in self._stock_ids]
