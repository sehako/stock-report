package com.stockreport.marketindex.domain

import java.time.LocalDate

interface MarketIndexPriceRepository {
    fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice>

    fun findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate?

    fun findDailyPricesByIndexCodeAndTradeDateBetween(
        indexCode: MarketIndexCode,
        startDate: LocalDate,
        endDate: LocalDate,
    ): List<MarketIndexDailyPrice>
}
