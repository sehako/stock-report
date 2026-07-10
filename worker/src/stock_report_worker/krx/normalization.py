"""Normalize FinanceDataReader KRX listing frames."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

import pandas as pd


class KrxStockListingUnavailable(Exception):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason
        self.message = message


class KrxStockListingUnavailableReason(StrEnum):
    KRX_LISTING_FETCH_FAILED = "KRX_LISTING_FETCH_FAILED"
    KRX_DESC_FETCH_FAILED = "KRX_DESC_FETCH_FAILED"
    SOURCE_COLUMNS_MISSING = "SOURCE_COLUMNS_MISSING"
    SOURCE_VALUES_INVALID = "SOURCE_VALUES_INVALID"
    STOCK_UPSERT_FAILED = "STOCK_UPSERT_FAILED"


@dataclass(frozen=True)
class KrxListedStock:
    stock_code: str
    stock_name: str
    market: str
    industry_name: str | None
    listing_close_price: Decimal
    listing_volume: int
    stock_id: int | None = None

    def with_stock_id(self, stock_id: int) -> "KrxListedStock":
        return replace(self, stock_id=stock_id)


LISTING_COLUMN_ALIASES = {
    "code": ("Code", "Symbol", "stock_code", "종목코드"),
    "name": ("Name", "stock_name", "종목명"),
    "market": ("Market", "MarketId", "market", "시장구분"),
    "close": ("Close", "listing_close_price", "종가"),
    "volume": ("Volume", "listing_volume", "거래량"),
}

DESC_COLUMN_ALIASES = {
    "code": ("Code", "Symbol", "stock_code", "종목코드"),
    "industry": ("Sector", "Industry", "industry_name", "업종", "업종명"),
}

MARKET_ALIASES = {
    "KOSPI": "KOSPI",
    "STK": "KOSPI",
    "KS": "KOSPI",
    "유가증권": "KOSPI",
    "코스피": "KOSPI",
    "KOSDAQ": "KOSDAQ",
    "KSQ": "KOSDAQ",
    "KQ": "KOSDAQ",
    "코스닥": "KOSDAQ",
    "KONEX": "KONEX",
    "KNX": "KONEX",
    "코넥스": "KONEX",
}


def normalize_krx_stock_listing(
    listing_frame: pd.DataFrame, desc_frame: pd.DataFrame
) -> list[KrxListedStock]:
    listing_columns = _resolve_columns(listing_frame, LISTING_COLUMN_ALIASES, "KRX")
    desc_columns = _resolve_columns(desc_frame, DESC_COLUMN_ALIASES, "KRX-DESC")
    industries = _industry_by_code(desc_frame, desc_columns)

    listed_stocks: list[KrxListedStock] = []
    seen_codes: set[str] = set()
    for index, row in listing_frame.iterrows():
        stock_code = _normalize_stock_code(row[listing_columns["code"]], index)
        if stock_code in seen_codes:
            _invalid("stock_code", index)
        seen_codes.add(stock_code)
        listed_stocks.append(
            KrxListedStock(
                stock_code=stock_code,
                stock_name=_normalize_required_text(row[listing_columns["name"]], "stock_name", index),
                market=_normalize_market(row[listing_columns["market"]], index),
                industry_name=industries.get(stock_code),
                listing_close_price=_normalize_decimal(
                    row[listing_columns["close"]], "listing_close_price", index
                ),
                listing_volume=_normalize_int(row[listing_columns["volume"]], "listing_volume", index),
            )
        )
    return listed_stocks


def _resolve_columns(
    frame: pd.DataFrame, aliases: dict[str, tuple[str, ...]], source_name: str
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical_name, candidates in aliases.items():
        column = next((candidate for candidate in candidates if candidate in frame.columns), None)
        if column is None:
            missing.append(canonical_name)
        else:
            resolved[canonical_name] = column
    if missing:
        raise KrxStockListingUnavailable(
            KrxStockListingUnavailableReason.SOURCE_COLUMNS_MISSING,
            f"{source_name} missing columns: {', '.join(missing)}",
        )
    return resolved


def _industry_by_code(frame: pd.DataFrame, columns: dict[str, str]) -> dict[str, str | None]:
    industries: dict[str, str | None] = {}
    for index, row in frame.iterrows():
        stock_code = _normalize_stock_code(row[columns["code"]], index)
        industries[stock_code] = _normalize_optional_text(row[columns["industry"]])
    return industries


def _normalize_stock_code(value: Any, row_index: Any) -> str:
    if pd.isna(value):
        _invalid("stock_code", row_index)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text.isdigit():
        _invalid("stock_code", row_index)
    return text.zfill(6)


def _normalize_required_text(value: Any, field_name: str, row_index: Any) -> str:
    text = _normalize_optional_text(value)
    if text is None:
        _invalid(field_name, row_index)
    return text


def _normalize_optional_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = " ".join(str(value).split())
    return text or None


def _normalize_market(value: Any, row_index: Any) -> str:
    text = _normalize_required_text(value, "market", row_index)
    return MARKET_ALIASES.get(text.upper(), "UNKNOWN")


def _normalize_decimal(value: Any, field_name: str, row_index: Any) -> Decimal:
    if pd.isna(value):
        _invalid(field_name, row_index)
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        _invalid(field_name, row_index)


def _normalize_int(value: Any, field_name: str, row_index: Any) -> int:
    decimal_value = _normalize_decimal(value, field_name, row_index)
    if decimal_value != decimal_value.to_integral_value():
        _invalid(field_name, row_index)
    return int(decimal_value)


def _invalid(field_name: str, row_index: Any) -> None:
    raise KrxStockListingUnavailable(
        KrxStockListingUnavailableReason.SOURCE_VALUES_INVALID,
        f"invalid {field_name} at row {row_index}",
    )
