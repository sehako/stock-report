from types import SimpleNamespace

import batch.main as batch_main


class FakeStockUniverseRunner:
    result = SimpleNamespace(digest_matched=True)
    run_count = 0

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def run(self):
        type(self).run_count += 1
        return type(self).result


class FakeStockDailyPriceRunner:
    run_count = 0

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def run(self):
        type(self).run_count += 1
        return SimpleNamespace(is_success=True)


def test_main_runs_stock_daily_price_after_stock_universe(monkeypatch):
    FakeStockUniverseRunner.result = SimpleNamespace(digest_matched=True)
    FakeStockUniverseRunner.run_count = 0
    FakeStockDailyPriceRunner.run_count = 0
    monkeypatch.setattr(batch_main, "load_batch_config", lambda: SimpleNamespace(log_level="INFO"))
    monkeypatch.setattr(batch_main, "configure_logging", lambda log_level: None)
    monkeypatch.setattr(batch_main, "StockUniverseRunner", FakeStockUniverseRunner)
    monkeypatch.setattr(batch_main, "StockDailyPriceRunner", FakeStockDailyPriceRunner)
    monkeypatch.setattr(batch_main, "FinanceDataReaderKrxListingClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgStockUniverseRepository", lambda: object())
    monkeypatch.setattr(batch_main, "FinanceDataReaderStockPriceClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgStockDailyPriceRepository", lambda: object())

    batch_main.main()

    assert FakeStockUniverseRunner.run_count == 1
    assert FakeStockDailyPriceRunner.run_count == 1


def test_main_does_not_run_stock_daily_price_when_stock_universe_digest_fails(monkeypatch):
    FakeStockUniverseRunner.result = SimpleNamespace(digest_matched=False)
    FakeStockUniverseRunner.run_count = 0
    FakeStockDailyPriceRunner.run_count = 0
    monkeypatch.setattr(batch_main, "load_batch_config", lambda: SimpleNamespace(log_level="INFO"))
    monkeypatch.setattr(batch_main, "configure_logging", lambda log_level: None)
    monkeypatch.setattr(batch_main, "StockUniverseRunner", FakeStockUniverseRunner)
    monkeypatch.setattr(batch_main, "StockDailyPriceRunner", FakeStockDailyPriceRunner, raising=False)
    monkeypatch.setattr(batch_main, "FinanceDataReaderKrxListingClient", lambda: object())
    monkeypatch.setattr(batch_main, "PsycopgStockUniverseRepository", lambda: object())

    try:
        batch_main.main()
    except RuntimeError:
        pass

    assert FakeStockUniverseRunner.run_count == 1
    assert FakeStockDailyPriceRunner.run_count == 0
