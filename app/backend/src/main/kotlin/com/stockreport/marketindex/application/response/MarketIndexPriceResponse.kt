package com.stockreport.marketindex.application.response

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexPricesResponse(
    val indexCode: String,
    val period: String,
    val startDate: LocalDate?,
    val endDate: LocalDate?,
    val items: List<MarketIndexPriceResponse>,
)

data class MarketIndexPriceResponse(
    val tradeDate: LocalDate,
    val openPrice: BigDecimal,
    val highPrice: BigDecimal,
    val lowPrice: BigDecimal,
    val closePrice: BigDecimal,
    val volume: Long,
    val changeRatePercent: BigDecimal?,
)
