from jobs.stock_universe.application.stock_universe_runner import StockUniverseRunner
from jobs.stock_universe.infrastructure.client.finance_data_reader_client import FinanceDataReaderKrxListingClient
from jobs.stock_universe.infrastructure.persistence.stock_universe_repository import PsycopgStockUniverseRepository
from shared.config import load_batch_config
from shared.logging import configure_logging


def main() -> None:
    config = load_batch_config()
    configure_logging(config.log_level)
    runner = StockUniverseRunner(
        FinanceDataReaderKrxListingClient(),
        PsycopgStockUniverseRepository(),
    )
    result = runner.run()
    if not result.digest_matched:
        raise RuntimeError("선정 종목 digest와 DB tracked digest가 일치하지 않습니다.")


if __name__ == "__main__":
    main()
