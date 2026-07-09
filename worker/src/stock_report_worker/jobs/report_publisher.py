"""Initial report publication boundary."""

from __future__ import annotations

from datetime import date
from typing import Protocol


class InitialReportPublisher(Protocol):
    def publish_initial(self, report_date: date, batch_job_run_id: int) -> None:
        """Publish the initial report revision boundary."""


class NoopInitialReportPublisher:
    def publish_initial(self, report_date: date, batch_job_run_id: int) -> None:
        return None
