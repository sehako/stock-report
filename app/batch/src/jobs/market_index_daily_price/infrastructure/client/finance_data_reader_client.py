from datetime import date, timedelta

from jobs.market_index_daily_price.domain.model import MarketIndexTarget


class FinanceDataReaderMarketIndexPriceClient:
    def fetch_daily_prices(
        self,
        target: MarketIndexTarget,
        last_loaded_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        import FinanceDataReader as fdr

        if start_date is not None and end_date is not None:
            return fdr.DataReader(target.fdr_symbol, start_date.isoformat(), end_date.isoformat())

        start = "1900-01-01"
        if last_loaded_date is not None:
            start = (last_loaded_date + timedelta(days=1)).isoformat()
        return fdr.DataReader(target.fdr_symbol, start)
