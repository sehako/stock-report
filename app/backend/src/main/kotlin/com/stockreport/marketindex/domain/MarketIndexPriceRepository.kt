package com.stockreport.marketindex.domain

interface MarketIndexPriceRepository {
    fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice>
}
