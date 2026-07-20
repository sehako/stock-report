from datetime import date
from typing import Protocol

from jobs.market_index_daily_price.domain.model import MarketIndexDailyPrice


class MarketIndexDailyPriceRepository(Protocol):
    def find_last_loaded_date(self, index_code: str) -> date | None:
        """Return the latest loaded trade date for one market index."""

    def upsert_market_index_prices(self, index_code: str, prices: list[MarketIndexDailyPrice]) -> int:
        """Insert or update daily prices for one market index."""

