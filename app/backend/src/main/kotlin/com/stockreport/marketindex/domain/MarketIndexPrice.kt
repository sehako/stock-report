package com.stockreport.marketindex.domain

import java.math.BigDecimal
import java.time.LocalDate

data class MarketIndexPrice(
    val indexCode: MarketIndexCode,
    val tradeDate: LocalDate,
    val closePrice: BigDecimal,
    val storedChangeRate: BigDecimal?,
)
