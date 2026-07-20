from __future__ import annotations

from collections.abc import Callable
from datetime import date

from jobs.market_index_daily_price.domain.model import MarketIndexDailyPrice
from jobs.market_index_daily_price.domain.repository import MarketIndexDailyPriceRepository
from shared.database import connect_database


class PsycopgMarketIndexDailyPriceRepository(MarketIndexDailyPriceRepository):
    def __init__(self, connection_factory: Callable | None = None):
        self._connection_factory = connection_factory or connect_database

    def find_last_loaded_date(self, index_code: str) -> date | None:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            row = cursor.execute(
                """
                SELECT MAX(trade_date)
                FROM market_index_price
                WHERE index_code = %s
                """,
                (index_code,),
            ).fetchone()
            if row is None:
                return None
            return row[0]
        finally:
            close = getattr(connection, "close", None)
            if close is not None:
                close()

    def upsert_market_index_prices(self, index_code: str, prices: list[MarketIndexDailyPrice]) -> int:
        connection = self._connection_factory()
        try:
            cursor = connection.cursor()
            cursor.executemany(
                """
                INSERT INTO market_index_price (
                    index_code,
                    trade_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    change_rate
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (index_code, trade_date) DO UPDATE
                SET open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    change_rate = EXCLUDED.change_rate
                """,
                [
                    (
                        price.index_code,
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
