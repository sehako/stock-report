from datetime import date

import pandas as pd

import pytest

from jobs.stock_daily_price.application.dto import ReloadStockDailyPriceCommand
from jobs.stock_daily_price.application.stock_daily_price_runner import StockDailyPriceRunner
from jobs.stock_daily_price.domain.model import TrackedStock


class FakeStockPriceClient:
    def __init__(self):
        self.calls = []

    def fetch_daily_prices(self, stock_code, last_loaded_date=None, start_date=None, end_date=None):
        self.calls.append((stock_code, last_loaded_date, start_date, end_date))
        if stock_code == "000002":
            return pd.DataFrame()
        if stock_code == "000003":
            raise RuntimeError("FDR failed")
        return pd.DataFrame(
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


class FakeStockDailyPriceRepository:
    def __init__(self):
        self.saved_prices = []
        self.stock_by_code = {
            "005930": TrackedStock(10, "KOSPI", "005930", "삼성전자", date(2024, 1, 15)),
            "000000": TrackedStock(99, "KOSPI", "000000", "저장실패", None),
        }

    def find_tracked_stocks_with_last_loaded_date(self):
        return [
            TrackedStock(1, "KOSPI", "000001", "성공", date(2026, 7, 16)),
            TrackedStock(2, "KOSPI", "000002", "스킵", None),
            TrackedStock(3, "KOSPI", "000003", "실패", None),
        ]

    def find_stock_by_code(self, stock_code):
        return self.stock_by_code.get(stock_code)

    def upsert_stock_prices(self, stock_id, prices):
        self.saved_prices.append((stock_id, list(prices)))
        if stock_id == 99:
            return 0
        return len(prices)


def test_runner_continues_after_empty_result_and_single_stock_failure():
    client = FakeStockPriceClient()
    repository = FakeStockDailyPriceRepository()
    runner = StockDailyPriceRunner(client, repository)

    result = runner.run()

    assert result.total_stock_count == 3
    assert result.success_count == 1
    assert result.skipped_count == 1
    assert result.failed_count == 1
    assert result.failed_stocks[0].stock_code == "000003"
    assert result.is_success is True
    assert client.calls == [
        ("000001", date(2026, 7, 16), None, None),
        ("000002", None, None, None),
        ("000003", None, None, None),
    ]
    assert repository.saved_prices[0][0] == 1


def test_runner_reloads_single_stock_for_requested_period_only():
    class TargetedClient:
        def __init__(self):
            self.calls = []

        def fetch_daily_prices(self, stock_code, last_loaded_date=None, start_date=None, end_date=None):
            self.calls.append((stock_code, last_loaded_date, start_date, end_date))
            return pd.DataFrame(
                [
                    {"Open": 900, "High": 950, "Low": 890, "Close": 940, "Volume": 1000, "Change": 0.01},
                    {"Open": 1000, "High": 1100, "Low": 900, "Close": 1050, "Volume": 12000, "Change": 0.05},
                    {"Open": 1100, "High": 1200, "Low": 1000, "Close": 1150, "Volume": 13000, "Change": 0.02},
                ],
                index=pd.to_datetime(["2023-12-29", "2024-01-15", "2024-02-01"]),
            )

    client = TargetedClient()
    repository = FakeStockDailyPriceRepository()
    runner = StockDailyPriceRunner(client, repository)
    command = ReloadStockDailyPriceCommand(
        stock_code="005930",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    result = runner.run(command)

    assert result.total_stock_count == 1
    assert result.success_count == 1
    assert result.saved_price_count == 1
    assert client.calls == [("005930", None, date(2024, 1, 1), date(2024, 1, 31))]
    assert repository.saved_prices[0][0] == 10
    assert [price.trade_date for price in repository.saved_prices[0][1]] == [date(2024, 1, 15)]


def test_runner_fails_single_stock_reload_before_external_call_when_stock_does_not_exist():
    client = FakeStockPriceClient()
    repository = FakeStockDailyPriceRepository()
    runner = StockDailyPriceRunner(client, repository)
    command = ReloadStockDailyPriceCommand(
        stock_code="123456",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )

    with pytest.raises(ValueError, match="종목을 찾을 수 없습니다"):
        runner.run(command)

    assert client.calls == []
    assert repository.saved_prices == []


def test_runner_fails_single_stock_reload_when_saved_count_is_zero():
    client = FakeStockPriceClient()
    repository = FakeStockDailyPriceRepository()
    runner = StockDailyPriceRunner(client, repository)
    command = ReloadStockDailyPriceCommand(
        stock_code="000000",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    with pytest.raises(RuntimeError, match="저장된 종목 일봉 row가 없습니다"):
        runner.run(command)
