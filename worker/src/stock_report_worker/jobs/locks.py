"""Advisory lock boundary for one report-date batch."""

from __future__ import annotations

import hashlib
from datetime import date

from sqlalchemy import Connection, text


class BatchLock:
    def acquire(self, connection: Connection, report_date: date) -> bool:
        raise NotImplementedError

    def release(self, connection: Connection, report_date: date) -> None:
        return None


class NoopBatchLock(BatchLock):
    def acquire(self, connection: Connection, report_date: date) -> bool:
        return True


class PostgresAdvisoryBatchLock(BatchLock):
    def acquire(self, connection: Connection, report_date: date) -> bool:
        lock_key = advisory_lock_key(report_date)
        return bool(
            connection.execute(
                text("select pg_try_advisory_lock(:lock_key)"),
                {"lock_key": lock_key},
            ).scalar_one()
        )

    def release(self, connection: Connection, report_date: date) -> None:
        lock_key = advisory_lock_key(report_date)
        connection.execute(
            text("select pg_advisory_unlock(:lock_key)"),
            {"lock_key": lock_key},
        )


def advisory_lock_key(report_date: date) -> int:
    digest = hashlib.sha256(f"stock-report:{report_date.isoformat()}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)
