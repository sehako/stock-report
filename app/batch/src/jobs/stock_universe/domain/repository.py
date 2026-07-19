from typing import Protocol

from jobs.stock_universe.domain.model import StockUniverseStock


class StockUniverseRepository(Protocol):
    def replace_tracked_stocks(self, stocks: list[StockUniverseStock]) -> int:
        """Save selected stocks and untrack stocks outside the current selection."""

    def find_tracked_stock_codes(self) -> list[str]:
        """Return stock codes currently marked as tracked."""
