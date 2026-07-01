from stock_report_worker.cli import main


def test_main_returns_none() -> None:
    assert main() is None
