from dataclasses import dataclass, field


@dataclass(frozen=True)
class StockDailyPriceFailedStock:
    stock_id: int
    stock_code: str
    stock_name: str
    reason: str


@dataclass(frozen=True)
class StockDailyPriceResult:
    total_stock_count: int
    success_count: int
    skipped_count: int
    failed_count: int
    saved_price_count: int
    failed_stocks: list[StockDailyPriceFailedStock] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return True
