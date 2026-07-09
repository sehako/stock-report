"""Command-line interface for the one-shot worker."""

from __future__ import annotations

import argparse
from datetime import date, datetime

from stock_report_worker.config import WorkerSettings
from stock_report_worker.db import create_worker_engine
from stock_report_worker.jobs.daily_report import DailyReportBatch


def determine_report_date(now: datetime, timezone_name: str = "Asia/Seoul") -> date:
    from zoneinfo import ZoneInfo

    return now.astimezone(ZoneInfo(timezone_name)).date()


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stock-report-worker")
    parser.add_argument("--report-date", help="Report date in YYYY-MM-DD format.")
    args = parser.parse_args(argv)

    settings = WorkerSettings()
    report_date = (
        date.fromisoformat(args.report_date)
        if args.report_date
        else determine_report_date(datetime.now(settings.zoneinfo), settings.timezone)
    )
    engine = create_worker_engine(settings.database_url)
    result = DailyReportBatch(engine=engine, settings=settings).run(report_date)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    return run_cli(argv)
