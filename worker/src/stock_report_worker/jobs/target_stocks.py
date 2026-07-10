"""Target stock provider boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from stock_report_worker.krx.normalization import KrxListedStock


@dataclass(frozen=True)
class TargetStock:
    id: int
    selection_rank: int = 0
    selection_volume: int = 0
    stock_code: str = ""
    stock_name_snapshot: str = ""
    market_snapshot: str = ""
    industry_name_snapshot: str | None = None
    selection_close_price: Decimal = Decimal("0")


class TargetStockProvider(Protocol):
    def list_for(self, report_date: date) -> list[TargetStock]:
        """Return target stocks for the batch."""


class KrxStockListingCollector(Protocol):
    def collect(self, now: datetime) -> list[KrxListedStock]:
        """Collect listed KRX stocks with persisted stock ids."""


class InMemoryTargetStockProvider:
    def __init__(self, stock_ids: list[int] | None = None) -> None:
        self._stock_ids = stock_ids or []

    def list_for(self, report_date: date) -> list[TargetStock]:
        return [TargetStock(id=stock_id) for stock_id in self._stock_ids]


class KrxTargetStockProvider:
    def __init__(
        self,
        listing_provider: KrxStockListingCollector,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._listing_provider = listing_provider
        self._now = now

    def list_for(self, report_date: date) -> list[TargetStock]:
        return select_target_stocks(self._listing_provider.collect(self._now()))


def select_target_stocks(listed_stocks: list[KrxListedStock]) -> list[TargetStock]:
    eligible = [
        stock
        for stock in listed_stocks
        if stock.listing_close_price >= Decimal("1000")
    ]
    ordered = sorted(eligible, key=lambda stock: (-stock.listing_volume, stock.stock_code))[:200]
    targets: list[TargetStock] = []
    for index, stock in enumerate(ordered, start=1):
        if stock.stock_id is None:
            raise ValueError(f"listed stock has no stock_id: {stock.stock_code}")
        targets.append(
            TargetStock(
                id=stock.stock_id,
                selection_rank=index,
                selection_volume=stock.listing_volume,
                stock_code=stock.stock_code,
                stock_name_snapshot=stock.stock_name,
                market_snapshot=stock.market,
                industry_name_snapshot=stock.industry_name,
                selection_close_price=stock.listing_close_price,
            )
        )
    return targets
