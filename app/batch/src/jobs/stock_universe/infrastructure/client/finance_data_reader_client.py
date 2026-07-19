class FinanceDataReaderKrxListingClient:
    def fetch_krx_listing(self):
        import FinanceDataReader as fdr

        return fdr.StockListing("KRX")
