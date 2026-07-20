from datetime import date

import pandas as pd

from jobs.stock_daily_price.application.stock_daily_price_runner import StockDailyPriceRunner
from jobs.stock_daily_price.domain.model import TrackedStock


class FakeStockPriceClient:
    def __init__(self):
        self.calls = []

    def fetch_daily_prices(self, stock_code, last_loaded_date):
        self.calls.append((stock_code, last_loaded_date))
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

    def find_tracked_stocks_with_last_loaded_date(self):
        return [
            TrackedStock(1, "KOSPI", "000001", "성공", date(2026, 7, 16)),
            TrackedStock(2, "KOSPI", "000002", "스킵", None),
            TrackedStock(3, "KOSPI", "000003", "실패", None),
        ]

    def upsert_stock_prices(self, stock_id, prices):
        self.saved_prices.append((stock_id, list(prices)))
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
        ("000001", date(2026, 7, 16)),
        ("000002", None),
        ("000003", None),
    ]
    assert repository.saved_prices[0][0] == 1
