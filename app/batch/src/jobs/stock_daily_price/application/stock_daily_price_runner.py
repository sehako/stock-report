import logging

from jobs.stock_daily_price.application.dto import (
    StockDailyPriceFailedStock,
    StockDailyPriceResult,
)
from jobs.stock_daily_price.domain.repository import StockDailyPriceRepository
from jobs.stock_daily_price.domain.service import normalize_stock_daily_prices


class StockDailyPriceRunner:
    def __init__(self, stock_price_client, stock_daily_price_repository: StockDailyPriceRepository):
        self._stock_price_client = stock_price_client
        self._stock_daily_price_repository = stock_daily_price_repository
        self._logger = logging.getLogger(__name__)

    def run(self) -> StockDailyPriceResult:
        self._logger.info("stock daily price loading started")
        tracked_stocks = self._stock_daily_price_repository.find_tracked_stocks_with_last_loaded_date()
        success_count = 0
        skipped_count = 0
        saved_price_count = 0
        failed_stocks: list[StockDailyPriceFailedStock] = []

        for stock in tracked_stocks:
            try:
                rows = self._stock_price_client.fetch_daily_prices(
                    stock.stock_code,
                    stock.last_loaded_date,
                )
                if _is_empty_rows(rows):
                    skipped_count += 1
                    self._logger.info(
                        "stock daily price skipped: stock_code=%s stock_name=%s reason=empty_source",
                        stock.stock_code,
                        stock.stock_name,
                    )
                    continue

                collection = normalize_stock_daily_prices(stock.stock_id, rows)
                saved_count = self._stock_daily_price_repository.upsert_stock_prices(
                    stock.stock_id,
                    collection.prices,
                )
                if saved_count == 0:
                    skipped_count += 1
                    continue
                success_count += 1
                saved_price_count += saved_count
                self._logger.info(
                    "stock daily price saved: stock_code=%s stock_name=%s saved=%s excluded=%s duplicated=%s",
                    stock.stock_code,
                    stock.stock_name,
                    saved_count,
                    collection.excluded_row_count,
                    collection.duplicate_trade_date_count,
                )
            except Exception as exc:
                failed_stocks.append(
                    StockDailyPriceFailedStock(
                        stock_id=stock.stock_id,
                        stock_code=stock.stock_code,
                        stock_name=stock.stock_name,
                        reason=str(exc),
                    )
                )
                self._logger.exception(
                    "stock daily price failed: stock_code=%s stock_name=%s",
                    stock.stock_code,
                    stock.stock_name,
                )

        result = StockDailyPriceResult(
            total_stock_count=len(tracked_stocks),
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=len(failed_stocks),
            saved_price_count=saved_price_count,
            failed_stocks=failed_stocks,
        )
        self._logger.info(
            "stock daily price loading completed: total=%s success=%s skipped=%s failed=%s saved=%s",
            result.total_stock_count,
            result.success_count,
            result.skipped_count,
            result.failed_count,
            result.saved_price_count,
        )
        return result


def _is_empty_rows(rows) -> bool:
    empty = getattr(rows, "empty", None)
    if empty is not None:
        return bool(empty)
    return len(rows) == 0
