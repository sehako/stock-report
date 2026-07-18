import logging

from jobs.stock_universe.application.dto import StockUniverseResult
from jobs.stock_universe.domain.repository import StockUniverseRepository
from jobs.stock_universe.domain.service import select_top_volume_stocks, stock_code_digest


class StockUniverseRunner:
    def __init__(self, krx_listing_client, stock_universe_repository: StockUniverseRepository):
        self._krx_listing_client = krx_listing_client
        self._stock_universe_repository = stock_universe_repository
        self._logger = logging.getLogger(__name__)

    def run(self) -> StockUniverseResult:
        self._logger.info("stock universe selection started")
        rows = self._krx_listing_client.fetch_krx_listing()
        selection = select_top_volume_stocks(rows)
        untracked_count = self._stock_universe_repository.replace_tracked_stocks(selection.stocks)
        tracked_codes = self._stock_universe_repository.find_tracked_stock_codes()

        selected_digest = stock_code_digest(stock.stock_code for stock in selection.stocks)
        tracked_digest = stock_code_digest(tracked_codes)
        result = StockUniverseResult(
            source_row_count=selection.source_row_count,
            valid_row_count=selection.valid_row_count,
            selected_count=len(selection.stocks),
            excluded_counts=dict(selection.excluded_counts),
            duplicate_stock_code_count=selection.duplicate_stock_code_count,
            untracked_count=untracked_count,
            selected_digest=selected_digest,
            tracked_digest=tracked_digest,
            digest_matched=selected_digest == tracked_digest,
        )
        self._logger.info(
            "stock universe selection completed: source=%s valid=%s selected=%s untracked=%s digest_matched=%s",
            result.source_row_count,
            result.valid_row_count,
            result.selected_count,
            result.untracked_count,
            result.digest_matched,
        )
        return result
