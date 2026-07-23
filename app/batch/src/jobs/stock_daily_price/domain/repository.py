from typing import Protocol

from jobs.stock_daily_price.domain.model import StockDailyPrice, TrackedStock


class StockDailyPriceRepository(Protocol):
    def find_tracked_stocks_with_last_loaded_date(self) -> list[TrackedStock]:
        """Return tracked stocks with each stock's latest loaded trade date."""

    def find_stock_by_code(self, stock_code: str) -> TrackedStock | None:
        """Return one stock by stock code with its latest loaded trade date."""

    def upsert_stock_prices(self, stock_id: int, prices: list[StockDailyPrice]) -> int:
        """Insert or update daily prices for one stock."""
