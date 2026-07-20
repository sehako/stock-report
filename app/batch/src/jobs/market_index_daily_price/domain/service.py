from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from jobs.market_index_daily_price.domain.model import (
    MarketIndexDailyPrice,
    MarketIndexDailyPriceCollectionResult,
)


class MarketIndexDailyPriceNormalizationError(ValueError):
    pass


def normalize_market_index_daily_prices(
    index_code: str,
    rows: Any,
) -> MarketIndexDailyPriceCollectionResult:
    records = _to_indexed_records(rows)
    prices_by_date: dict[date, MarketIndexDailyPrice] = {}
    excluded_count = 0
    duplicate_count = 0

    for trade_date_value, row in records:
        trade_date = _parse_trade_date(trade_date_value)
        open_price = _parse_required_decimal(_value(row, "Open"))
        high_price = _parse_required_decimal(_value(row, "High"))
        low_price = _parse_required_decimal(_value(row, "Low"))
        close_price = _parse_required_decimal(_value(row, "Close"))
        volume = _parse_required_int(_value(row, "Volume"))
        if (
            trade_date is None
            or open_price is None
            or high_price is None
            or low_price is None
            or close_price is None
            or volume is None
        ):
            excluded_count += 1
            continue

        if trade_date in prices_by_date:
            duplicate_count += 1
        prices_by_date[trade_date] = MarketIndexDailyPrice(
            index_code=index_code,
            trade_date=trade_date,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            change_rate=_parse_optional_decimal(_value(row, "Change")),
        )

    prices = [prices_by_date[trade_date] for trade_date in sorted(prices_by_date)]
    if not prices:
        raise MarketIndexDailyPriceNormalizationError("저장 가능한 지수 일봉 row가 없습니다.")
    return MarketIndexDailyPriceCollectionResult(
        prices=prices,
        excluded_row_count=excluded_count,
        duplicate_trade_date_count=duplicate_count,
    )


def _to_indexed_records(rows: Any) -> list[tuple[Any, Mapping[str, Any]]]:
    if hasattr(rows, "iterrows"):
        return [(index, row.to_dict()) for index, row in rows.iterrows()]
    return [(row.get("Date") or row.get("trade_date"), row) for row in rows]


def _value(row: Mapping[str, Any], key: str) -> Any:
    return row[key] if key in row else None


def _parse_trade_date(value: Any) -> date | None:
    if _is_missing(value):
        return None
    to_pydatetime = getattr(value, "to_pydatetime", None)
    if to_pydatetime is not None:
        return to_pydatetime().date()
    if isinstance(value, date):
        return value
    try:
        import pandas as pd

        parsed = pd.to_datetime(value)
        if _is_missing(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _parse_required_decimal(value: Any) -> Decimal | None:
    if _is_missing(value):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _parse_optional_decimal(value: Any) -> Decimal | None:
    return _parse_required_decimal(value)


def _parse_required_int(value: Any) -> int | None:
    decimal_value = _parse_required_decimal(value)
    if decimal_value is None:
        return None
    return int(decimal_value)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(value != value)
    except Exception:
        return False
