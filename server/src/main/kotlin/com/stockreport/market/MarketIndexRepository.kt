package com.stockreport.market

import java.math.BigDecimal
import java.sql.ResultSet
import java.time.LocalDate
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.stereotype.Repository

@Repository
class MarketIndexRepository(
    private val jdbcTemplate: NamedParameterJdbcTemplate,
) {

    fun findPrices(
        startDate: LocalDate,
        endDate: LocalDate,
        indexCodes: List<String>,
    ): List<MarketIndexPriceRow> =
        jdbcTemplate.query(
            """
            select
                index_code,
                trade_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                change_rate
            from market_index_price
            where index_code in (:indexCodes)
              and trade_date between :startDate and :endDate
            order by
                case index_code when 'KOSPI' then 1 when 'KOSDAQ' then 2 else 3 end,
                trade_date asc
            """.trimIndent(),
            mapOf(
                "indexCodes" to indexCodes,
                "startDate" to startDate,
                "endDate" to endDate,
            ),
        ) { rs, _ -> rs.toMarketIndexPriceRow() }

    private fun ResultSet.toMarketIndexPriceRow(): MarketIndexPriceRow =
        MarketIndexPriceRow(
            indexCode = getString("index_code"),
            tradeDate = getObject("trade_date", LocalDate::class.java),
            openPrice = getBigDecimal("open_price"),
            highPrice = getBigDecimal("high_price"),
            lowPrice = getBigDecimal("low_price"),
            closePrice = getBigDecimal("close_price"),
            volume = getLongOrNull("volume"),
            changeRate = getBigDecimal("change_rate"),
        )

    private fun ResultSet.getLongOrNull(columnLabel: String): Long? {
        val value = getLong(columnLabel)
        return if (wasNull()) null else value
    }
}

data class MarketIndexPriceRow(
    val indexCode: String,
    val tradeDate: LocalDate,
    val openPrice: BigDecimal?,
    val highPrice: BigDecimal?,
    val lowPrice: BigDecimal?,
    val closePrice: BigDecimal?,
    val volume: Long?,
    val changeRate: BigDecimal?,
)
