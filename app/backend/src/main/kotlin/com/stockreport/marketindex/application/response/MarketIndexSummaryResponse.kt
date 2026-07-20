package com.stockreport.marketindex.application.response

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexSummariesResponse(
    val items: List<MarketIndexSummaryResponse>,
)

data class MarketIndexSummaryResponse(
    val indexCode: String,
    val status: String,
    val tradeDate: LocalDate?,
    val closePrice: BigDecimal?,
    val changeValue: BigDecimal?,
    val changeRatePercent: BigDecimal?,
)
