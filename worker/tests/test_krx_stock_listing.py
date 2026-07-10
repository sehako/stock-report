from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.pool import StaticPool

from stock_report_worker.krx.normalization import (
    KrxListedStock,
    KrxStockListingUnavailable,
    KrxStockListingUnavailableReason,
    normalize_krx_stock_listing,
)
from stock_report_worker.krx.listing_client import KrxStockListingProvider
from stock_report_worker.repositories.schema import metadata, stock
from stock_report_worker.repositories.stocks import StockRepository


@pytest.fixture()
def engine():
    test_engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(test_engine)
    return test_engine


def test_normalizes_krx_listing_and_desc_by_stock_code() -> None:
    listing = pd.DataFrame(
        [
            {"Code": "005930", "Name": " 삼성전자 ", "Market": "KOSPI", "Close": "85000", "Volume": "123456"},
            {"Code": 12345, "Name": "에코프로비엠", "Market": "KOSDAQ", "Close": 210000, "Volume": 5000},
            {"Code": "900001", "Name": "미분류", "Market": "기타", "Close": 1000, "Volume": 1},
        ]
    )
    desc = pd.DataFrame(
        [
            {"Code": "005930", "Sector": "전기전자"},
            {"Code": "012345", "Sector": "일반전기전자"},
        ]
    )

    stocks = normalize_krx_stock_listing(listing, desc)

    assert [(stock.stock_code, stock.stock_name, stock.market, stock.industry_name) for stock in stocks] == [
        ("005930", "삼성전자", "KOSPI", "전기전자"),
        ("012345", "에코프로비엠", "KOSDAQ", "일반전기전자"),
        ("900001", "미분류", "UNKNOWN", None),
    ]
    assert stocks[0].listing_close_price == Decimal("85000")
    assert stocks[0].listing_volume == 123456


def test_missing_required_source_columns_are_classified_as_listing_unavailable() -> None:
    listing = pd.DataFrame([{"Code": "005930", "Name": "삼성전자", "Market": "KOSPI", "Close": 85000}])
    desc = pd.DataFrame([{"Code": "005930", "Sector": "전기전자"}])

    with pytest.raises(KrxStockListingUnavailable) as exc_info:
        normalize_krx_stock_listing(listing, desc)

    assert exc_info.value.reason == KrxStockListingUnavailableReason.SOURCE_COLUMNS_MISSING


def test_invalid_required_source_values_are_classified_as_listing_unavailable() -> None:
    listing = pd.DataFrame(
        [{"Code": "005930", "Name": "삼성전자", "Market": "KOSPI", "Close": "not-a-price", "Volume": 1}]
    )
    desc = pd.DataFrame([{"Code": "005930", "Sector": "전기전자"}])

    with pytest.raises(KrxStockListingUnavailable) as exc_info:
        normalize_krx_stock_listing(listing, desc)

    assert exc_info.value.reason == KrxStockListingUnavailableReason.SOURCE_VALUES_INVALID


def test_duplicate_listing_stock_code_is_classified_as_listing_unavailable() -> None:
    listing = pd.DataFrame(
        [
            {"Code": "005930", "Name": "삼성전자", "Market": "KOSPI", "Close": 85000, "Volume": 1},
            {"Code": "005930", "Name": "삼성전자우", "Market": "KOSPI", "Close": 70000, "Volume": 2},
        ]
    )
    desc = pd.DataFrame([{"Code": "005930", "Sector": "전기전자"}])

    with pytest.raises(KrxStockListingUnavailable) as exc_info:
        normalize_krx_stock_listing(listing, desc)

    assert exc_info.value.reason == KrxStockListingUnavailableReason.SOURCE_VALUES_INVALID


def test_stock_repository_upserts_by_stock_code_and_returns_ids_in_input_order(engine) -> None:
    repository = StockRepository()
    first_now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    second_now = datetime(2026, 7, 10, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    initial_stocks = [
        KrxListedStock("005930", "삼성전자", "KOSPI", "전기전자", Decimal("85000"), 123456),
        KrxListedStock("012345", "에코프로비엠", "KOSDAQ", None, Decimal("210000"), 5000),
    ]
    updated_stocks = [
        KrxListedStock("012345", "에코프로비엠", "KOSDAQ", "일반전기전자", Decimal("210000"), 5000),
        KrxListedStock("005930", "삼성전자우", "KOSPI", "전기전자", Decimal("85000"), 123456),
    ]

    with engine.begin() as connection:
        first_ids = repository.upsert_listed_stocks(connection, initial_stocks, first_now)
        second_ids = repository.upsert_listed_stocks(connection, updated_stocks, second_now)
        rows = connection.execute(select(stock).order_by(stock.c.stock_code)).mappings().all()

    assert first_ids == [1, 2]
    assert second_ids == [2, 1]
    assert [(row["stock_code"], row["stock_name"], row["industry_name"]) for row in rows] == [
        ("005930", "삼성전자우", "전기전자"),
        ("012345", "에코프로비엠", "일반전기전자"),
    ]
    assert rows[0]["created_at"] == first_now.replace(tzinfo=None)
    assert rows[0]["updated_at"] == second_now.replace(tzinfo=None)


class FakeListingClient:
    def __init__(self, listing_frame=None, desc_frame=None, *, fail_market: str | None = None) -> None:
        self.listing_frame = listing_frame
        self.desc_frame = desc_frame
        self.fail_market = fail_market
        self.calls: list[str] = []

    def stock_listing(self, market: str) -> pd.DataFrame:
        self.calls.append(market)
        if market == self.fail_market:
            raise RuntimeError(f"{market} unavailable")
        if market == "KRX":
            return self.listing_frame
        if market == "KRX-DESC":
            return self.desc_frame
        raise AssertionError(f"unexpected market: {market}")


def test_krx_stock_listing_provider_upserts_and_returns_listed_stocks_with_stock_ids(engine) -> None:
    listing = pd.DataFrame(
        [{"Code": "005930", "Name": "삼성전자", "Market": "KOSPI", "Close": 85000, "Volume": 123456}]
    )
    desc = pd.DataFrame([{"Code": "005930", "Sector": "전기전자"}])
    provider = KrxStockListingProvider(engine, FakeListingClient(listing, desc))
    now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    listed_stocks = provider.collect(now)

    assert provider.client.calls == ["KRX", "KRX-DESC"]
    assert listed_stocks == [
        KrxListedStock(
            "005930",
            "삼성전자",
            "KOSPI",
            "전기전자",
            Decimal("85000"),
            123456,
            stock_id=1,
        )
    ]
    with engine.begin() as connection:
        rows = connection.execute(select(stock)).mappings().all()
    assert [(row["stock_code"], row["industry_name"]) for row in rows] == [("005930", "전기전자")]


def test_krx_listing_fetch_failure_is_classified_as_listing_unavailable(engine) -> None:
    provider = KrxStockListingProvider(engine, FakeListingClient(fail_market="KRX"))
    now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    with pytest.raises(KrxStockListingUnavailable) as exc_info:
        provider.collect(now)

    assert exc_info.value.reason == KrxStockListingUnavailableReason.KRX_LISTING_FETCH_FAILED


def test_krx_desc_fetch_failure_is_classified_as_listing_unavailable(engine) -> None:
    listing = pd.DataFrame(
        [{"Code": "005930", "Name": "삼성전자", "Market": "KOSPI", "Close": 85000, "Volume": 123456}]
    )
    provider = KrxStockListingProvider(engine, FakeListingClient(listing_frame=listing, fail_market="KRX-DESC"))
    now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    with pytest.raises(KrxStockListingUnavailable) as exc_info:
        provider.collect(now)

    assert exc_info.value.reason == KrxStockListingUnavailableReason.KRX_DESC_FETCH_FAILED


def postgres_url() -> str | None:
    import os

    return os.environ.get("WORKER_POSTGRES_TEST_URL")


def make_flyway_postgres_engine():
    url = postgres_url()
    if not url:
        pytest.skip("WORKER_POSTGRES_TEST_URL is required for PostgreSQL/Flyway verification.")
    schema_name = f"worker_test_{uuid4().hex}"
    admin_engine = create_engine(url, future=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'create schema "{schema_name}"'))

    pg_engine = create_engine(url, future=True)

    @event.listens_for(pg_engine, "connect")
    def set_search_path(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'set search_path to "{schema_name}"')
        finally:
            cursor.close()

    migration_sql = (
        Path(__file__).parents[2]
        / "server"
        / "src"
        / "main"
        / "resources"
        / "db"
        / "migration"
        / "V1__initial_schema.sql"
    ).read_text()
    with pg_engine.begin() as connection:
        connection.exec_driver_sql(migration_sql)
    return admin_engine, pg_engine, schema_name


def drop_schema(admin_engine, schema_name: str) -> None:
    with admin_engine.begin() as connection:
        connection.execute(text(f'drop schema if exists "{schema_name}" cascade'))


def test_postgres_flyway_schema_accepts_stock_upsert() -> None:
    admin_engine, pg_engine, schema_name = make_flyway_postgres_engine()
    try:
        repository = StockRepository()
        first_now = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        second_now = datetime(2026, 7, 10, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with pg_engine.begin() as connection:
            first_ids = repository.upsert_listed_stocks(
                connection,
                [KrxListedStock("005930", "삼성전자", "KOSPI", "전기전자", Decimal("85000"), 123456)],
                first_now,
            )
            second_ids = repository.upsert_listed_stocks(
                connection,
                [KrxListedStock("005930", "삼성전자우", "KOSPI", "전기전자", Decimal("85000"), 123456)],
                second_now,
            )
            rows = connection.execute(select(stock)).mappings().all()

        assert first_ids == second_ids
        assert [(row["stock_code"], row["stock_name"]) for row in rows] == [("005930", "삼성전자우")]
    finally:
        drop_schema(admin_engine, schema_name)
