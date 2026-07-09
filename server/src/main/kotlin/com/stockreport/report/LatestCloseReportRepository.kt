package com.stockreport.report

import java.sql.ResultSet
import java.time.LocalDate
import java.time.OffsetDateTime
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate
import org.springframework.stereotype.Repository

@Repository
class LatestCloseReportRepository(
    private val jdbcTemplate: NamedParameterJdbcTemplate,
) {

    fun findActiveRevisionByReportDate(reportDate: LocalDate): ReportRevisionRow? =
        jdbcTemplate.query(
            """
            select
                id,
                report_date,
                revision_no,
                revision_type,
                calculation_version,
                target_stock_count,
                completed_stock_count,
                failed_stock_count,
                insufficient_stock_count,
                no_trading_stock_count,
                published_at
            from report_revision
            where report_date = :reportDate
              and is_active = true
            """.trimIndent(),
            mapOf("reportDate" to reportDate),
        ) { rs, _ -> rs.toReportRevisionRow() }.singleOrNull()

    fun findLatestActiveRevision(): ReportRevisionRow? =
        jdbcTemplate.query(
            """
            select
                id,
                report_date,
                revision_no,
                revision_type,
                calculation_version,
                target_stock_count,
                completed_stock_count,
                failed_stock_count,
                insufficient_stock_count,
                no_trading_stock_count,
                published_at
            from report_revision
            where is_active = true
            order by report_date desc, revision_no desc
            limit 1
            """.trimIndent(),
        ) { rs, _ -> rs.toReportRevisionRow() }.singleOrNull()

    fun findBatchStatusByReportDate(reportDate: LocalDate): String? =
        jdbcTemplate.query(
            """
            select status
            from batch_job_run
            where report_date = :reportDate
            """.trimIndent(),
            mapOf("reportDate" to reportDate),
        ) { rs, _ -> rs.getString("status") }.singleOrNull()

    fun findMarketIndices(reportDate: LocalDate): List<MarketIndexRow> =
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
            where trade_date = :reportDate
              and index_code in ('KOSPI', 'KOSDAQ')
            order by case index_code when 'KOSPI' then 1 when 'KOSDAQ' then 2 else 3 end
            """.trimIndent(),
            mapOf("reportDate" to reportDate),
        ) { rs, _ ->
            MarketIndexRow(
                indexCode = rs.getString("index_code"),
                tradeDate = rs.getObject("trade_date", LocalDate::class.java),
                openPrice = rs.getBigDecimal("open_price"),
                highPrice = rs.getBigDecimal("high_price"),
                lowPrice = rs.getBigDecimal("low_price"),
                closePrice = rs.getBigDecimal("close_price"),
                volume = rs.getLongOrNull("volume"),
                changeRate = rs.getBigDecimal("change_rate"),
            )
        }

    fun countGoldenCrossStocks(reportRevisionId: Long, calculationVersion: String): Int =
        jdbcTemplate.queryForObject(
            """
            select count(distinct sa.stock_id)
            from stock_analysis sa
            join signal_event se on se.id = sa.signal_event_id
            where sa.report_revision_id = :reportRevisionId
              and se.signal_type = 'STOCH_MACD_GOLDEN_CROSS'
              and se.calculation_version = :calculationVersion
            """.trimIndent(),
            mapOf(
                "reportRevisionId" to reportRevisionId,
                "calculationVersion" to calculationVersion,
            ),
            Int::class.java,
        ) ?: 0

    fun findAiSummary(reportDate: LocalDate, reportRevisionId: Long): AiSummaryRow? =
        jdbcTemplate.query(
            """
            select status, summary_text
            from market_ai_summary
            where report_date = :reportDate
              and report_revision_id = :reportRevisionId
            """.trimIndent(),
            MapSqlParameterSource()
                .addValue("reportDate", reportDate)
                .addValue("reportRevisionId", reportRevisionId),
        ) { rs, _ ->
            AiSummaryRow(
                status = rs.getString("status"),
                summaryText = rs.getString("summary_text"),
            )
        }.singleOrNull()

    private fun ResultSet.toReportRevisionRow(): ReportRevisionRow =
        ReportRevisionRow(
            id = getLong("id"),
            reportDate = getObject("report_date", LocalDate::class.java),
            revisionNo = getInt("revision_no"),
            revisionType = getString("revision_type"),
            calculationVersion = getString("calculation_version"),
            targetStockCount = getIntOrNull("target_stock_count"),
            completedStockCount = getIntOrNull("completed_stock_count"),
            failedStockCount = getIntOrNull("failed_stock_count"),
            insufficientStockCount = getIntOrNull("insufficient_stock_count"),
            noTradingStockCount = getIntOrNull("no_trading_stock_count"),
            publishedAt = getObject("published_at", OffsetDateTime::class.java),
        )

    private fun ResultSet.getIntOrNull(columnLabel: String): Int? {
        val value = getInt(columnLabel)
        return if (wasNull()) null else value
    }

    private fun ResultSet.getLongOrNull(columnLabel: String): Long? {
        val value = getLong(columnLabel)
        return if (wasNull()) null else value
    }
}

data class ReportRevisionRow(
    val id: Long,
    val reportDate: LocalDate,
    val revisionNo: Int,
    val revisionType: String,
    val calculationVersion: String,
    val targetStockCount: Int?,
    val completedStockCount: Int?,
    val failedStockCount: Int?,
    val insufficientStockCount: Int?,
    val noTradingStockCount: Int?,
    val publishedAt: OffsetDateTime?,
)

data class MarketIndexRow(
    val indexCode: String,
    val tradeDate: LocalDate,
    val openPrice: java.math.BigDecimal?,
    val highPrice: java.math.BigDecimal?,
    val lowPrice: java.math.BigDecimal?,
    val closePrice: java.math.BigDecimal?,
    val volume: Long?,
    val changeRate: java.math.BigDecimal?,
)

data class AiSummaryRow(
    val status: String,
    val summaryText: String?,
)
