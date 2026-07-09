"""Sequential stock execution orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine

from stock_report_worker.db import transaction
from stock_report_worker.jobs.retry_policy import RetryPolicy
from stock_report_worker.jobs.timeout import StockFetchTimeout, TimeoutRunner
from stock_report_worker.repositories.batch_runs import (
    BatchStockRun,
    BatchStockRunRepository,
)
from stock_report_worker.repositories.processing_status import ProcessingStatusRepository


class PermanentDataUpdateError(Exception):
    """A non-retryable data update failure."""


class PermanentAnalysisError(Exception):
    """A non-retryable placeholder analysis failure."""


StockTask = Callable[[int], None]


class SequentialStockRunner:
    def __init__(
        self,
        *,
        engine: Engine,
        retry_policy: RetryPolicy,
        timeout_runner: TimeoutRunner,
        now: Callable[[], datetime],
        consecutive_timeout_limit: int,
        stock_runs: BatchStockRunRepository | None = None,
        processing_status: ProcessingStatusRepository | None = None,
    ) -> None:
        self._engine = engine
        self._retry_policy = retry_policy
        self._timeout_runner = timeout_runner
        self._now = now
        self._consecutive_timeout_limit = consecutive_timeout_limit
        self._stock_runs = stock_runs or BatchStockRunRepository()
        self._processing_status = processing_status or ProcessingStatusRepository()

    def run_once(
        self,
        *,
        job_id: int,
        runs: list[BatchStockRun],
        task: StockTask,
    ) -> bool:
        """Process currently eligible runs. Return True when provider outage stopped the pass."""

        consecutive_timeouts = 0
        processed_run_ids: set[int] = set()

        for run in runs:
            processed_run_ids.add(run.id)
            now = self._now()
            with transaction(self._engine) as connection:
                self._stock_runs.mark_running(connection, run_id=run.id, now=now)
                self._processing_status.upsert_status(
                    connection,
                    report_date=run.report_date,
                    stock_id=run.stock_id,
                    analysis_status="DATA_PREPARING",
                    batch_job_run_id=job_id,
                    now=now,
                )

            try:
                self._timeout_runner.run(lambda stock_id=run.stock_id: task(stock_id))
            except StockFetchTimeout as exc:
                consecutive_timeouts += 1
                self._record_retryable_failure(run, job_id, str(exc), "DATA_PREPARING")
                if consecutive_timeouts >= self._consecutive_timeout_limit:
                    self._defer_unstarted(
                        job_id=job_id,
                        processed_run_ids=processed_run_ids,
                        report_date=run.report_date,
                        last_error="provider timeout threshold reached",
                    )
                    return True
            except PermanentDataUpdateError as exc:
                consecutive_timeouts = 0
                self._record_permanent_failure(run, job_id, str(exc), "DATA_UPDATE_FAILED")
            except PermanentAnalysisError as exc:
                consecutive_timeouts = 0
                self._record_permanent_failure(run, job_id, str(exc), "ANALYSIS_FAILED")
            except Exception as exc:
                consecutive_timeouts = 0
                self._record_retryable_failure(run, job_id, str(exc), "DATA_PREPARING")
            else:
                consecutive_timeouts = 0
                now = self._now()
                with transaction(self._engine) as connection:
                    self._stock_runs.mark_succeeded(
                        connection,
                        run_id=run.id,
                        attempt_count=run.attempt_count + 1,
                        now=now,
                    )

        return False

    def _record_retryable_failure(
        self, run: BatchStockRun, job_id: int, last_error: str, analysis_status: str
    ) -> None:
        now = self._now()
        attempt_count = run.attempt_count + 1
        decision = self._retry_policy.decide(attempt_count=attempt_count, now=now)
        final_analysis_status = (
            "DATA_UPDATE_FAILED" if decision.status == "FAILED_PERMANENT" else analysis_status
        )
        with transaction(self._engine) as connection:
            self._stock_runs.mark_failed(
                connection,
                run_id=run.id,
                status=decision.status,
                attempt_count=attempt_count,
                next_retry_at=decision.next_retry_at,
                last_error=last_error,
                now=now,
            )
            self._processing_status.upsert_status(
                connection,
                report_date=run.report_date,
                stock_id=run.stock_id,
                analysis_status=final_analysis_status,
                batch_job_run_id=job_id,
                now=now,
                last_error=last_error,
            )

    def _record_permanent_failure(
        self, run: BatchStockRun, job_id: int, last_error: str, analysis_status: str
    ) -> None:
        now = self._now()
        with transaction(self._engine) as connection:
            self._stock_runs.mark_failed(
                connection,
                run_id=run.id,
                status="FAILED_PERMANENT",
                attempt_count=run.attempt_count + 1,
                next_retry_at=None,
                last_error=last_error,
                now=now,
            )
            self._processing_status.upsert_status(
                connection,
                report_date=run.report_date,
                stock_id=run.stock_id,
                analysis_status=analysis_status,
                batch_job_run_id=job_id,
                now=now,
                last_error=last_error,
            )

    def _defer_unstarted(
        self,
        *,
        job_id: int,
        processed_run_ids: set[int],
        report_date,
        last_error: str,
    ) -> None:
        now = self._now()
        next_retry_at = now + self._retry_policy.retry_interval
        with transaction(self._engine) as connection:
            stock_ids = self._stock_runs.defer_unstarted(
                connection,
                job_id=job_id,
                processed_run_ids=processed_run_ids,
                next_retry_at=next_retry_at,
                now=now,
                last_error=last_error,
            )
            for stock_id in stock_ids:
                self._processing_status.upsert_status(
                    connection,
                    report_date=report_date,
                    stock_id=stock_id,
                    analysis_status="DATA_PREPARING",
                    batch_job_run_id=job_id,
                    now=now,
                    last_error=last_error,
                )
