"""One-shot daily report batch orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from time import sleep

from sqlalchemy import Engine

from stock_report_worker.config import WorkerSettings
from stock_report_worker.db import transaction
from stock_report_worker.jobs.locks import BatchLock, NoopBatchLock, PostgresAdvisoryBatchLock
from stock_report_worker.jobs.report_publisher import (
    InitialReportPublisher,
    NoopInitialReportPublisher,
)
from stock_report_worker.jobs.retry_policy import RetryPolicy
from stock_report_worker.jobs.stock_runner import SequentialStockRunner, StockTask
from stock_report_worker.jobs.target_stocks import KrxTargetStockProvider, TargetStockProvider
from stock_report_worker.jobs.timeout import TimeoutRunner
from stock_report_worker.jobs.trading_calendar import TradingCalendar, TradingDayStatus, WeekdayTradingCalendar
from stock_report_worker.krx.listing_client import KrxStockListingProvider
from stock_report_worker.krx.normalization import KrxStockListingUnavailable
from stock_report_worker.repositories.batch_runs import BatchJobRunRepository, BatchStockRunRepository
from stock_report_worker.repositories.processing_status import ProcessingStatusRepository


@dataclass(frozen=True)
class DailyReportResult:
    exit_code: int
    status: str
    batch_job_run_id: int | None = None


class DailyReportBatch:
    def __init__(
        self,
        *,
        engine: Engine,
        settings: WorkerSettings,
        calendar: TradingCalendar | None = None,
        target_stock_provider: TargetStockProvider | None = None,
        stock_task: StockTask | None = None,
        publisher: InitialReportPublisher | None = None,
        lock: BatchLock | None = None,
        now: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._calendar = calendar or WeekdayTradingCalendar()
        self._stock_task = stock_task or (lambda stock_id: None)
        self._publisher = publisher or NoopInitialReportPublisher()
        self._lock = lock or self._default_lock(engine)
        self._now = now or (lambda: datetime.now(settings.zoneinfo))
        self._target_stock_provider = target_stock_provider or KrxTargetStockProvider(
            KrxStockListingProvider(engine),
            now=self._now,
        )
        self._sleeper = sleeper or sleep
        self._jobs = BatchJobRunRepository()
        self._stock_runs = BatchStockRunRepository()
        self._processing_status = ProcessingStatusRepository()

    def run(self, report_date: date) -> DailyReportResult:
        with self._engine.connect() as lock_connection:
            if not self._lock.acquire(lock_connection, report_date):
                return DailyReportResult(exit_code=0, status="DUPLICATE_SKIPPED")

            try:
                now = self._now()
                with transaction(self._engine) as connection:
                    job = self._jobs.get_or_create_running(connection, report_date, now)

                status = self._calendar.status_for(report_date)
                if status == TradingDayStatus.CLOSED:
                    now = self._now()
                    with transaction(self._engine) as connection:
                        self._jobs.mark_status(
                            connection,
                            job.id,
                            "SKIPPED_MARKET_CLOSED",
                            now,
                            finished=True,
                        )
                    return DailyReportResult(0, "SKIPPED_MARKET_CLOSED", job.id)

                if status == TradingDayStatus.UNKNOWN:
                    now = self._now()
                    with transaction(self._engine) as connection:
                        self._jobs.mark_status(
                            connection,
                            job.id,
                            "FAILED",
                            now,
                            last_error="trading day status is unknown",
                            finished=True,
                        )
                    return DailyReportResult(1, "FAILED", job.id)

                try:
                    self._run_open_day(report_date, job.id)
                except KrxStockListingUnavailable as exc:
                    now = self._now()
                    with transaction(self._engine) as connection:
                        self._jobs.mark_status(
                            connection,
                            job.id,
                            "DELAYED",
                            now,
                            last_error=f"{exc.reason}: {exc.message}",
                            finished=True,
                        )
                    return DailyReportResult(1, "DELAYED", job.id)
                except Exception as exc:
                    now = self._now()
                    with transaction(self._engine) as connection:
                        self._jobs.mark_status(
                            connection,
                            job.id,
                            "FAILED",
                            now,
                            last_error=str(exc),
                            finished=True,
                        )
                    return DailyReportResult(1, "FAILED", job.id)

                return DailyReportResult(0, "PUBLISHED_INITIAL", job.id)
            finally:
                self._lock.release(lock_connection, report_date)

    def _run_open_day(self, report_date: date, job_id: int) -> None:
        retry_policy = RetryPolicy(
            max_retries=self._settings.max_retries,
            retry_interval=self._settings.retry_interval,
        )
        target_stocks = self._target_stock_provider.list_for(report_date)
        target_stock_ids = [stock.id for stock in target_stocks]
        now = self._now()
        with transaction(self._engine) as connection:
            self._stock_runs.prune_to_stock_ids(
                connection,
                job_id=job_id,
                stock_ids=target_stock_ids,
            )
            self._processing_status.prune_to_stock_ids(
                connection,
                report_date=report_date,
                stock_ids=target_stock_ids,
            )
            self._stock_runs.ensure_pending(
                connection,
                job_id=job_id,
                report_date=report_date,
                stock_ids=target_stock_ids,
                now=now,
            )
            for target_stock in target_stocks:
                self._processing_status.upsert_status(
                    connection,
                    report_date=report_date,
                    stock_id=target_stock.id,
                    analysis_status="DATA_PREPARING",
                    batch_job_run_id=job_id,
                    now=now,
                )
            self._stock_runs.recover_running_as_retryable(
                connection,
                job_id=job_id,
                now=now,
                last_error="recovered stale running stock run",
            )

        stock_runner = SequentialStockRunner(
            engine=self._engine,
            retry_policy=retry_policy,
            timeout_runner=TimeoutRunner(self._settings.stock_timeout_seconds),
            now=self._now,
            consecutive_timeout_limit=self._settings.consecutive_timeout_limit,
        )

        while True:
            now = self._now()
            with transaction(self._engine) as connection:
                processable = self._stock_runs.list_processable(connection, job_id=job_id, now=now)

            if processable:
                provider_outage = stock_runner.run_once(
                    job_id=job_id,
                    runs=processable,
                    task=self._stock_task,
                )
                now = self._now()
                with transaction(self._engine) as connection:
                    unfinished = self._stock_runs.count_unfinished(connection, job_id=job_id)
                    if unfinished:
                        self._jobs.mark_status(connection, job_id, "RETRYING", now)
                    if provider_outage:
                        continue
                continue

            with transaction(self._engine) as connection:
                retryable = self._stock_runs.list_retryable(connection, job_id=job_id)
                unfinished = self._stock_runs.count_unfinished(connection, job_id=job_id)
            if unfinished == 0:
                break
            if retryable:
                earliest = min(run.next_retry_at for run in retryable if run.next_retry_at is not None)
                if earliest is not None:
                    current = self._now()
                    if earliest.tzinfo is None and current.tzinfo is not None:
                        current = current.replace(tzinfo=None)
                    elif earliest.tzinfo is not None and current.tzinfo is None:
                        earliest = earliest.replace(tzinfo=None)
                    delay = max(0.0, (earliest - current).total_seconds())
                    if delay:
                        now = self._now()
                        with transaction(self._engine) as connection:
                            self._jobs.mark_status(connection, job_id, "RETRYING", now)
                        self._sleeper(delay)
                    continue
            raise RuntimeError("batch has unfinished stock runs without retryable schedule")

        self._publisher.publish_initial(report_date, job_id)
        now = self._now()
        with transaction(self._engine) as connection:
            self._jobs.mark_status(
                connection,
                job_id,
                "PUBLISHED_INITIAL",
                now,
                finished=True,
            )

    def _default_lock(self, engine: Engine) -> BatchLock:
        if engine.dialect.name == "postgresql":
            return PostgresAdvisoryBatchLock()
        return NoopBatchLock()


def run() -> None:
    """Backward-compatible import check entrypoint."""

    return None
