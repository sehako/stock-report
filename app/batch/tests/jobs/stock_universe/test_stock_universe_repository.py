from jobs.stock_universe.domain.model import StockUniverseStock
from jobs.stock_universe.infrastructure.persistence.stock_universe_repository import PsycopgStockUniverseRepository


class FakeCursor:
    def __init__(self, rows=None, rowcount=0):
        self.rows = rows or []
        self.rowcount = rowcount
        self.executed = []

    def executemany(self, sql, params):
        self.executed.append(("executemany", sql, params))

    def execute(self, sql, params=None):
        self.executed.append(("execute", sql, params))
        return self

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor(rows=[("000001",), ("000002",)], rowcount=7)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_repository_upserts_selected_stocks_and_untracks_missing_rows():
    connection = FakeConnection()
    repository = PsycopgStockUniverseRepository(lambda: connection)
    stocks = [
        StockUniverseStock("KOSPI", "000001", "첫번째", 100),
        StockUniverseStock("KOSDAQ", "000002", "두번째", 90),
    ]

    untracked_count = repository.replace_tracked_stocks(stocks)

    assert untracked_count == 7
    assert connection.committed is True
    assert connection.rolled_back is False
    executed = connection.cursor_instance.executed
    assert executed[0][0] == "executemany"
    assert "ON CONFLICT (market, stock_code) DO UPDATE" in executed[0][1]
    assert executed[0][2] == [
        ("KOSPI", "000001", "첫번째", True),
        ("KOSDAQ", "000002", "두번째", True),
    ]
    assert executed[1][0] == "execute"
    assert "tracked = false" in executed[1][1]
    assert executed[1][2] == (["000001", "000002"],)


def test_repository_rolls_back_when_database_update_fails():
    class FailingCursor(FakeCursor):
        def executemany(self, sql, params):
            raise RuntimeError("database failed")

    class FailingConnection(FakeConnection):
        def __init__(self):
            super().__init__()
            self.cursor_instance = FailingCursor()

    connection = FailingConnection()
    repository = PsycopgStockUniverseRepository(lambda: connection)
    stocks = [StockUniverseStock("KOSPI", "000001", "첫번째", 100)]

    try:
        repository.replace_tracked_stocks(stocks)
    except RuntimeError:
        pass

    assert connection.committed is False
    assert connection.rolled_back is True
