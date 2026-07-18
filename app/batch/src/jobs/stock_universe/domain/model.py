from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class StockUniverseStock:
    market: str
    stock_code: str
    stock_name: str
    volume: int


@dataclass(frozen=True)
class StockUniverseSelectionResult:
    stocks: list[StockUniverseStock]
    source_row_count: int
    valid_row_count: int
    excluded_counts: Mapping[str, int] = field(default_factory=dict)
    duplicate_stock_code_count: int = 0
