package com.stockreport.marketindex.infrastructure.persistence

import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository
import java.sql.ResultSet

@Repository
class MarketIndexPriceRepositoryImpl(
    private val jdbcTemplate: JdbcTemplate,
) : MarketIndexPriceRepository {
    override fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice> =
        jdbcTemplate.query(
            """
            SELECT index_code, trade_date, close_price, change_rate
            FROM market_index_price
            WHERE index_code = ?
            ORDER BY trade_date DESC
            LIMIT 2
            """.trimIndent(),
            { resultSet, _ -> resultSet.toMarketIndexPrice() },
            indexCode.name,
        )

    private fun ResultSet.toMarketIndexPrice(): MarketIndexPrice =
        MarketIndexPrice(
            indexCode = MarketIndexCode.valueOf(getString("index_code")),
            tradeDate = getDate("trade_date").toLocalDate(),
            closePrice = getBigDecimal("close_price"),
            storedChangeRate = getBigDecimal("change_rate"),
        )
}
