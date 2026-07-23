from datetime import date
from types import SimpleNamespace

import pandas as pd

from jobs.stock_daily_price.infrastructure.client.finance_data_reader_client import (
    FinanceDataReaderStockPriceClient,
)


def test_fetch_daily_prices_uses_stock_code_and_early_start_for_initial_load(monkeypatch):
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
    client = FinanceDataReaderStockPriceClient()

    result = client.fetch_daily_prices("005930", None)

    assert result is expected
    assert calls == [("005930", "1900-01-01")]


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
    client = FinanceDataReaderStockPriceClient()

    client.fetch_daily_prices("005930", date(2026, 7, 17))

    assert calls == [("005930", "2026-07-18")]


def test_fetch_daily_prices_uses_requested_period_when_dates_are_provided(monkeypatch):
    calls = []

    def data_reader(symbol, start, end):
        calls.append((symbol, start, end))
        return pd.DataFrame()

    monkeypatch.setitem(
        __import__("sys").modules,
        "FinanceDataReader",
        SimpleNamespace(DataReader=data_reader),
    )
    client = FinanceDataReaderStockPriceClient()

    client.fetch_daily_prices(
        "005930",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    assert calls == [("005930", "2024-01-01", "2024-01-31")]
