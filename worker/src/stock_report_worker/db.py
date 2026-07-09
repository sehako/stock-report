"""Database connection helpers for the worker."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import Connection


def create_worker_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine without creating or migrating schemas."""

    return create_engine(database_url, future=True)


@contextmanager
def transaction(engine: Engine) -> Iterator[Connection]:
    """Open a transaction-scoped connection."""

    with engine.begin() as connection:
        yield connection
