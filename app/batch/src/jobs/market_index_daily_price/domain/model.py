from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class MarketIndexTarget:
    index_code: str
    fdr_symbol: str


SUPPORTED_MARKET_INDEX_TARGETS = [
    MarketIndexTarget(index_code="KOSPI", fdr_symbol="KS11"),
    MarketIndexTarget(index_code="KOSDAQ", fdr_symbol="KQ11"),
]


@dataclass(frozen=True)
class MarketIndexDailyPrice:
    index_code: str
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    change_rate: Decimal | None


@dataclass(frozen=True)
class MarketIndexDailyPriceCollectionResult:
    prices: list[MarketIndexDailyPrice]
    excluded_row_count: int
    duplicate_trade_date_count: int
