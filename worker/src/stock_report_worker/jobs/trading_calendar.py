"""Trading day decision boundary."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Protocol


class TradingDayStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class TradingCalendar(Protocol):
    def status_for(self, report_date: date) -> TradingDayStatus:
        """Return the trading status for the report date."""


class WeekdayTradingCalendar:
    """Temporary calendar until the real KRX source is implemented."""

    def status_for(self, report_date: date) -> TradingDayStatus:
        return TradingDayStatus.OPEN if report_date.weekday() < 5 else TradingDayStatus.CLOSED
