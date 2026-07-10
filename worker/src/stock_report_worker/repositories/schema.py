"""SQLAlchemy table definitions for Flyway-managed tables.

These definitions are references for SQL construction only. The worker never
calls create_all in runtime code.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()
id_type = BigInteger().with_variant(Integer, "sqlite")

stock = Table(
    "stock",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("stock_code", String(32), nullable=False),
    Column("stock_name", String(255), nullable=False),
    Column("market", String(16), nullable=False),
    Column("industry_name", String(255)),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint("stock_code", name="uq_stock_stock_code"),
)

batch_job_run = Table(
    "batch_job_run",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("report_date", Date, nullable=False),
    Column("status", String(32), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("last_error", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint("report_date", name="uq_batch_job_run_report_date"),
)

batch_stock_run = Table(
    "batch_stock_run",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("batch_job_run_id", BigInteger, nullable=False),
    Column("stock_id", BigInteger, nullable=False),
    Column("report_date", Date, nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempt_count", Integer, nullable=False),
    Column("next_retry_at", DateTime(timezone=True)),
    Column("last_error", Text),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint(
        "batch_job_run_id",
        "stock_id",
        name="uq_batch_stock_run_batch_job_run_id_stock_id",
    ),
)

daily_stock_processing_status = Table(
    "daily_stock_processing_status",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("report_date", Date, nullable=False),
    Column("stock_id", BigInteger, nullable=False),
    Column("analysis_status", String(32), nullable=False),
    Column("last_batch_job_run_id", BigInteger),
    Column("last_error", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint(
        "report_date",
        "stock_id",
        name="uq_daily_stock_processing_status_report_date_stock_id",
    ),
)

report_revision = Table(
    "report_revision",
    metadata,
    Column("id", id_type, primary_key=True, autoincrement=True),
    Column("report_date", Date, nullable=False),
    Column("revision_no", Integer, nullable=False),
    Column("revision_type", String(16), nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("calculation_version", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("published_at", DateTime(timezone=True)),
)
