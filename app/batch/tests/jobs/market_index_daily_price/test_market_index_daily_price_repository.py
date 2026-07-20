from datetime import date
from decimal import Decimal

from jobs.market_index_daily_price.domain.model import MarketIndexDailyPrice
from jobs.market_index_daily_price.infrastructure.persistence.market_index_daily_price_repository import (
    PsycopgMarketIndexDailyPriceRepository,
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

    def fetchone(self):
        return self.rows[0] if self.rows else None


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


def test_repository_reads_last_loaded_date_for_index_code():
    cursor = FakeCursor(rows=[(date(2026, 7, 17),)])
    connection = FakeConnection(cursor)
    repository = PsycopgMarketIndexDailyPriceRepository(lambda: connection)

    last_loaded_date = repository.find_last_loaded_date("KOSPI")

    assert last_loaded_date == date(2026, 7, 17)
    assert connection.closed is True
    method, sql, params = cursor.executed[0]
    assert method == "execute"
    assert "MAX(trade_date)" in sql
    assert "FROM market_index_price" in sql
    assert "WHERE index_code = %s" in sql
    assert params == ("KOSPI",)


def test_repository_returns_none_when_index_has_no_loaded_date():
    cursor = FakeCursor(rows=[(None,)])
    connection = FakeConnection(cursor)
    repository = PsycopgMarketIndexDailyPriceRepository(lambda: connection)

    last_loaded_date = repository.find_last_loaded_date("KOSDAQ")

    assert last_loaded_date is None


def test_repository_upserts_market_index_prices_with_conflict_update_and_commit():
    connection = FakeConnection()
    repository = PsycopgMarketIndexDailyPriceRepository(lambda: connection)
    prices = [
        MarketIndexDailyPrice(
            index_code="KOSPI",
            trade_date=date(2026, 7, 17),
            open_price=Decimal("3200.10"),
            high_price=Decimal("3210.20"),
            low_price=Decimal("3190.30"),
            close_price=Decimal("3205.40"),
            volume=123456,
            change_rate=Decimal("0.01"),
        )
    ]

    saved_count = repository.upsert_market_index_prices("KOSPI", prices)

    assert saved_count == 1
    assert connection.committed is True
    assert connection.rolled_back is False
    method, sql, params = connection.cursor_instance.executed[0]
    assert method == "executemany"
    assert "INSERT INTO market_index_price" in sql
    assert "ON CONFLICT (index_code, trade_date) DO UPDATE" in sql
    assert params == [
        (
            "KOSPI",
            date(2026, 7, 17),
            Decimal("3200.10"),
            Decimal("3210.20"),
            Decimal("3190.30"),
            Decimal("3205.40"),
            123456,
            Decimal("0.01"),
        )
    ]


def test_repository_rolls_back_index_transaction_when_upsert_fails():
    class FailingCursor(FakeCursor):
        def executemany(self, sql, params):
            raise RuntimeError("database failed")

    connection = FakeConnection(FailingCursor())
    repository = PsycopgMarketIndexDailyPriceRepository(lambda: connection)
    price = MarketIndexDailyPrice(
        index_code="KOSDAQ",
        trade_date=date(2026, 7, 17),
        open_price=Decimal("800.10"),
        high_price=Decimal("810.20"),
        low_price=Decimal("790.30"),
        close_price=Decimal("805.40"),
        volume=98765,
        change_rate=None,
    )

    try:
        repository.upsert_market_index_prices("KOSDAQ", [price])
    except RuntimeError:
        pass

    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True
