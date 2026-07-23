from types import SimpleNamespace

import pytest

import batch.main as batch_main


class FakeStockUniverseRunner:
    result = SimpleNamespace(digest_matched=True)
    run_count = 0
    run_order = []

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def run(self):
        type(self).run_count += 1
        type(self).run_order.append("stock_universe")
        return type(self).result


class FakeStockDailyPriceRunner:
    run_count = 0
    run_order = []
    commands = []
    result = SimpleNamespace(is_success=True, saved_price_count=1)

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def run(self, command=None):
        type(self).run_count += 1
        type(self).run_order.append("stock_daily_price")
        type(self).commands.append(command)
        return type(self).result


class FakeMarketIndexDailyPriceRunner:
    run_count = 0
    run_order = []
    commands = []
    result = SimpleNamespace(is_success=True, saved_price_count=1)

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def run(self, command=None):
        type(self).run_count += 1
        type(self).run_order.append("market_index_daily_price")
        type(self).commands.append(command)
        return type(self).result


@pytest.fixture(autouse=True)
def reset_fake_runners():
    FakeStockUniverseRunner.result = SimpleNamespace(digest_matched=True)
    FakeStockUniverseRunner.run_count = 0
    FakeStockUniverseRunner.run_order = []
    FakeStockDailyPriceRunner.run_count = 0
    FakeStockDailyPriceRunner.run_order = []
    FakeStockDailyPriceRunner.commands = []
    FakeStockDailyPriceRunner.result = SimpleNamespace(is_success=True, saved_price_count=1)
    FakeMarketIndexDailyPriceRunner.run_count = 0
    FakeMarketIndexDailyPriceRunner.run_order = []
    FakeMarketIndexDailyPriceRunner.commands = []
    FakeMarketIndexDailyPriceRunner.result = SimpleNamespace(is_success=True, saved_price_count=1)


@pytest.fixture
def patched_main(monkeypatch):
    monkeypatch.setattr(batch_main, "load_batch_config", lambda: SimpleNamespace(log_level="INFO"))
    monkeypatch.setattr(batch_main, "configure_logging", lambda log_level: None)
    monkeypatch.setattr(batch_main, "StockUniverseRunner", FakeStockUniverseRunner)
    monkeypatch.setattr(batch_main, "StockDailyPriceRunner", FakeStockDailyPriceRunner)
    monkeypatch.setattr(batch_main, "MarketIndexDailyPriceRunner", FakeMarketIndexDailyPriceRunner)
    monkeypatch.setattr(batch_main, "FinanceDataReaderKrxListingClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgStockUniverseRepository", lambda: object())
    monkeypatch.setattr(batch_main, "FinanceDataReaderStockPriceClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgStockDailyPriceRepository", lambda: object())
    monkeypatch.setattr(batch_main, "FinanceDataReaderMarketIndexPriceClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgMarketIndexDailyPriceRepository", lambda: object())


def test_main_runs_market_index_daily_price_after_stock_daily_price(patched_main):
    run_order = []
    FakeStockUniverseRunner.run_order = run_order
    FakeStockDailyPriceRunner.run_order = run_order
    FakeMarketIndexDailyPriceRunner.run_order = run_order

    batch_main.main([])

    assert run_order == [
        "stock_universe",
        "stock_daily_price",
        "market_index_daily_price",
    ]
    assert FakeStockDailyPriceRunner.commands == [None]
    assert FakeMarketIndexDailyPriceRunner.commands == [None]


def test_main_runs_only_stock_daily_price_for_stock_reload(patched_main):
    batch_main.main(
        [
            "--stock-code",
            "005930",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ]
    )

    assert FakeStockUniverseRunner.run_count == 0
    assert FakeStockDailyPriceRunner.run_count == 1
    assert FakeMarketIndexDailyPriceRunner.run_count == 0
    command = FakeStockDailyPriceRunner.commands[0]
    assert command.stock_code == "005930"
    assert command.start_date.isoformat() == "2024-01-01"
    assert command.end_date.isoformat() == "2024-01-31"


def test_main_runs_only_market_index_daily_price_for_index_reload(patched_main):
    batch_main.main(
        [
            "--index-code",
            "kospi",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ]
    )

    assert FakeStockUniverseRunner.run_count == 0
    assert FakeStockDailyPriceRunner.run_count == 0
    assert FakeMarketIndexDailyPriceRunner.run_count == 1
    command = FakeMarketIndexDailyPriceRunner.commands[0]
    assert command.index_code == "KOSPI"
    assert command.start_date.isoformat() == "2024-01-01"
    assert command.end_date.isoformat() == "2024-01-31"


def test_main_fails_stock_reload_when_runner_saves_no_rows(patched_main):
    FakeStockDailyPriceRunner.result = SimpleNamespace(is_success=True, saved_price_count=0)

    with pytest.raises(RuntimeError, match="저장된 row가 없습니다"):
        batch_main.main(
            [
                "--stock-code",
                "005930",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )


def test_main_fails_index_reload_when_runner_reports_failure(patched_main):
    FakeMarketIndexDailyPriceRunner.result = SimpleNamespace(is_success=False, saved_price_count=1)

    with pytest.raises(RuntimeError, match="지정 재수집에 실패했습니다"):
        batch_main.main(
            [
                "--index-code",
                "KOSPI",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ]
        )


@pytest.mark.parametrize(
    "argv",
    [
        ["--stock-code", "005930", "--index-code", "KOSPI", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--stock-code", "005930", "--start-date", "2024-01-01"],
        ["--stock-code", "005930", "--end-date", "2024-01-31"],
        ["--stock-code", "005930", "--start-date", "2024-01-32", "--end-date", "2024-01-31"],
        ["--stock-code", "005930", "--start-date", "2024-02-01", "--end-date", "2024-01-31"],
        ["--stock-code", "5930", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--stock-code", "005930.KS", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--stock-code", "삼성전자", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--stock-code", "ABCDEF", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
        ["--index-code", "UNKNOWN", "--start-date", "2024-01-01", "--end-date", "2024-01-31"],
    ],
)
def test_main_rejects_invalid_targeted_reload_options(patched_main, argv):
    with pytest.raises(SystemExit):
        batch_main.main(argv)

    assert FakeStockUniverseRunner.run_count == 0
    assert FakeStockDailyPriceRunner.run_count == 0
    assert FakeMarketIndexDailyPriceRunner.run_count == 0


def test_main_does_not_run_stock_daily_price_when_stock_universe_digest_fails(patched_main):
    FakeStockUniverseRunner.result = SimpleNamespace(digest_matched=False)

    try:
        batch_main.main([])
    except RuntimeError:
        pass

    assert FakeStockUniverseRunner.run_count == 1
    assert FakeStockDailyPriceRunner.run_count == 0
    assert FakeMarketIndexDailyPriceRunner.run_count == 0
