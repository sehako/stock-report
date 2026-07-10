from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from time import sleep
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, event, insert, select, text
from sqlalchemy.pool import StaticPool

from stock_report_worker.config import WorkerSettings
from stock_report_worker.jobs.daily_report import DailyReportBatch
from stock_report_worker.jobs.locks import BatchLock, PostgresAdvisoryBatchLock
from stock_report_worker.jobs.stock_runner import PermanentAnalysisError
from stock_report_worker.jobs.target_stocks import InMemoryTargetStockProvider, TargetStock
from stock_report_worker.jobs.trading_calendar import TradingDayStatus
from stock_report_worker.krx.normalization import (
    KrxStockListingUnavailable,
    KrxStockListingUnavailableReason,
)
from stock_report_worker.repositories.schema import (
    batch_job_run,
    batch_stock_run,
    daily_stock_processing_status,
    metadata,
    report_revision,
    stock,
)


class FakeCalendar:
    def __init__(self, status: TradingDayStatus) -> None:
        self._status = status

    def status_for(self, report_date: date) -> TradingDayStatus:
        return self._status


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 9, 19, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class DeniedLock(BatchLock):
    def acquire(self, connection, report_date: date) -> bool:
        return False


class PublisherSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[date, int]] = []

    def publish_initial(self, report_date: date, batch_job_run_id: int) -> None:
        self.calls.append((report_date, batch_job_run_id))


class FakeTargetStockProvider:
    def __init__(self, target_ids: list[int] | None = None, *, fail: bool = False) -> None:
        self._target_ids = target_ids or []
        self._fail = fail
        self.calls: list[date] = []

    def list_for(self, report_date: date) -> list[TargetStock]:
        self.calls.append(report_date)
        if self._fail:
            raise KrxStockListingUnavailable(
                KrxStockListingUnavailableReason.KRX_LISTING_FETCH_FAILED,
                "KRX StockListing failed",
            )
        return [
            TargetStock(
                id=stock_id,
                selection_rank=index,
                selection_volume=stock_id * 10,
                stock_code=f"{stock_id:06d}",
            )
            for index, stock_id in enumerate(self._target_ids, start=1)
        ]


class SequencedTargetStockProvider:
    def __init__(self, target_id_sets: list[list[int]]) -> None:
        self._target_id_sets = target_id_sets
        self.calls: list[date] = []

    def list_for(self, report_date: date) -> list[TargetStock]:
        self.calls.append(report_date)
        target_ids = self._target_id_sets.pop(0)
        return [
            TargetStock(
                id=stock_id,
                selection_rank=index,
                selection_volume=stock_id * 10,
                stock_code=f"{stock_id:06d}",
            )
            for index, stock_id in enumerate(target_ids, start=1)
        ]


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


@pytest.fixture()
def settings() -> WorkerSettings:
    return WorkerSettings(
        database_url="sqlite+pysqlite:///:memory:",
        stock_timeout_seconds=0.01,
        retry_interval_seconds=600,
        max_retries=3,
        consecutive_timeout_limit=5,
    )


def seed_stocks(engine, stock_ids: list[int]) -> None:
    with engine.begin() as connection:
        for stock_id in stock_ids:
            connection.execute(
                insert(stock).values(
                    id=stock_id,
                    stock_code=f"{stock_id:06d}",
                    stock_name=f"stock-{stock_id}",
                    market="KOSPI",
                )
            )


def rows(engine, table):
    with engine.begin() as connection:
        return connection.execute(select(table).order_by(table.c.id)).mappings().all()


def batch(
    engine,
    settings,
    clock: FakeClock,
    *,
    status: TradingDayStatus = TradingDayStatus.OPEN,
    stock_ids: list[int] | None = None,
    task=None,
    publisher=None,
    lock=None,
) -> DailyReportBatch:
    return DailyReportBatch(
        engine=engine,
        settings=settings,
        calendar=FakeCalendar(status),
        target_stock_provider=InMemoryTargetStockProvider(stock_ids or []),
        stock_task=task or (lambda stock_id: None),
        publisher=publisher or PublisherSpy(),
        lock=lock,
        now=clock.now,
        sleeper=clock.sleep,
    )


def batch_with_provider(
    engine,
    settings,
    clock: FakeClock,
    provider,
    *,
    status: TradingDayStatus = TradingDayStatus.OPEN,
    task=None,
    publisher=None,
    lock=None,
) -> DailyReportBatch:
    return DailyReportBatch(
        engine=engine,
        settings=settings,
        calendar=FakeCalendar(status),
        target_stock_provider=provider,
        stock_task=task or (lambda stock_id: None),
        publisher=publisher or PublisherSpy(),
        lock=lock,
        now=clock.now,
        sleeper=clock.sleep,
    )


def test_market_closed_is_successful_skip(engine, settings) -> None:
    clock = FakeClock()
    result = batch(engine, settings, clock, status=TradingDayStatus.CLOSED).run(date(2026, 7, 9))

    assert result.exit_code == 0
    assert result.status == "SKIPPED_MARKET_CLOSED"
    assert rows(engine, batch_job_run)[0]["status"] == "SKIPPED_MARKET_CLOSED"


def test_unknown_trading_day_fails_non_zero(engine, settings) -> None:
    clock = FakeClock()
    result = batch(engine, settings, clock, status=TradingDayStatus.UNKNOWN).run(date(2026, 7, 9))

    job = rows(engine, batch_job_run)[0]
    assert result.exit_code == 1
    assert job["status"] == "FAILED"
    assert "unknown" in job["last_error"]


def test_lock_denial_skips_duplicate_run_without_job_row(engine, settings) -> None:
    clock = FakeClock()
    result = batch(engine, settings, clock, lock=DeniedLock()).run(date(2026, 7, 9))

    assert result.exit_code == 0
    assert result.status == "DUPLICATE_SKIPPED"
    assert rows(engine, batch_job_run) == []


def test_open_day_processes_target_stocks_in_order_and_publishes(engine, settings) -> None:
    seed_stocks(engine, [1, 2, 3])
    clock = FakeClock()
    calls: list[int] = []
    publisher = PublisherSpy()

    result = batch(
        engine,
        settings,
        clock,
        stock_ids=[1, 2, 3],
        task=lambda stock_id: calls.append(stock_id),
        publisher=publisher,
    ).run(date(2026, 7, 9))

    assert result.exit_code == 0
    assert calls == [1, 2, 3]
    assert rows(engine, batch_job_run)[0]["status"] == "PUBLISHED_INITIAL"
    assert [row["status"] for row in rows(engine, batch_stock_run)] == ["SUCCEEDED"] * 3
    assert publisher.calls == [(date(2026, 7, 9), result.batch_job_run_id)]


def test_open_day_uses_selected_targets_once_for_stock_runs_and_initial_status(
    engine, settings
) -> None:
    seed_stocks(engine, [1, 2, 3])
    clock = FakeClock()
    provider = FakeTargetStockProvider([3, 1])
    calls: list[int] = []

    result = batch_with_provider(
        engine,
        settings,
        clock,
        provider,
        task=lambda stock_id: calls.append(stock_id),
    ).run(date(2026, 7, 9))

    assert result.exit_code == 0
    assert provider.calls == [date(2026, 7, 9)]
    assert calls == [3, 1]
    assert [row["stock_id"] for row in rows(engine, batch_stock_run)] == [3, 1]
    assert [row["analysis_status"] for row in rows(engine, daily_stock_processing_status)] == [
        "DATA_PREPARING",
        "DATA_PREPARING",
    ]


def test_krx_listing_unavailable_delays_batch_without_stock_runs_or_revision(
    engine, settings
) -> None:
    clock = FakeClock()
    provider = FakeTargetStockProvider(fail=True)

    result = batch_with_provider(engine, settings, clock, provider).run(date(2026, 7, 9))

    job = rows(engine, batch_job_run)[0]
    assert result.exit_code == 1
    assert result.status == "DELAYED"
    assert job["status"] == "DELAYED"
    assert "KRX_LISTING_FETCH_FAILED" in job["last_error"]
    assert job["finished_at"] is not None
    assert rows(engine, batch_stock_run) == []
    assert rows(engine, daily_stock_processing_status) == []
    assert rows(engine, report_revision) == []


def test_market_closed_does_not_collect_target_stocks(engine, settings) -> None:
    clock = FakeClock()
    provider = FakeTargetStockProvider([1])

    result = batch_with_provider(
        engine,
        settings,
        clock,
        provider,
        status=TradingDayStatus.CLOSED,
    ).run(date(2026, 7, 9))

    assert result.exit_code == 0
    assert provider.calls == []


def test_rerun_replaces_previous_target_stock_rows_with_current_selection(engine, settings) -> None:
    seed_stocks(engine, [1, 2, 3])
    clock = FakeClock()
    provider = SequencedTargetStockProvider([[1, 2], [3]])
    report_date = date(2026, 7, 9)

    first = batch_with_provider(engine, settings, clock, provider).run(report_date)
    second = batch_with_provider(engine, settings, clock, provider).run(report_date)

    assert first.batch_job_run_id == second.batch_job_run_id
    assert [row["stock_id"] for row in rows(engine, batch_stock_run)] == [3]
    assert [row["stock_id"] for row in rows(engine, daily_stock_processing_status)] == [3]


def test_timeout_wrapper_path_records_retryable(engine, settings) -> None:
    seed_stocks(engine, [1])
    clock = FakeClock()

    def slow_task(stock_id: int) -> None:
        sleep(0.05)

    result = batch(engine, settings, clock, stock_ids=[1], task=slow_task).run(date(2026, 7, 9))

    stock_run = rows(engine, batch_stock_run)[0]
    status = rows(engine, daily_stock_processing_status)[0]
    assert result.exit_code == 0
    assert stock_run["status"] == "FAILED_PERMANENT"
    assert stock_run["attempt_count"] == 4
    assert status["analysis_status"] == "DATA_UPDATE_FAILED"


def test_five_consecutive_timeouts_defer_unstarted_without_attempt_increment(engine, settings) -> None:
    seed_stocks(engine, [1, 2, 3, 4, 5, 6])
    clock = FakeClock()
    settings.consecutive_timeout_limit = 5
    settings.max_retries = 0

    def slow_task(stock_id: int) -> None:
        sleep(0.05)

    batch(engine, settings, clock, stock_ids=[1, 2, 3, 4, 5, 6], task=slow_task).run(
        date(2026, 7, 9)
    )

    stock_runs = rows(engine, batch_stock_run)
    assert [row["attempt_count"] for row in stock_runs[:5]] == [1, 1, 1, 1, 1]
    assert stock_runs[5]["status"] == "FAILED_PERMANENT"
    assert stock_runs[5]["attempt_count"] == 1


def test_provider_outage_initially_defers_unstarted_without_attempt_increment(engine, settings) -> None:
    seed_stocks(engine, [1, 2, 3, 4, 5, 6])
    clock = FakeClock()
    settings.consecutive_timeout_limit = 5
    calls: list[int] = []

    def sometimes_slow(stock_id: int) -> None:
        calls.append(stock_id)
        if len(calls) <= 5:
            sleep(0.05)

    batch(engine, settings, clock, stock_ids=[1, 2, 3, 4, 5, 6], task=sometimes_slow).run(
        date(2026, 7, 9)
    )

    first_pass_sixth = rows(engine, batch_stock_run)[5]
    assert first_pass_sixth["attempt_count"] == 1
    assert calls[:5] == [1, 2, 3, 4, 5]
    assert 6 in calls


def test_general_exception_resets_consecutive_timeout_counter(engine, settings) -> None:
    seed_stocks(engine, [1, 2, 3, 4, 5, 6])
    clock = FakeClock()
    settings.consecutive_timeout_limit = 5
    settings.max_retries = 0

    def mixed_failures(stock_id: int) -> None:
        if stock_id == 3:
            raise RuntimeError("ordinary failure")
        sleep(0.05)

    batch(engine, settings, clock, stock_ids=[1, 2, 3, 4, 5, 6], task=mixed_failures).run(
        date(2026, 7, 9)
    )

    assert [row["attempt_count"] for row in rows(engine, batch_stock_run)] == [1, 1, 1, 1, 1, 1]


def test_successful_stock_commit_survives_later_permanent_failure(engine, settings) -> None:
    seed_stocks(engine, [1, 2])
    clock = FakeClock()

    def task(stock_id: int) -> None:
        if stock_id == 2:
            raise PermanentAnalysisError("analysis failed")

    result = batch(engine, settings, clock, stock_ids=[1, 2], task=task).run(date(2026, 7, 9))

    stock_runs = rows(engine, batch_stock_run)
    statuses = rows(engine, daily_stock_processing_status)
    assert result.exit_code == 0
    assert [row["status"] for row in stock_runs] == ["SUCCEEDED", "FAILED_PERMANENT"]
    assert statuses[1]["analysis_status"] == "ANALYSIS_FAILED"


def test_existing_job_row_is_reused_for_same_report_date(engine, settings) -> None:
    seed_stocks(engine, [1])
    clock = FakeClock()
    report_date = date(2026, 7, 9)

    first = batch(engine, settings, clock, stock_ids=[1]).run(report_date)
    second = batch(engine, settings, clock, stock_ids=[1]).run(report_date)

    assert first.batch_job_run_id == second.batch_job_run_id
    assert len(rows(engine, batch_job_run)) == 1


def test_stale_running_stock_run_is_recovered_before_publish(engine, settings) -> None:
    seed_stocks(engine, [1])
    clock = FakeClock()
    report_date = date(2026, 7, 9)
    with engine.begin() as connection:
        job_id = connection.execute(
            insert(batch_job_run).values(
                report_date=report_date,
                status="RUNNING",
                started_at=clock.now(),
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        ).inserted_primary_key[0]
        connection.execute(
            insert(batch_stock_run).values(
                batch_job_run_id=job_id,
                stock_id=1,
                report_date=report_date,
                status="RUNNING",
                attempt_count=1,
                started_at=clock.now(),
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )

    calls: list[int] = []
    result = batch(
        engine,
        settings,
        clock,
        stock_ids=[1],
        task=lambda stock_id: calls.append(stock_id),
    ).run(report_date)

    stock_run = rows(engine, batch_stock_run)[0]
    assert result.exit_code == 0
    assert calls == [1]
    assert stock_run["status"] == "SUCCEEDED"
    assert stock_run["attempt_count"] == 2


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


def test_postgres_advisory_lock_blocks_duplicate_connection() -> None:
    url = postgres_url()
    if not url:
        pytest.skip("WORKER_POSTGRES_TEST_URL is required for PostgreSQL advisory lock verification.")
    pg_engine = create_engine(url, future=True)
    report_date = date(2026, 7, 9)
    lock = PostgresAdvisoryBatchLock()
    with pg_engine.connect() as first, pg_engine.connect() as second:
        assert lock.acquire(first, report_date) is True
        assert lock.acquire(second, report_date) is False
        lock.release(first, report_date)


def test_postgres_advisory_lock_is_held_while_waiting_for_retry(settings) -> None:
    admin_engine, pg_engine, schema_name = make_flyway_postgres_engine()
    try:
        seed_stocks(pg_engine, [1])
        clock = FakeClock()
        report_date = date(2026, 7, 9)
        lock = PostgresAdvisoryBatchLock()
        calls: list[int] = []
        lock_blocked_during_sleep: list[bool] = []

        def flaky_task(stock_id: int) -> None:
            calls.append(stock_id)
            if len(calls) == 1:
                raise RuntimeError("temporary failure")

        def sleeper(seconds: float) -> None:
            with pg_engine.connect() as second:
                lock_blocked_during_sleep.append(not lock.acquire(second, report_date))
            clock.sleep(seconds)

        result = DailyReportBatch(
            engine=pg_engine,
            settings=settings,
            calendar=FakeCalendar(TradingDayStatus.OPEN),
            target_stock_provider=InMemoryTargetStockProvider([1]),
            stock_task=flaky_task,
            lock=lock,
            now=clock.now,
            sleeper=sleeper,
        ).run(report_date)

        assert result.exit_code == 0
        assert calls == [1, 1]
        assert lock_blocked_during_sleep == [True]
        with pg_engine.connect() as connection:
            assert lock.acquire(connection, report_date) is True
            lock.release(connection, report_date)
    finally:
        drop_schema(admin_engine, schema_name)


def test_postgres_flyway_schema_accepts_worker_state_transitions(settings) -> None:
    admin_engine, pg_engine, schema_name = make_flyway_postgres_engine()
    try:
        seed_stocks(pg_engine, [1, 2])
        clock = FakeClock()

        def task(stock_id: int) -> None:
            if stock_id == 2:
                raise PermanentAnalysisError("analysis failed")

        result = batch(
            pg_engine,
            settings,
            clock,
            stock_ids=[1, 2],
            task=task,
            lock=PostgresAdvisoryBatchLock(),
        ).run(date(2026, 7, 9))

        assert result.exit_code == 0
        assert rows(pg_engine, batch_job_run)[0]["status"] == "PUBLISHED_INITIAL"
        assert [row["status"] for row in rows(pg_engine, batch_stock_run)] == [
            "SUCCEEDED",
            "FAILED_PERMANENT",
        ]
        assert [row["analysis_status"] for row in rows(pg_engine, daily_stock_processing_status)] == [
            "DATA_PREPARING",
            "ANALYSIS_FAILED",
        ]
    finally:
        drop_schema(admin_engine, schema_name)
