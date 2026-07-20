from jobs.stock_universe.application.stock_universe_runner import StockUniverseRunner
from jobs.stock_universe.infrastructure.client.finance_data_reader_client import FinanceDataReaderKrxListingClient
from jobs.stock_universe.infrastructure.persistence.stock_universe_repository import PsycopgStockUniverseRepository
from jobs.stock_daily_price.application.stock_daily_price_runner import StockDailyPriceRunner
from jobs.stock_daily_price.infrastructure.client.finance_data_reader_client import FinanceDataReaderStockPriceClient
from jobs.stock_daily_price.infrastructure.persistence.stock_daily_price_repository import (
    PsycopgStockDailyPriceRepository,
)
from shared.config import load_batch_config
from shared.logging import configure_logging


def main() -> None:
    config = load_batch_config()
    configure_logging(config.log_level)
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


if __name__ == "__main__":
    main()
