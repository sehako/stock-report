from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ReloadMarketIndexDailyPriceCommand:
    index_code: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class MarketIndexDailyPriceFailedIndex:
    index_code: str
    reason: str


@dataclass(frozen=True)
class MarketIndexDailyPriceResult:
    total_index_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    saved_price_count: int
    failed_indexes: list[MarketIndexDailyPriceFailedIndex] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return True
