from datetime import datetime
from zoneinfo import ZoneInfo

from stock_report_worker.cli import determine_report_date, main


def test_main_help_returns_zero(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "stock-report-worker" in capsys.readouterr().out


def test_report_date_is_determined_in_asia_seoul() -> None:
    utc_now = datetime(2026, 7, 8, 15, 10, tzinfo=ZoneInfo("UTC"))
    assert determine_report_date(utc_now).isoformat() == "2026-07-09"
