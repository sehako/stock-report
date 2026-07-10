"""Repository for daily stock processing status."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Connection, and_, delete, insert, select, update

from stock_report_worker.repositories.schema import daily_stock_processing_status


class ProcessingStatusRepository:
    def prune_to_stock_ids(
        self,
        connection: Connection,
        *,
        report_date: date,
        stock_ids: list[int],
    ) -> None:
        statement = delete(daily_stock_processing_status).where(
            daily_stock_processing_status.c.report_date == report_date
        )
        if stock_ids:
            statement = statement.where(daily_stock_processing_status.c.stock_id.not_in(stock_ids))
        connection.execute(statement)

    def upsert_status(
        self,
        connection: Connection,
        *,
        report_date: date,
        stock_id: int,
        analysis_status: str,
        batch_job_run_id: int,
        now: datetime,
        last_error: str | None = None,
    ) -> None:
        existing = connection.execute(
            select(daily_stock_processing_status.c.id).where(
                and_(
                    daily_stock_processing_status.c.report_date == report_date,
                    daily_stock_processing_status.c.stock_id == stock_id,
                )
            )
        ).first()
        values = {
            "analysis_status": analysis_status,
            "last_batch_job_run_id": batch_job_run_id,
            "last_error": last_error,
            "updated_at": now,
        }
        if existing is None:
            connection.execute(
                insert(daily_stock_processing_status).values(
                    report_date=report_date,
                    stock_id=stock_id,
                    created_at=now,
                    **values,
                )
            )
        else:
            connection.execute(
                update(daily_stock_processing_status)
                .where(daily_stock_processing_status.c.id == existing[0])
                .values(**values)
            )
