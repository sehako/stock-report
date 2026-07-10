package com.stockreport.market

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexTimeseriesResponse(
    val startDate: LocalDate,
    val endDate: LocalDate,
    val indices: List<MarketIndexSeriesDto>,
)

data class MarketIndexSeriesDto(
    val indexCode: String,
    val prices: List<MarketIndexPricePointDto>,
)

data class MarketIndexPricePointDto(
    val tradeDate: LocalDate,
    val openPrice: BigDecimal?,
    val highPrice: BigDecimal?,
    val lowPrice: BigDecimal?,
    val closePrice: BigDecimal?,
    val volume: Long?,
    val changeRate: BigDecimal?,
)
