package com.stockreport.marketindex.domain

enum class MarketIndexCode {
    KOSPI,
    KOSDAQ,

    ;

    companion object {
        fun from(value: String): MarketIndexCode? =
            entries.firstOrNull { it.name == value }
    }
}
