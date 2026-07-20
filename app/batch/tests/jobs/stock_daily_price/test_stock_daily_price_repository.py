from datetime import date
from decimal import Decimal

from jobs.stock_daily_price.domain.model import StockDailyPrice
from jobs.stock_daily_price.infrastructure.persistence.stock_daily_price_repository import (
    PsycopgStockDailyPriceRepository,
)


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append(("execute", sql, params))
        return self

    def executemany(self, sql, params):
        self.executed.append(("executemany", sql, params))
        self.rowcount = len(params)

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursor=None):
        self.cursor_instance = cursor or FakeCursor()
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


def test_repository_reads_tracked_stocks_with_last_loaded_date():
    cursor = FakeCursor(rows=[(1, "KOSPI", "005930", "삼성전자", date(2026, 7, 17))])
    connection = FakeConnection(cursor)
    repository = PsycopgStockDailyPriceRepository(lambda: connection)

    stocks = repository.find_tracked_stocks_with_last_loaded_date()

    assert stocks[0].stock_id == 1
    assert stocks[0].last_loaded_date == date(2026, 7, 17)
    sql = cursor.executed[0][1]
    assert "LEFT JOIN stock_price" in sql
    assert "MAX(sp.trade_date)" in sql
    assert "s.tracked = true" in sql


def test_repository_upserts_stock_prices_with_conflict_update_and_commit():
    connection = FakeConnection()
    repository = PsycopgStockDailyPriceRepository(lambda: connection)
    prices = [
        StockDailyPrice(
            stock_id=1,
            trade_date=date(2026, 7, 17),
            open_price=Decimal("1000"),
            high_price=Decimal("1100"),
            low_price=Decimal("900"),
            close_price=Decimal("1050"),
            volume=12000,
            change_rate=Decimal("0.05"),
        )
    ]

    saved_count = repository.upsert_stock_prices(1, prices)

    assert saved_count == 1
    assert connection.committed is True
    assert connection.rolled_back is False
    method, sql, params = connection.cursor_instance.executed[0]
    assert method == "executemany"
    assert "INSERT INTO stock_price" in sql
    assert "ON CONFLICT (stock_id, trade_date) DO UPDATE" in sql
    assert params == [
        (
            1,
            date(2026, 7, 17),
            Decimal("1000"),
            Decimal("1100"),
            Decimal("900"),
            Decimal("1050"),
            12000,
            Decimal("0.05"),
        )
    ]


def test_repository_rolls_back_stock_when_upsert_fails():
    class FailingCursor(FakeCursor):
        def executemany(self, sql, params):
            raise RuntimeError("database failed")

    connection = FakeConnection(FailingCursor())
    repository = PsycopgStockDailyPriceRepository(lambda: connection)
    price = StockDailyPrice(
        stock_id=1,
        trade_date=date(2026, 7, 17),
        open_price=Decimal("1000"),
        high_price=Decimal("1100"),
        low_price=Decimal("900"),
        close_price=Decimal("1050"),
        volume=12000,
        change_rate=None,
    )

    try:
        repository.upsert_stock_prices(1, [price])
    except RuntimeError:
        pass

    assert connection.committed is False
    assert connection.rolled_back is True
