from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from jobs.stock_daily_price.domain.service import (
    StockDailyPriceNormalizationError,
    normalize_stock_daily_prices,
)


def test_normalizes_fdr_rows_to_daily_price_models():
    rows = pd.DataFrame(
        [
            {
                "Open": 1000,
                "High": 1100,
                "Low": 900,
                "Close": 1050,
                "Volume": 12000,
                "Change": 0.05,
            }
        ],
        index=pd.to_datetime(["2026-07-17"]),
    )

    result = normalize_stock_daily_prices(stock_id=10, rows=rows)

    assert result.excluded_row_count == 0
    assert result.duplicate_trade_date_count == 0
    assert result.prices[0].stock_id == 10
    assert result.prices[0].trade_date == date(2026, 7, 17)
    assert result.prices[0].open_price == Decimal("1000")
    assert result.prices[0].high_price == Decimal("1100")
    assert result.prices[0].low_price == Decimal("900")
    assert result.prices[0].close_price == Decimal("1050")
    assert result.prices[0].volume == 12000
    assert result.prices[0].change_rate == Decimal("0.05")


def test_normalizes_missing_or_invalid_change_as_none():
    rows = pd.DataFrame(
        [
            {"Open": 1000, "High": 1100, "Low": 900, "Close": 1050, "Volume": 12000},
            {
                "Open": 2000,
                "High": 2100,
                "Low": 1900,
                "Close": 2050,
                "Volume": 22000,
                "Change": "not-a-number",
            },
        ],
        index=pd.to_datetime(["2026-07-16", "2026-07-17"]),
    )

    result = normalize_stock_daily_prices(stock_id=10, rows=rows)

    assert [price.change_rate for price in result.prices] == [None, None]


def test_excludes_only_rows_with_missing_required_values():
    rows = pd.DataFrame(
        [
            {"Open": None, "High": 1100, "Low": 900, "Close": 1050, "Volume": 12000},
            {
                "Open": 2000,
                "High": 2100,
                "Low": 1900,
                "Close": 2050,
                "Volume": 22000,
                "Change": 0.025,
            },
        ],
        index=pd.to_datetime(["2026-07-16", "2026-07-17"]),
    )

    result = normalize_stock_daily_prices(stock_id=10, rows=rows)

    assert result.excluded_row_count == 1
    assert len(result.prices) == 1
    assert result.prices[0].trade_date == date(2026, 7, 17)


def test_keeps_last_row_when_trade_date_is_duplicated():
    rows = pd.DataFrame(
        [
            {
                "Open": 1000,
                "High": 1100,
                "Low": 900,
                "Close": 1050,
                "Volume": 12000,
                "Change": 0.05,
            },
            {
                "Open": 2000,
                "High": 2100,
                "Low": 1900,
                "Close": 2050,
                "Volume": 22000,
                "Change": 0.025,
            },
        ],
        index=pd.to_datetime(["2026-07-17", "2026-07-17"]),
    )

    result = normalize_stock_daily_prices(stock_id=10, rows=rows)

    assert result.duplicate_trade_date_count == 1
    assert len(result.prices) == 1
    assert result.prices[0].open_price == Decimal("2000")


def test_raises_when_no_rows_can_be_saved():
    rows = pd.DataFrame(
        [{"Open": None, "High": 1100, "Low": 900, "Close": 1050, "Volume": 12000}],
        index=pd.to_datetime(["2026-07-17"]),
    )

    with pytest.raises(StockDailyPriceNormalizationError):
        normalize_stock_daily_prices(stock_id=10, rows=rows)
