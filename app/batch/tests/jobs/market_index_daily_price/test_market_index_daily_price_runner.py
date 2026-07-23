from datetime import date

import pandas as pd

import pytest

from jobs.market_index_daily_price.application.dto import ReloadMarketIndexDailyPriceCommand
from jobs.market_index_daily_price.application.market_index_daily_price_runner import (
    MarketIndexDailyPriceRunner,
)


class FakeMarketIndexPriceClient:
    def __init__(self, rows_by_index_code=None, failures_by_index_code=None):
        self._rows_by_index_code = rows_by_index_code or {}
        self._failures_by_index_code = failures_by_index_code or {}
        self.calls = []

    def fetch_daily_prices(self, target, last_loaded_date=None, start_date=None, end_date=None):
        self.calls.append((target.index_code, target.fdr_symbol, last_loaded_date, start_date, end_date))
        if target.index_code in self._failures_by_index_code:
            raise RuntimeError(self._failures_by_index_code[target.index_code])
        return self._rows_by_index_code[target.index_code]


class FakeMarketIndexDailyPriceRepository:
    def __init__(self, last_loaded_dates=None, failures_by_index_code=None):
        self._last_loaded_dates = last_loaded_dates or {}
        self._failures_by_index_code = failures_by_index_code or {}
        self.last_loaded_date_calls = []
        self.saved_prices = []

    def find_last_loaded_date(self, index_code):
        self.last_loaded_date_calls.append(index_code)
        return self._last_loaded_dates.get(index_code)

    def upsert_market_index_prices(self, index_code, prices):
        if index_code in self._failures_by_index_code:
            raise RuntimeError(self._failures_by_index_code[index_code])
        self.saved_prices.append((index_code, list(prices)))
        return len(prices)


def test_runner_saves_successful_index_and_skips_empty_source():
    kospi_rows = pd.DataFrame(
        [
            {
                "Open": 2700,
                "High": 2720,
                "Low": 2680,
                "Close": 2710,
                "Volume": 1200000,
                "Change": 0.012,
            }
        ],
        index=pd.to_datetime(["2026-07-17"]),
    )
    client = FakeMarketIndexPriceClient(
        rows_by_index_code={
            "KOSPI": kospi_rows,
            "KOSDAQ": pd.DataFrame(),
        }
    )
    repository = FakeMarketIndexDailyPriceRepository(
        last_loaded_dates={"KOSPI": date(2026, 7, 16)}
    )
    runner = MarketIndexDailyPriceRunner(client, repository)

    result = runner.run()

    assert result.total_index_count == 2
    assert result.success_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 0
    assert result.saved_price_count == 1
    assert result.failed_indexes == []
    assert result.is_success is True
    assert repository.last_loaded_date_calls == ["KOSPI", "KOSDAQ"]
    assert client.calls == [
        ("KOSPI", "KS11", date(2026, 7, 16), None, None),
        ("KOSDAQ", "KQ11", None, None, None),
    ]
    assert repository.saved_prices[0][0] == "KOSPI"
    assert repository.saved_prices[0][1][0].index_code == "KOSPI"


def test_runner_records_failed_index_and_continues_next_index():
    kosdaq_rows = pd.DataFrame(
        [
            {
                "Open": 880,
                "High": 890,
                "Low": 870,
                "Close": 885,
                "Volume": 900000,
                "Change": 0.003,
            }
        ],
        index=pd.to_datetime(["2026-07-17"]),
    )
    client = FakeMarketIndexPriceClient(
        rows_by_index_code={"KOSDAQ": kosdaq_rows},
        failures_by_index_code={"KOSPI": "FDR failed"},
    )
    repository = FakeMarketIndexDailyPriceRepository()
    runner = MarketIndexDailyPriceRunner(client, repository)

    result = runner.run()

    assert result.total_index_count == 2
    assert result.success_count == 1
    assert result.skipped_count == 0
    assert result.failed_count == 1
    assert result.saved_price_count == 1
    assert result.failed_indexes[0].index_code == "KOSPI"
    assert result.failed_indexes[0].reason == "FDR failed"
    assert client.calls == [
        ("KOSPI", "KS11", None, None, None),
        ("KOSDAQ", "KQ11", None, None, None),
    ]
    assert repository.saved_prices[0][0] == "KOSDAQ"


def test_runner_does_not_raise_when_all_indexes_fail():
    client = FakeMarketIndexPriceClient(
        rows_by_index_code={
            "KOSPI": pd.DataFrame(
                [{"Open": None, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000}],
                index=pd.to_datetime(["2026-07-17"]),
            ),
            "KOSDAQ": pd.DataFrame(
                [{"Open": 880, "High": 890, "Low": 870, "Close": 885, "Volume": 900000}],
                index=pd.to_datetime(["2026-07-17"]),
            ),
        }
    )
    repository = FakeMarketIndexDailyPriceRepository(failures_by_index_code={"KOSDAQ": "DB failed"})
    runner = MarketIndexDailyPriceRunner(client, repository)

    result = runner.run()

    assert result.total_index_count == 2
    assert result.success_count == 0
    assert result.skipped_count == 0
    assert result.failed_count == 2
    assert result.saved_price_count == 0
    assert [failed.index_code for failed in result.failed_indexes] == ["KOSPI", "KOSDAQ"]
    assert result.is_success is True


def test_runner_reloads_single_index_for_requested_period_only():
    rows = pd.DataFrame(
        [
            {"Open": 2600, "High": 2650, "Low": 2590, "Close": 2640, "Volume": 1000, "Change": 0.01},
            {"Open": 2700, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000, "Change": 0.012},
            {"Open": 2800, "High": 2820, "Low": 2780, "Close": 2810, "Volume": 1300000, "Change": 0.02},
        ],
        index=pd.to_datetime(["2023-12-29", "2024-01-15", "2024-02-01"]),
    )
    client = FakeMarketIndexPriceClient(rows_by_index_code={"KOSPI": rows})
    repository = FakeMarketIndexDailyPriceRepository()
    runner = MarketIndexDailyPriceRunner(client, repository)
    command = ReloadMarketIndexDailyPriceCommand(
        index_code="kospi",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    result = runner.run(command)

    assert result.total_index_count == 1
    assert result.success_count == 1
    assert result.saved_price_count == 1
    assert repository.last_loaded_date_calls == []
    assert client.calls == [("KOSPI", "KS11", None, date(2024, 1, 1), date(2024, 1, 31))]
    assert repository.saved_prices[0][0] == "KOSPI"
    assert [price.trade_date for price in repository.saved_prices[0][1]] == [date(2024, 1, 15)]


def test_runner_fails_single_index_reload_before_external_call_when_index_is_not_supported():
    client = FakeMarketIndexPriceClient()
    repository = FakeMarketIndexDailyPriceRepository()
    runner = MarketIndexDailyPriceRunner(client, repository)
    command = ReloadMarketIndexDailyPriceCommand(
        index_code="UNKNOWN",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    with pytest.raises(ValueError, match="지원하지 않는 지수 코드입니다"):
        runner.run(command)

    assert client.calls == []
    assert repository.saved_prices == []


def test_runner_fails_single_index_reload_when_saved_count_is_zero():
    rows = pd.DataFrame(
        [
            {"Open": 2700, "High": 2720, "Low": 2680, "Close": 2710, "Volume": 1200000},
        ],
        index=pd.to_datetime(["2024-01-15"]),
    )

    class ZeroSaveRepository(FakeMarketIndexDailyPriceRepository):
        def upsert_market_index_prices(self, index_code, prices):
            self.saved_prices.append((index_code, list(prices)))
            return 0

    client = FakeMarketIndexPriceClient(rows_by_index_code={"KOSDAQ": rows})
    runner = MarketIndexDailyPriceRunner(client, ZeroSaveRepository())
    command = ReloadMarketIndexDailyPriceCommand(
        index_code="KosDaQ",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    with pytest.raises(RuntimeError, match="저장된 지수 일봉 row가 없습니다"):
        runner.run(command)
