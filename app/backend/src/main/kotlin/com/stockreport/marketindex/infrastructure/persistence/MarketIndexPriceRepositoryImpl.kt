package com.stockreport.marketindex.infrastructure.persistence

import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexDailyPrice
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Repository
import java.sql.ResultSet
import java.time.LocalDate

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

    override fun findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate? =
        jdbcTemplate.queryForObject(
            """
            SELECT MAX(trade_date) AS latest_trade_date
            FROM market_index_price
            WHERE index_code = ?
            """.trimIndent(),
            { resultSet, _ -> resultSet.getDate("latest_trade_date")?.toLocalDate() },
            indexCode.name,
        )

    override fun findDailyPricesByIndexCodeAndTradeDateBetween(
        indexCode: MarketIndexCode,
        startDate: LocalDate,
        endDate: LocalDate,
    ): List<MarketIndexDailyPrice> =
        jdbcTemplate.query(
            """
            SELECT index_code, trade_date, open_price, high_price, low_price, close_price, volume, change_rate
            FROM market_index_price
            WHERE index_code = ?
              AND trade_date >= ?
              AND trade_date <= ?
            ORDER BY trade_date ASC
            """.trimIndent(),
            { resultSet, _ -> resultSet.toMarketIndexDailyPrice() },
            indexCode.name,
            startDate,
            endDate,
        )

    private fun ResultSet.toMarketIndexPrice(): MarketIndexPrice =
        MarketIndexPrice(
            indexCode = MarketIndexCode.valueOf(getString("index_code")),
            tradeDate = getDate("trade_date").toLocalDate(),
            closePrice = getBigDecimal("close_price"),
            storedChangeRate = getBigDecimal("change_rate"),
        )

    private fun ResultSet.toMarketIndexDailyPrice(): MarketIndexDailyPrice =
        MarketIndexDailyPrice(
            indexCode = MarketIndexCode.valueOf(getString("index_code")),
            tradeDate = getDate("trade_date").toLocalDate(),
            openPrice = getBigDecimal("open_price"),
            highPrice = getBigDecimal("high_price"),
            lowPrice = getBigDecimal("low_price"),
            closePrice = getBigDecimal("close_price"),
            volume = getLong("volume"),
            storedChangeRate = getBigDecimal("change_rate"),
        )
}
