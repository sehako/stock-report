package com.stockreport.marketindex.domain

import java.time.LocalDate

enum class MarketIndexPricePeriod(
    val value: String,
) {
    ONE_MONTH("1M") {
        override fun startDateFrom(endDate: LocalDate): LocalDate = endDate.minusMonths(1)
    },
    THREE_MONTHS("3M") {
        override fun startDateFrom(endDate: LocalDate): LocalDate = endDate.minusMonths(3)
    },
    ONE_YEAR("1Y") {
        override fun startDateFrom(endDate: LocalDate): LocalDate = endDate.minusYears(1)
    },
    ;

    abstract fun startDateFrom(endDate: LocalDate): LocalDate

    companion object {
        fun from(value: String): MarketIndexPricePeriod? =
            entries.firstOrNull { it.value == value }
    }
}
