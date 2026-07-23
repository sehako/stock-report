import argparse
from datetime import date
from typing import Sequence

from jobs.market_index_daily_price.application.dto import ReloadMarketIndexDailyPriceCommand
from jobs.stock_universe.application.stock_universe_runner import StockUniverseRunner
from jobs.stock_universe.infrastructure.client.finance_data_reader_client import FinanceDataReaderKrxListingClient
from jobs.stock_universe.infrastructure.persistence.stock_universe_repository import PsycopgStockUniverseRepository
from jobs.stock_daily_price.application.dto import ReloadStockDailyPriceCommand
from jobs.stock_daily_price.application.stock_daily_price_runner import StockDailyPriceRunner
from jobs.stock_daily_price.infrastructure.client.finance_data_reader_client import FinanceDataReaderStockPriceClient
from jobs.stock_daily_price.infrastructure.persistence.stock_daily_price_repository import (
    PsycopgStockDailyPriceRepository,
)
from jobs.market_index_daily_price.application.market_index_daily_price_runner import (
    MarketIndexDailyPriceRunner,
)
from jobs.market_index_daily_price.infrastructure.client.finance_data_reader_client import (
    FinanceDataReaderMarketIndexPriceClient,
)
from jobs.market_index_daily_price.infrastructure.persistence.market_index_daily_price_repository import (
    PsycopgMarketIndexDailyPriceRepository,
)
from shared.config import load_batch_config
from shared.logging import configure_logging


SUPPORTED_INDEX_CODES = {"KOSPI", "KOSDAQ"}


def main(argv: Sequence[str] | None = None) -> None:
    command = _parse_command(argv)
    config = load_batch_config()
    configure_logging(config.log_level)
    if isinstance(command, ReloadStockDailyPriceCommand):
        stock_daily_price_runner = StockDailyPriceRunner(
            FinanceDataReaderStockPriceClient(),
            PsycopgStockDailyPriceRepository(),
        )
        _ensure_targeted_reload_success(stock_daily_price_runner.run(command))
        return
    if isinstance(command, ReloadMarketIndexDailyPriceCommand):
        market_index_daily_price_runner = MarketIndexDailyPriceRunner(
            FinanceDataReaderMarketIndexPriceClient(),
            PsycopgMarketIndexDailyPriceRepository(),
        )
        _ensure_targeted_reload_success(market_index_daily_price_runner.run(command))
        return

    stock_universe_runner = StockUniverseRunner(
        FinanceDataReaderKrxListingClient(),
        PsycopgStockUniverseRepository(),
    )
    stock_universe_result = stock_universe_runner.run()
    if not stock_universe_result.digest_matched:
        raise RuntimeError("선정 종목 digest와 DB tracked digest가 일치하지 않습니다.")
    stock_daily_price_runner = StockDailyPriceRunner(
        FinanceDataReaderStockPriceClient(),
        PsycopgStockDailyPriceRepository(),
    )
    stock_daily_price_runner.run()
    market_index_daily_price_runner = MarketIndexDailyPriceRunner(
        FinanceDataReaderMarketIndexPriceClient(),
        PsycopgMarketIndexDailyPriceRepository(),
    )
    market_index_daily_price_runner.run()


def _parse_command(
    argv: Sequence[str] | None,
) -> ReloadStockDailyPriceCommand | ReloadMarketIndexDailyPriceCommand | None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-code")
    parser.add_argument("--index-code")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args(argv)

    if not any([args.stock_code, args.index_code, args.start_date, args.end_date]):
        return None
    if args.stock_code and args.index_code:
        parser.error("--stock-code와 --index-code는 동시에 지정할 수 없습니다.")
    if not (args.stock_code or args.index_code):
        parser.error("기간 옵션은 --stock-code 또는 --index-code와 함께 지정해야 합니다.")
    if not (args.start_date and args.end_date):
        parser.error("--start-date와 --end-date를 모두 지정해야 합니다.")

    start_date = _parse_date_argument(parser, "--start-date", args.start_date)
    end_date = _parse_date_argument(parser, "--end-date", args.end_date)
    if start_date > end_date:
        parser.error("--start-date는 --end-date보다 늦을 수 없습니다.")

    if args.stock_code:
        if not (len(args.stock_code) == 6 and args.stock_code.isdigit()):
            parser.error("--stock-code는 6자리 숫자 문자열이어야 합니다.")
        return ReloadStockDailyPriceCommand(
            stock_code=args.stock_code,
            start_date=start_date,
            end_date=end_date,
        )

    index_code = args.index_code.upper()
    if index_code not in SUPPORTED_INDEX_CODES:
        parser.error("--index-code는 KOSPI 또는 KOSDAQ만 지원합니다.")
    return ReloadMarketIndexDailyPriceCommand(
        index_code=index_code,
        start_date=start_date,
        end_date=end_date,
    )


def _parse_date_argument(parser: argparse.ArgumentParser, option_name: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        parser.error(f"{option_name}는 YYYY-MM-DD 형식이어야 합니다.")


def _ensure_targeted_reload_success(result) -> None:
    if not result.is_success:
        raise RuntimeError("지정 재수집에 실패했습니다.")
    if result.saved_price_count == 0:
        raise RuntimeError("지정 재수집에서 저장된 row가 없습니다.")


if __name__ == "__main__":
    main()
