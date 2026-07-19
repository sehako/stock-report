from jobs.stock_universe.application.stock_universe_runner import StockUniverseRunner


def krx_row(code: str, volume: int):
    return {
        "Code": code,
        "Name": f"종목{code}",
        "Market": "KOSPI",
        "Volume": volume,
    }


class FakeKrxListingClient:
    def __init__(self, rows):
        self.rows = rows

    def fetch_krx_listing(self):
        return self.rows


class FakeStockUniverseRepository:
    def __init__(self):
        self.saved_stocks = None

    def replace_tracked_stocks(self, stocks):
        self.saved_stocks = list(stocks)
        return 3

    def find_tracked_stock_codes(self):
        return [stock.stock_code for stock in self.saved_stocks]


def test_runner_fetches_selects_saves_and_returns_digest_match():
    rows = [krx_row(f"{index:06d}", index) for index in range(1, 202)]
    repository = FakeStockUniverseRepository()
    runner = StockUniverseRunner(FakeKrxListingClient(rows), repository)

    result = runner.run()

    assert result.source_row_count == 201
    assert result.selected_count == 200
    assert result.untracked_count == 3
    assert result.digest_matched is True
    assert len(repository.saved_stocks) == 200
    assert repository.saved_stocks[0].stock_code == "000201"
