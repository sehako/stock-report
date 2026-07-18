from dataclasses import dataclass


@dataclass(frozen=True)
class StockUniverseResult:
    source_row_count: int
    valid_row_count: int
    selected_count: int
    excluded_counts: dict[str, int]
    duplicate_stock_code_count: int
    untracked_count: int
    selected_digest: str
    tracked_digest: str
    digest_matched: bool
