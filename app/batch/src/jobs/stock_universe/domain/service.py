from collections import Counter
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from jobs.stock_universe.domain.model import StockUniverseSelectionResult, StockUniverseStock


DEFAULT_SELECTION_SIZE = 200
SUPPORTED_MARKETS = {"KOSPI", "KOSDAQ"}


class StockUniverseSelectionError(ValueError):
    pass


def select_top_volume_stocks(
    rows: Any,
    selection_size: int = DEFAULT_SELECTION_SIZE,
) -> StockUniverseSelectionResult:
    source_rows = _to_records(rows)
    excluded_counts: Counter[str] = Counter()
    by_code: dict[str, StockUniverseStock] = {}
    duplicate_count = 0

    for row in source_rows:
        stock_code = _normalize_text(_value(row, "Code", "Symbol", "stock_code"))
        stock_name = _normalize_text(_value(row, "Name", "stock_name"))
        market = _normalize_market(_value(row, "Market", "MarketId", "market"))

        if not stock_code:
            excluded_counts["missing_stock_code"] += 1
            continue
        if not stock_name:
            excluded_counts["missing_stock_name"] += 1
            continue
        if market not in SUPPORTED_MARKETS:
            excluded_counts["unsupported_market"] += 1
            continue

        stock = StockUniverseStock(
            market=market,
            stock_code=stock_code,
            stock_name=stock_name,
            volume=_parse_volume(_value(row, "Volume", "volume")),
        )
        previous = by_code.get(stock.stock_code)
        if previous is None:
            by_code[stock.stock_code] = stock
            continue

        duplicate_count += 1
        if (stock.volume, _code_sort_key(stock.stock_code)) > (
            previous.volume,
            _code_sort_key(previous.stock_code),
        ):
            by_code[stock.stock_code] = stock

    valid_stocks = list(by_code.values())
    if len(valid_stocks) < selection_size:
        raise StockUniverseSelectionError(
            f"거래량 상위 {selection_size}개를 선정하려면 유효 종목이 최소 {selection_size}개 필요합니다."
        )

    selected = sorted(valid_stocks, key=lambda stock: (-stock.volume, _code_sort_key(stock.stock_code)))[
        :selection_size
    ]
    return StockUniverseSelectionResult(
        stocks=selected,
        source_row_count=len(source_rows),
        valid_row_count=len(valid_stocks),
        excluded_counts=dict(excluded_counts),
        duplicate_stock_code_count=duplicate_count,
    )


def stock_code_digest(stock_codes: Iterable[str]) -> str:
    import hashlib

    payload = "\n".join(sorted(stock_codes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _to_records(rows: Any) -> list[Mapping[str, Any]]:
    if hasattr(rows, "to_dict"):
        return list(rows.to_dict("records"))
    return list(rows)


def _value(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _normalize_text(value: Any) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


def _normalize_market(value: Any) -> str:
    market = _normalize_text(value).upper()
    if market == "KOSDAQ GLOBAL":
        return "KOSDAQ"
    return market


def _parse_volume(value: Any) -> int:
    if _is_missing(value):
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        return max(0, int(Decimal(text)))
    except (InvalidOperation, ValueError):
        return 0


def _code_sort_key(stock_code: str) -> str:
    return stock_code.zfill(6)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(value != value)
    except Exception:
        return False
