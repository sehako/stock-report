from datetime import date, timedelta


class FinanceDataReaderStockPriceClient:
    def fetch_daily_prices(
        self,
        stock_code: str,
        last_loaded_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        import FinanceDataReader as fdr

        if start_date is not None and end_date is not None:
            return fdr.DataReader(stock_code, start_date.isoformat(), end_date.isoformat())

        start = "1900-01-01"
        if last_loaded_date is not None:
            start = (last_loaded_date + timedelta(days=1)).isoformat()
        return fdr.DataReader(stock_code, start)
