package com.stockreport.marketindex.presentation

import com.stockreport.marketindex.application.MarketIndexService
import com.stockreport.marketindex.application.response.MarketIndexSummariesResponse
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RestController

@RestController
class MarketIndexController(
    private val marketIndexService: MarketIndexService,
) {
    @GetMapping("/api/market-indexes")
    fun getMarketIndexSummaries(): MarketIndexSummariesResponse =
        marketIndexService.getMarketIndexSummaries()
}
