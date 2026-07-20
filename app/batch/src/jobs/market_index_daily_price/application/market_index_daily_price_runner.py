import logging

from jobs.market_index_daily_price.application.dto import (
    MarketIndexDailyPriceFailedIndex,
    MarketIndexDailyPriceResult,
)
from jobs.market_index_daily_price.domain.model import SUPPORTED_MARKET_INDEX_TARGETS
from jobs.market_index_daily_price.domain.repository import MarketIndexDailyPriceRepository
from jobs.market_index_daily_price.domain.service import normalize_market_index_daily_prices


class MarketIndexDailyPriceRunner:
    def __init__(
        self,
        market_index_price_client,
        market_index_daily_price_repository: MarketIndexDailyPriceRepository,
    ):
        self._market_index_price_client = market_index_price_client
        self._market_index_daily_price_repository = market_index_daily_price_repository
        self._logger = logging.getLogger(__name__)

    def run(self) -> MarketIndexDailyPriceResult:
        self._logger.info("market index daily price loading started")
        success_count = 0
        skipped_count = 0
        saved_price_count = 0
        failed_indexes: list[MarketIndexDailyPriceFailedIndex] = []

        for target in SUPPORTED_MARKET_INDEX_TARGETS:
            try:
                last_loaded_date = self._market_index_daily_price_repository.find_last_loaded_date(
                    target.index_code
                )
                rows = self._market_index_price_client.fetch_daily_prices(target, last_loaded_date)
                if _is_empty_rows(rows):
                    skipped_count += 1
                    self._logger.info(
                        "market index daily price skipped: index_code=%s reason=empty_source",
                        target.index_code,
                    )
                    continue

                collection = normalize_market_index_daily_prices(target.index_code, rows)
                saved_count = self._market_index_daily_price_repository.upsert_market_index_prices(
                    target.index_code,
                    collection.prices,
                )
                if saved_count == 0:
                    skipped_count += 1
                    continue
                success_count += 1
                saved_price_count += saved_count
                self._logger.info(
                    "market index daily price saved: index_code=%s saved=%s excluded=%s duplicated=%s",
                    target.index_code,
                    saved_count,
                    collection.excluded_row_count,
                    collection.duplicate_trade_date_count,
                )
            except Exception as exc:
                failed_indexes.append(
                    MarketIndexDailyPriceFailedIndex(
                        index_code=target.index_code,
                        reason=str(exc),
                    )
                )
                self._logger.exception(
                    "market index daily price failed: index_code=%s",
                    target.index_code,
                )

        result = MarketIndexDailyPriceResult(
            total_index_count=len(SUPPORTED_MARKET_INDEX_TARGETS),
            success_count=success_count,
            skipped_count=skipped_count,
            failed_count=len(failed_indexes),
            saved_price_count=saved_price_count,
            failed_indexes=failed_indexes,
        )
        failed_index_codes = ",".join(failed.index_code for failed in failed_indexes)
        self._logger.info(
            "market index daily price loading completed: total=%s success=%s skipped=%s failed=%s saved=%s failed_indexes=%s",
            result.total_index_count,
            result.success_count,
            result.skipped_count,
            result.failed_count,
            result.saved_price_count,
            failed_index_codes,
        )
        return result


def _is_empty_rows(rows) -> bool:
    empty = getattr(rows, "empty", None)
    if empty is not None:
        return bool(empty)
    return len(rows) == 0
