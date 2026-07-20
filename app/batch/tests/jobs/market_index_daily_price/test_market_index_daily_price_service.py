from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from jobs.market_index_daily_price.domain.model import SUPPORTED_MARKET_INDEX_TARGETS
from jobs.market_index_daily_price.domain.service import (
    MarketIndexDailyPriceNormalizationError,
    normalize_market_index_daily_prices,
)


def test_defines_supported_market_index_targets():
    assert [(target.index_code, target.fdr_symbol) for target in SUPPORTED_MARKET_INDEX_TARGETS] == [
        ("KOSPI", "KS11"),
        ("KOSDAQ", "KQ11"),
    ]


def test_normalizes_fdr_rows_to_market_index_daily_price_models():
    rows = pd.DataFrame(
        [
            {
                "Open": 2700.5,
                "High": 2720.25,
                "Low": 2680.75,
                "Close": 2710.1,
                "Volume": 1200000,
                "Change": 0.0123,
            }
        ],
        index=pd.to_datetime(["2026-07-17"]),
    )

    result = normalize_market_index_daily_prices(index_code="KOSPI", rows=rows)

    assert result.excluded_row_count == 0
    assert result.duplicate_trade_date_count == 0
    assert result.prices[0].index_code == "KOSPI"
    assert result.prices[0].trade_date == date(2026, 7, 17)
    assert result.prices[0].open_price == Decimal("2700.5")
    assert result.prices[0].high_price == Decimal("2720.25")
    assert result.prices[0].low_price == Decimal("2680.75")
    assert result.prices[0].close_price == Decimal("2710.1")
    assert result.prices[0].volume == 1200000
    assert result.prices[0].change_rate == Decimal("0.0123")


def test_normalizes_missing_or_invalid_change_as_none():
    rows = pd.DataFrame(
        [
            {"Open": 2700, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000},
            {
                "Open": 880,
                "High": 890,
                "Low": 870,
                "Close": 885,
                "Volume": 900000,
                "Change": "not-a-number",
            },
        ],
        index=pd.to_datetime(["2026-07-16", "2026-07-17"]),
    )

    result = normalize_market_index_daily_prices(index_code="KOSDAQ", rows=rows)

    assert [price.change_rate for price in result.prices] == [None, None]


def test_excludes_only_rows_with_missing_required_values():
    rows = pd.DataFrame(
        [
            {"Open": None, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000},
            {
                "Open": 880,
                "High": 890,
                "Low": 870,
                "Close": 885,
                "Volume": 900000,
                "Change": 0.003,
            },
        ],
        index=pd.to_datetime(["2026-07-16", "2026-07-17"]),
    )

    result = normalize_market_index_daily_prices(index_code="KOSDAQ", rows=rows)

    assert result.excluded_row_count == 1
    assert len(result.prices) == 1
    assert result.prices[0].trade_date == date(2026, 7, 17)


def test_keeps_last_row_when_trade_date_is_duplicated():
    rows = pd.DataFrame(
        [
            {
                "Open": 2700,
                "High": 2720,
                "Low": 2680,
                "Close": 2710,
                "Volume": 1200000,
                "Change": 0.012,
            },
            {
                "Open": 2750,
                "High": 2760,
                "Low": 2740,
                "Close": 2755,
                "Volume": 1300000,
                "Change": 0.015,
            },
        ],
        index=pd.to_datetime(["2026-07-17", "2026-07-17"]),
    )

    result = normalize_market_index_daily_prices(index_code="KOSPI", rows=rows)

    assert result.duplicate_trade_date_count == 1
    assert len(result.prices) == 1
    assert result.prices[0].open_price == Decimal("2750")


def test_raises_when_source_rows_exist_but_no_rows_can_be_saved():
    rows = pd.DataFrame(
        [{"Open": None, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000}],
        index=pd.to_datetime(["2026-07-17"]),
    )

    with pytest.raises(MarketIndexDailyPriceNormalizationError):
        normalize_market_index_daily_prices(index_code="KOSPI", rows=rows)
