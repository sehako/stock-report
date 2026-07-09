package com.stockreport.report

import java.math.BigDecimal
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import org.hamcrest.Matchers.nullValue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Primary
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.setup.MockMvcBuilders
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.web.context.WebApplicationContext
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class LatestCloseReportApiTests {

    @Autowired
    private lateinit var webApplicationContext: WebApplicationContext

    private lateinit var mockMvc: MockMvc

    @Autowired
    private lateinit var jdbcTemplate: JdbcTemplate

    companion object {
        private const val TODAY = "2026-07-09"
        private const val PREVIOUS_REPORT_DATE = "2026-07-08"

        @Container
        @ServiceConnection
        @JvmStatic
        val postgres: PostgreSQLContainer<*> = PostgreSQLContainer("postgres:16-alpine")
    }

    @BeforeEach
    fun resetDatabase() {
        mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext).build()
        jdbcTemplate.execute(
            """
            truncate table
                stock,
                report_revision,
                batch_job_run,
                market_index_price
            restart identity cascade
            """.trimIndent(),
        )
    }

    @Test
    fun `당일 활성 리비전이 있으면 PUBLISHED와 당일 리포트를 반환한다`() {
        insertReportRevision(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionNo = 1,
            revisionType = "FINAL",
            isActive = true,
            calculationVersion = "close-v0",
        )
        insertReportRevision(
            reportDate = TODAY,
            revisionNo = 2,
            revisionType = "FINAL",
            isActive = true,
            calculationVersion = "close-v1",
        )

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("PUBLISHED"))
            .andExpect(jsonPath("$.asOfDate").value(TODAY))
            .andExpect(jsonPath("$.report.reportDate").value(TODAY))
            .andExpect(jsonPath("$.report.revisionNo").value(2))
            .andExpect(jsonPath("$.report.revisionType").value("FINAL"))
            .andExpect(jsonPath("$.report.calculationVersion").value("close-v1"))
    }

    @Test
    fun `당일 DELAYED이고 당일 활성 리비전이 없으면 DELAYED와 직전 활성 리포트를 반환한다`() {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertBatchJobRun(reportDate = TODAY, status = "DELAYED")

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("DELAYED"))
            .andExpect(jsonPath("$.report.reportDate").value(PREVIOUS_REPORT_DATE))
    }

    @Test
    fun `당일 FAILED이고 당일 활성 리비전이 없으면 DELAYED와 직전 활성 리포트를 반환한다`() {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertBatchJobRun(reportDate = TODAY, status = "FAILED")

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("DELAYED"))
            .andExpect(jsonPath("$.report.reportDate").value(PREVIOUS_REPORT_DATE))
    }

    @ParameterizedTest
    @ValueSource(strings = ["RUNNING", "RETRYING"])
    fun `당일 RUNNING 또는 RETRYING이면 PREPARING과 직전 활성 리포트를 반환한다`(batchStatus: String) {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertBatchJobRun(reportDate = TODAY, status = batchStatus)

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("PREPARING"))
            .andExpect(jsonPath("$.report.reportDate").value(PREVIOUS_REPORT_DATE))
    }

    @Test
    fun `당일 SKIPPED_MARKET_CLOSED이면 MARKET_CLOSED와 직전 활성 리포트를 반환한다`() {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertBatchJobRun(reportDate = TODAY, status = "SKIPPED_MARKET_CLOSED")

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("MARKET_CLOSED"))
            .andExpect(jsonPath("$.report.reportDate").value(PREVIOUS_REPORT_DATE))
    }

    @Test
    fun `당일 배치 행이 없고 당일 활성 리비전이 없으면 NOT_PUBLISHED와 직전 활성 리포트를 반환한다`() {
        insertReportRevision(reportDate = "2026-07-05", calculationVersion = "old-version")
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("NOT_PUBLISHED"))
            .andExpect(jsonPath("$.report.reportDate").value(PREVIOUS_REPORT_DATE))
            .andExpect(jsonPath("$.report.calculationVersion").value("close-v1"))
    }

    @Test
    fun `활성 리비전이 전혀 없으면 EMPTY와 null report를 반환한다`() {
        insertBatchJobRun(reportDate = TODAY, status = "RUNNING")

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.status").value("EMPTY"))
            .andExpect(jsonPath("$.asOfDate").value(TODAY))
            .andExpect(jsonPath("$.report").value(nullValue()))
    }

    @Test
    fun `최신 활성 리비전의 calculationVersion이 응답에 포함된다`() {
        insertReportRevision(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionNo = 3,
            calculationVersion = "stoch-macd-v2",
        )

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.calculationVersion").value("stoch-macd-v2"))
    }

    @Test
    fun `KOSPI KOSDAQ 지수 요약이 선택 리비전의 reportDate 기준으로 반환된다`() {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertMarketIndex("KOSPI", PREVIOUS_REPORT_DATE, "2700.5000")
        insertMarketIndex("KOSDAQ", PREVIOUS_REPORT_DATE, "920.1250")
        insertMarketIndex("KOSPI", TODAY, "2800.0000")

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.marketIndices.length()").value(2))
            .andExpect(jsonPath("$.report.marketIndices[0].indexCode").value("KOSPI"))
            .andExpect(jsonPath("$.report.marketIndices[0].tradeDate").value(PREVIOUS_REPORT_DATE))
            .andExpect(jsonPath("$.report.marketIndices[0].closePrice").value(2700.5000))
            .andExpect(jsonPath("$.report.marketIndices[1].indexCode").value("KOSDAQ"))
            .andExpect(jsonPath("$.report.marketIndices[1].tradeDate").value(PREVIOUS_REPORT_DATE))
            .andExpect(jsonPath("$.report.marketIndices[1].closePrice").value(920.1250))
    }

    @Test
    fun `스캐너 통계가 리비전 커버리지 집계와 골든크로스 종목 수를 반환한다`() {
        val revisionId = insertReportRevision(
            reportDate = PREVIOUS_REPORT_DATE,
            targetStockCount = 200,
            completedStockCount = 190,
            failedStockCount = 3,
            insufficientStockCount = 5,
            noTradingStockCount = 2,
            calculationVersion = "close-v1",
        )
        val stockId = insertStock("005930", "Samsung Electronics")
        val otherStockId = insertStock("000660", "SK Hynix")
        val signalEventId = insertSignalEvent(stockId, PREVIOUS_REPORT_DATE, "close-v1")
        val mismatchedVersionSignalEventId = insertSignalEvent(otherStockId, PREVIOUS_REPORT_DATE, "close-v0")
        insertStockAnalysis(revisionId, stockId, signalEventId, "SIGNAL_FOUND", 1)
        insertStockAnalysis(revisionId, otherStockId, mismatchedVersionSignalEventId, "SIGNAL_FOUND", 2)

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.analysisUniverse.market").value("KRX"))
            .andExpect(jsonPath("$.report.analysisUniverse.targetStockCount").value(200))
            .andExpect(jsonPath("$.report.scannerStats.targetStockCount").value(200))
            .andExpect(jsonPath("$.report.scannerStats.completedStockCount").value(190))
            .andExpect(jsonPath("$.report.scannerStats.failedStockCount").value(3))
            .andExpect(jsonPath("$.report.scannerStats.insufficientStockCount").value(5))
            .andExpect(jsonPath("$.report.scannerStats.noTradingStockCount").value(2))
            .andExpect(jsonPath("$.report.scannerStats.goldenCrossStockCount").value(1))
    }

    @Test
    fun `AI 요약이 있으면 상태와 내용을 반환한다`() {
        val revisionId = insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)
        insertAiSummary(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionId = revisionId,
            status = "COMPLETED",
            summaryText = "시장 요약 본문",
        )

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.aiSummary.status").value("COMPLETED"))
            .andExpect(jsonPath("$.report.aiSummary.summaryText").value("시장 요약 본문"))
    }

    @Test
    fun `AI 요약이 없으면 PENDING과 null summaryText를 반환한다`() {
        insertReportRevision(reportDate = PREVIOUS_REPORT_DATE)

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.aiSummary.status").value("PENDING"))
            .andExpect(jsonPath("$.report.aiSummary.summaryText").value(nullValue()))
    }

    @Test
    fun `AI 요약이 같은 거래일의 비활성 리비전을 참조하면 PENDING을 반환한다`() {
        val inactiveRevisionId = insertReportRevision(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionNo = 1,
            isActive = false,
        )
        insertReportRevision(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionNo = 2,
            isActive = true,
        )
        insertAiSummary(
            reportDate = PREVIOUS_REPORT_DATE,
            revisionId = inactiveRevisionId,
            status = "COMPLETED",
            summaryText = "이전 리비전 요약",
        )

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.report.revisionNo").value(2))
            .andExpect(jsonPath("$.report.aiSummary.status").value("PENDING"))
            .andExpect(jsonPath("$.report.aiSummary.summaryText").value(nullValue()))
    }

    private fun insertReportRevision(
        reportDate: String,
        revisionNo: Int = 1,
        revisionType: String = "FINAL",
        isActive: Boolean = true,
        calculationVersion: String = "close-v1",
        targetStockCount: Int = 200,
        completedStockCount: Int = 190,
        failedStockCount: Int = 3,
        insufficientStockCount: Int = 5,
        noTradingStockCount: Int = 2,
    ): Long =
        jdbcTemplate.queryForObject(
            """
            insert into report_revision (
                report_date,
                revision_no,
                revision_type,
                is_active,
                calculation_version,
                target_stock_count,
                completed_stock_count,
                failed_stock_count,
                insufficient_stock_count,
                no_trading_stock_count,
                published_at
            )
            values (?::date, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-07-08 19:15:00+09'::timestamptz)
            returning id
            """.trimIndent(),
            Long::class.java,
            reportDate,
            revisionNo,
            revisionType,
            isActive,
            calculationVersion,
            targetStockCount,
            completedStockCount,
            failedStockCount,
            insufficientStockCount,
            noTradingStockCount,
        ) ?: error("report_revision insert failed")

    private fun insertBatchJobRun(reportDate: String, status: String): Long =
        jdbcTemplate.queryForObject(
            """
            insert into batch_job_run (report_date, status)
            values (?::date, ?)
            returning id
            """.trimIndent(),
            Long::class.java,
            reportDate,
            status,
        ) ?: error("batch_job_run insert failed")

    private fun insertMarketIndex(indexCode: String, tradeDate: String, closePrice: String) {
        jdbcTemplate.update(
            """
            insert into market_index_price (
                index_code,
                trade_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                change_rate
            )
            values (?, ?::date, 1.0000, 2.0000, 0.5000, ?, 1000000, 0.01230000)
            """.trimIndent(),
            indexCode,
            tradeDate,
            BigDecimal(closePrice),
        )
    }

    private fun insertStock(stockCode: String, stockName: String): Long =
        jdbcTemplate.queryForObject(
            """
            insert into stock (stock_code, stock_name, market, industry_name)
            values (?, ?, 'KOSPI', 'Electronics')
            returning id
            """.trimIndent(),
            Long::class.java,
            stockCode,
            stockName,
        ) ?: error("stock insert failed")

    private fun insertSignalEvent(stockId: Long, crossDate: String, calculationVersion: String): Long =
        jdbcTemplate.queryForObject(
            """
            insert into signal_event (
                stock_id,
                signal_type,
                cross_date,
                calculation_version
            )
            values (?, 'STOCH_MACD_GOLDEN_CROSS', ?::date, ?)
            returning id
            """.trimIndent(),
            Long::class.java,
            stockId,
            crossDate,
            calculationVersion,
        ) ?: error("signal_event insert failed")

    private fun insertStockAnalysis(
        revisionId: Long,
        stockId: Long,
        signalEventId: Long?,
        analysisStatus: String,
        selectionRank: Int,
    ) {
        jdbcTemplate.update(
            """
            insert into stock_analysis (
                report_revision_id,
                stock_id,
                signal_event_id,
                analysis_status,
                stock_name_snapshot,
                market_snapshot,
                selection_rank,
                selection_volume
            )
            values (?, ?, ?, ?, 'Stock', 'KOSPI', ?, 1000)
            """.trimIndent(),
            revisionId,
            stockId,
            signalEventId,
            analysisStatus,
            selectionRank,
        )
    }

    private fun insertAiSummary(
        reportDate: String,
        revisionId: Long,
        status: String,
        summaryText: String?,
    ) {
        jdbcTemplate.update(
            """
            insert into market_ai_summary (
                report_date,
                report_revision_id,
                status,
                summary_text,
                input_hash
            )
            values (?::date, ?, ?, ?, 'hash-1')
            """.trimIndent(),
            reportDate,
            revisionId,
            status,
            summaryText,
        )
    }

    @TestConfiguration
    class FixedClockConfig {

        @Bean
        @Primary
        fun fixedClock(): Clock =
            Clock.fixed(
                Instant.parse("2026-07-09T01:00:00Z"),
                ZoneId.of("Asia/Seoul"),
            )
    }
}
