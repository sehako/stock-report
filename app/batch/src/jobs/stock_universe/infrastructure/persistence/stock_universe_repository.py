from __future__ import annotations

from collections.abc import Callable

from jobs.stock_universe.domain.model import StockUniverseStock
from jobs.stock_universe.domain.repository import StockUniverseRepository
from shared.database import connect_database


class PsycopgStockUniverseRepository(StockUniverseRepository):
    def __init__(self, connection_factory: Callable | None = None):
        self._connection_factory = connection_factory or connect_database

    def replace_tracked_stocks(self, stocks: list[StockUniverseStock]) -> int:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT INTO stock (market, stock_code, stock_name, tracked)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (market, stock_code) DO UPDATE
                SET stock_name = EXCLUDED.stock_name,
                    tracked = EXCLUDED.tracked
                """,
                [(stock.market, stock.stock_code, stock.stock_name, True) for stock in stocks],
            )
            stock_codes = [stock.stock_code for stock in stocks]
            cursor.execute(
                """
                UPDATE stock
                SET tracked = false
                WHERE tracked = true
                  AND NOT (stock_code = ANY(%s))
                """,
                (stock_codes,),
            )
            untracked_count = cursor.rowcount
            connection.commit()
            return untracked_count
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    def find_tracked_stock_codes(self) -> list[str]:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            rows = cursor.execute(
                """
                SELECT stock_code
                FROM stock
                WHERE tracked = true
                ORDER BY stock_code
                """
            ).fetchall()
            return [row[0] for row in rows]
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()
