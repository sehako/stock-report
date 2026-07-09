"""Repositories for batch job and stock run state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Connection, Select, and_, insert, select, update

from stock_report_worker.repositories.schema import batch_job_run, batch_stock_run


@dataclass(frozen=True)
class BatchJobRun:
    id: int
    report_date: date
    status: str


@dataclass(frozen=True)
class BatchStockRun:
    id: int
    batch_job_run_id: int
    stock_id: int
    report_date: date
    status: str
    attempt_count: int
    next_retry_at: datetime | None


class BatchJobRunRepository:
    def get_or_create_running(
        self, connection: Connection, report_date: date, now: datetime
    ) -> BatchJobRun:
        row = connection.execute(
            select(batch_job_run).where(batch_job_run.c.report_date == report_date)
        ).mappings().first()
        if row is None:
            result = connection.execute(
                insert(batch_job_run).values(
                    report_date=report_date,
                    status="RUNNING",
                    started_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            job_id = int(result.inserted_primary_key[0])
        else:
            job_id = int(row["id"])
            connection.execute(
                update(batch_job_run)
                .where(batch_job_run.c.id == job_id)
                .values(status="RUNNING", started_at=now, finished_at=None, last_error=None, updated_at=now)
            )
        return self.get(connection, report_date)

    def get(self, connection: Connection, report_date: date) -> BatchJobRun:
        row = connection.execute(
            select(batch_job_run).where(batch_job_run.c.report_date == report_date)
        ).mappings().one()
        return BatchJobRun(
            id=int(row["id"]),
            report_date=row["report_date"],
            status=str(row["status"]),
        )

    def mark_status(
        self,
        connection: Connection,
        job_id: int,
        status: str,
        now: datetime,
        *,
        last_error: str | None = None,
        finished: bool = False,
    ) -> None:
        values: dict[str, object] = {
            "status": status,
            "last_error": last_error,
            "updated_at": now,
        }
        if finished:
            values["finished_at"] = now
        connection.execute(
            update(batch_job_run).where(batch_job_run.c.id == job_id).values(**values)
        )


class BatchStockRunRepository:
    def ensure_pending(
        self,
        connection: Connection,
        *,
        job_id: int,
        report_date: date,
        stock_ids: list[int],
        now: datetime,
    ) -> None:
        for stock_id in stock_ids:
            existing = connection.execute(
                select(batch_stock_run.c.id).where(
                    and_(
                        batch_stock_run.c.batch_job_run_id == job_id,
                        batch_stock_run.c.stock_id == stock_id,
                    )
                )
            ).first()
            if existing is None:
                connection.execute(
                    insert(batch_stock_run).values(
                        batch_job_run_id=job_id,
                        stock_id=stock_id,
                        report_date=report_date,
                        status="PENDING",
                        attempt_count=0,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def recover_running_as_retryable(
        self,
        connection: Connection,
        *,
        job_id: int,
        now: datetime,
        last_error: str,
    ) -> list[int]:
        rows = connection.execute(
            select(batch_stock_run.c.id, batch_stock_run.c.stock_id).where(
                and_(
                    batch_stock_run.c.batch_job_run_id == job_id,
                    batch_stock_run.c.status == "RUNNING",
                )
            )
        ).mappings().all()
        recovered: list[int] = []
        for row in rows:
            connection.execute(
                update(batch_stock_run)
                .where(batch_stock_run.c.id == row["id"])
                .values(
                    status="RETRYABLE",
                    next_retry_at=now,
                    last_error=last_error,
                    finished_at=now,
                    updated_at=now,
                )
            )
            recovered.append(int(row["stock_id"]))
        return recovered

    def list_processable(
        self, connection: Connection, *, job_id: int, now: datetime
    ) -> list[BatchStockRun]:
        statement: Select = (
            select(batch_stock_run)
            .where(
                and_(
                    batch_stock_run.c.batch_job_run_id == job_id,
                    batch_stock_run.c.status.in_(["PENDING", "RETRYABLE"]),
                )
            )
            .order_by(batch_stock_run.c.id.asc())
        )
        rows = connection.execute(statement).mappings().all()
        return [
            self._from_row(row)
            for row in rows
            if row["status"] == "PENDING"
            or row["next_retry_at"] is None
            or _is_due(row["next_retry_at"], now)
        ]

    def list_retryable(self, connection: Connection, *, job_id: int) -> list[BatchStockRun]:
        rows = connection.execute(
            select(batch_stock_run)
            .where(
                and_(
                    batch_stock_run.c.batch_job_run_id == job_id,
                    batch_stock_run.c.status == "RETRYABLE",
                )
            )
            .order_by(batch_stock_run.c.next_retry_at.asc())
        ).mappings().all()
        return [self._from_row(row) for row in rows]

    def count_unfinished(self, connection: Connection, *, job_id: int) -> int:
        rows = connection.execute(
            select(batch_stock_run.c.status).where(batch_stock_run.c.batch_job_run_id == job_id)
        ).all()
        return sum(1 for row in rows if row[0] not in {"SUCCEEDED", "FAILED_PERMANENT"})

    def mark_running(self, connection: Connection, *, run_id: int, now: datetime) -> None:
        connection.execute(
            update(batch_stock_run)
            .where(batch_stock_run.c.id == run_id)
            .values(status="RUNNING", started_at=now, finished_at=None, updated_at=now)
        )

    def mark_succeeded(
        self, connection: Connection, *, run_id: int, attempt_count: int, now: datetime
    ) -> None:
        connection.execute(
            update(batch_stock_run)
            .where(batch_stock_run.c.id == run_id)
            .values(
                status="SUCCEEDED",
                attempt_count=attempt_count,
                next_retry_at=None,
                last_error=None,
                finished_at=now,
                updated_at=now,
            )
        )

    def mark_failed(
        self,
        connection: Connection,
        *,
        run_id: int,
        status: str,
        attempt_count: int,
        next_retry_at: datetime | None,
        last_error: str,
        now: datetime,
    ) -> None:
        connection.execute(
            update(batch_stock_run)
            .where(batch_stock_run.c.id == run_id)
            .values(
                status=status,
                attempt_count=attempt_count,
                next_retry_at=next_retry_at,
                last_error=last_error,
                finished_at=now,
                updated_at=now,
            )
        )

    def defer_unstarted(
        self,
        connection: Connection,
        *,
        job_id: int,
        processed_run_ids: set[int],
        next_retry_at: datetime,
        now: datetime,
        last_error: str,
    ) -> list[int]:
        rows = connection.execute(
            select(batch_stock_run).where(
                and_(
                    batch_stock_run.c.batch_job_run_id == job_id,
                    batch_stock_run.c.status.in_(["PENDING", "RETRYABLE"]),
                )
            )
        ).mappings().all()
        deferred: list[int] = []
        for row in rows:
            if int(row["id"]) in processed_run_ids:
                continue
            connection.execute(
                update(batch_stock_run)
                .where(batch_stock_run.c.id == row["id"])
                .values(
                    status="RETRYABLE",
                    next_retry_at=next_retry_at,
                    last_error=last_error,
                    updated_at=now,
                )
            )
            deferred.append(int(row["stock_id"]))
        return deferred

    def _from_row(self, row: object) -> BatchStockRun:
        mapping = dict(row)
        return BatchStockRun(
            id=int(mapping["id"]),
            batch_job_run_id=int(mapping["batch_job_run_id"]),
            stock_id=int(mapping["stock_id"]),
            report_date=mapping["report_date"],
            status=str(mapping["status"]),
            attempt_count=int(mapping["attempt_count"]),
            next_retry_at=mapping["next_retry_at"],
        )


def _is_due(next_retry_at: datetime, now: datetime) -> bool:
    if next_retry_at.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    elif next_retry_at.tzinfo is not None and now.tzinfo is None:
        next_retry_at = next_retry_at.replace(tzinfo=None)
    return next_retry_at <= now
