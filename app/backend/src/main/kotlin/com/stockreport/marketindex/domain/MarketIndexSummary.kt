package com.stockreport.marketindex.domain

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexSummary(
    val indexCode: MarketIndexCode,
    val status: MarketIndexSummaryStatus,
    val tradeDate: LocalDate?,
    val closePrice: BigDecimal?,
    val changeValue: BigDecimal?,
    val changeRatePercent: BigDecimal?,
)

enum class MarketIndexSummaryStatus {
    AVAILABLE,
    PARTIAL,
    EMPTY,
}
