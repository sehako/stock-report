from datetime import date
from types import SimpleNamespace

import pandas as pd

from jobs.market_index_daily_price.domain.model import MarketIndexTarget
from jobs.market_index_daily_price.infrastructure.client.finance_data_reader_client import (
    FinanceDataReaderMarketIndexPriceClient,
)


def test_fetch_daily_prices_uses_target_symbol_and_early_start_for_initial_load(monkeypatch):
    calls = []
    expected = pd.DataFrame()

    def data_reader(symbol, start):
        calls.append((symbol, start))
        return expected

    monkeypatch.setitem(
        __import__("sys").modules,
        "FinanceDataReader",
        SimpleNamespace(DataReader=data_reader),
    )
    client = FinanceDataReaderMarketIndexPriceClient()
    target = MarketIndexTarget(index_code="KOSPI", fdr_symbol="KS11")

    result = client.fetch_daily_prices(target, None)

    assert result is expected
    assert calls == [("KS11", "1900-01-01")]


def test_fetch_daily_prices_starts_at_next_day_after_last_loaded_date(monkeypatch):
    calls = []

    def data_reader(symbol, start):
        calls.append((symbol, start))
        return pd.DataFrame()

    monkeypatch.setitem(
        __import__("sys").modules,
        "FinanceDataReader",
        SimpleNamespace(DataReader=data_reader),
    )
    client = FinanceDataReaderMarketIndexPriceClient()
    target = MarketIndexTarget(index_code="KOSDAQ", fdr_symbol="KQ11")

    client.fetch_daily_prices(target, date(2026, 7, 17))

    assert calls == [("KQ11", "2026-07-18")]
