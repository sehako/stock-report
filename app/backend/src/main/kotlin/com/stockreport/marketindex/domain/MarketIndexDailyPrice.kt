package com.stockreport.marketindex.domain

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexDailyPrice(
    val indexCode: MarketIndexCode,
    val tradeDate: LocalDate,
    val openPrice: BigDecimal,
    val highPrice: BigDecimal,
    val lowPrice: BigDecimal,
    val closePrice: BigDecimal,
    val volume: Long,
    val storedChangeRate: BigDecimal?,
)
