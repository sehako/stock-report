package com.stockreport.market

import java.time.LocalDate
import org.springframework.format.annotation.DateTimeFormat
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/market-indices")
class MarketIndexController(
    private val marketIndexService: MarketIndexService,
) {

    @GetMapping("/timeseries")
    fun getTimeseries(
        @RequestParam
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        startDate: LocalDate,
        @RequestParam
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        endDate: LocalDate,
    ): MarketIndexTimeseriesResponse =
        marketIndexService.getTimeseries(startDate, endDate)
}
