"""Module execution entrypoint."""

from __future__ import annotations

import sys

from stock_report_worker.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
