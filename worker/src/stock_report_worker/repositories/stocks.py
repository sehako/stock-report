"""Repository for current stock metadata."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from stock_report_worker.krx.normalization import KrxListedStock
from stock_report_worker.repositories.schema import stock


class StockRepository:
    def upsert_listed_stocks(
        self, connection: Connection, listed_stocks: list[KrxListedStock], now: datetime
    ) -> list[int]:
        if not listed_stocks:
            return []

        values = [
            {
                "stock_code": listed_stock.stock_code,
                "stock_name": listed_stock.stock_name,
                "market": listed_stock.market,
                "industry_name": listed_stock.industry_name,
                "created_at": now,
                "updated_at": now,
            }
            for listed_stock in listed_stocks
        ]
        insert_statement = self._insert_statement(connection, values)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[stock.c.stock_code],
            set_={
                "stock_name": insert_statement.excluded.stock_name,
                "market": insert_statement.excluded.market,
                "industry_name": insert_statement.excluded.industry_name,
                "updated_at": insert_statement.excluded.updated_at,
            },
        )
        connection.execute(upsert_statement)

        stock_codes = [listed_stock.stock_code for listed_stock in listed_stocks]
        rows = connection.execute(
            select(stock.c.id, stock.c.stock_code).where(stock.c.stock_code.in_(stock_codes))
        ).mappings()
        ids_by_code = {str(row["stock_code"]): int(row["id"]) for row in rows}
        return [ids_by_code[stock_code] for stock_code in stock_codes]

    def _insert_statement(self, connection: Connection, values: list[dict[str, object]]):
        if connection.dialect.name == "postgresql":
            return postgresql_insert(stock).values(values)
        if connection.dialect.name == "sqlite":
            return sqlite_insert(stock).values(values)
        raise RuntimeError(f"unsupported stock upsert dialect: {connection.dialect.name}")
