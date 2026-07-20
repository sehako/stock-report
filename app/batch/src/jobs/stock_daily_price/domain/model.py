from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class TrackedStock:
    stock_id: int
    market: str
    stock_code: str
    stock_name: str
    last_loaded_date: date | None


@dataclass(frozen=True)
class StockDailyPrice:
    stock_id: int
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    change_rate: Decimal | None


@dataclass(frozen=True)
class StockDailyPriceCollectionResult:
    prices: list[StockDailyPrice]
    excluded_row_count: int
    duplicate_trade_date_count: int
