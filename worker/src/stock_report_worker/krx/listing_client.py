"""FinanceDataReader KRX listing client and provider."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from stock_report_worker.db import transaction
from stock_report_worker.krx.normalization import (
    KrxListedStock,
    KrxStockListingUnavailable,
    KrxStockListingUnavailableReason,
    normalize_krx_stock_listing,
)
from stock_report_worker.repositories.stocks import StockRepository


class KrxListingClient(Protocol):
    def stock_listing(self, market: str) -> pd.DataFrame:
        """Return a FinanceDataReader StockListing frame."""


class FinanceDataReaderKrxListingClient:
    def stock_listing(self, market: str) -> pd.DataFrame:
        import FinanceDataReader as fdr

        return fdr.StockListing(market)


class KrxStockListingProvider:
    def __init__(
        self,
        engine: Engine,
        client: KrxListingClient | None = None,
        stock_repository: StockRepository | None = None,
    ) -> None:
        self.engine = engine
        self.client = client or FinanceDataReaderKrxListingClient()
        self.stock_repository = stock_repository or StockRepository()

    def collect(self, now: datetime) -> list[KrxListedStock]:
        listing_frame = self._fetch("KRX", KrxStockListingUnavailableReason.KRX_LISTING_FETCH_FAILED)
        desc_frame = self._fetch("KRX-DESC", KrxStockListingUnavailableReason.KRX_DESC_FETCH_FAILED)
        listed_stocks = normalize_krx_stock_listing(listing_frame, desc_frame)
        try:
            with transaction(self.engine) as connection:
                stock_ids = self.stock_repository.upsert_listed_stocks(connection, listed_stocks, now)
        except SQLAlchemyError as exc:
            raise KrxStockListingUnavailable(
                KrxStockListingUnavailableReason.STOCK_UPSERT_FAILED,
                "stock metadata upsert failed",
            ) from exc
        return [
            listed_stock.with_stock_id(stock_id)
            for listed_stock, stock_id in zip(listed_stocks, stock_ids, strict=True)
        ]

    def _fetch(self, market: str, reason: KrxStockListingUnavailableReason) -> pd.DataFrame:
        try:
            return self.client.stock_listing(market)
        except KrxStockListingUnavailable:
            raise
        except Exception as exc:
            raise KrxStockListingUnavailable(reason, f"{market} StockListing failed") from exc
