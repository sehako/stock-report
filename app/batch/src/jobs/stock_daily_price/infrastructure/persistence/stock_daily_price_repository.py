from __future__ import annotations

from collections.abc import Callable

from jobs.stock_daily_price.domain.model import StockDailyPrice, TrackedStock
from jobs.stock_daily_price.domain.repository import StockDailyPriceRepository
from shared.database import connect_database


class PsycopgStockDailyPriceRepository(StockDailyPriceRepository):
    def __init__(self, connection_factory: Callable | None = None):
        self._connection_factory = connection_factory or connect_database

    def find_tracked_stocks_with_last_loaded_date(self) -> list[TrackedStock]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT
                    s.id,
                    s.market,
                    s.stock_code,
                    s.stock_name,
                    MAX(sp.trade_date) AS last_loaded_date
                FROM stock s
                LEFT JOIN stock_price sp ON sp.stock_id = s.id
                WHERE s.tracked = true
                GROUP BY s.id, s.market, s.stock_code, s.stock_name
                ORDER BY s.stock_code
                """
            ).fetchall()
            return [
                TrackedStock(
                    stock_id=row[0],
                    market=row[1],
                    stock_code=row[2],
                    stock_name=row[3],
                    last_loaded_date=row[4],
                )
                for row in rows
            ]
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    def find_stock_by_code(self, stock_code: str) -> TrackedStock | None:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            row = cursor.execute(
                """
                SELECT
                    s.id,
                    s.market,
                    s.stock_code,
                    s.stock_name,
                    MAX(sp.trade_date) AS last_loaded_date
                FROM stock s
                LEFT JOIN stock_price sp ON sp.stock_id = s.id
                WHERE s.stock_code = %s
                GROUP BY s.id, s.market, s.stock_code, s.stock_name
                """,
                (stock_code,),
            ).fetchone()
            if row is None:
                return None
            return TrackedStock(
                stock_id=row[0],
                market=row[1],
                stock_code=row[2],
                stock_name=row[3],
                last_loaded_date=row[4],
            )
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    def upsert_stock_prices(self, stock_id: int, prices: list[StockDailyPrice]) -> int:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT INTO stock_price (
                    stock_id,
                    trade_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    change_rate
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, trade_date) DO UPDATE
                SET open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    change_rate = EXCLUDED.change_rate
                """,
                [
                    (
                        price.stock_id,
                        price.trade_date,
                        price.open_price,
                        price.high_price,
                        price.low_price,
                        price.close_price,
                        price.volume,
                        price.change_rate,
                    )
                    for price in prices
                ],
            )
            connection.commit()
            return len(prices)
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()
