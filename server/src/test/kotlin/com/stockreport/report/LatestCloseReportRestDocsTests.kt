package com.stockreport.report

import java.math.BigDecimal
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Primary
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.restdocs.RestDocumentationContextProvider
import org.springframework.restdocs.RestDocumentationExtension
import org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.document
import org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.documentationConfiguration
import org.springframework.restdocs.payload.FieldDescriptor
import org.springframework.restdocs.payload.JsonFieldType
import org.springframework.restdocs.payload.PayloadDocumentation.fieldWithPath
import org.springframework.restdocs.payload.PayloadDocumentation.responseFields
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.content
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.test.web.servlet.setup.MockMvcBuilders
import org.springframework.web.context.WebApplicationContext
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
@ExtendWith(RestDocumentationExtension::class)
class LatestCloseReportRestDocsTests {

    @Autowired
    private lateinit var webApplicationContext: WebApplicationContext

    private lateinit var mockMvc: MockMvc

    @Autowired
    private lateinit var jdbcTemplate: JdbcTemplate

    companion object {
        private const val TODAY = "2026-07-09"
        private const val BEFORE_SERVICE_START_DATE = "2026-06-30"

        @Container
        @ServiceConnection
        @JvmStatic
        val postgres: PostgreSQLContainer<*> = PostgreSQLContainer("postgres:16-alpine")
    }

    @BeforeEach
    fun resetDatabase(restDocumentation: RestDocumentationContextProvider) {
        mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext)
            .apply<org.springframework.test.web.servlet.setup.DefaultMockMvcBuilder>(
                documentationConfiguration(restDocumentation),
            )
            .build()
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
    fun `PUBLISHED 응답 REST Docs 스니펫을 생성한다`() {
        val revisionId = insertReportRevision(reportDate = TODAY)
        insertMarketIndex("KOSPI", TODAY, "2700.5000")
        insertMarketIndex("KOSDAQ", TODAY, "920.1250")
        insertAiSummary(
            reportDate = TODAY,
            revisionId = revisionId,
            status = "COMPLETED",
            summaryText = "시장 요약 본문",
        )

        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/latest-close/published",
                    responseFields(
                        fieldWithPath("status").type(JsonFieldType.STRING)
                            .description(
                                "API 표시 상태이다. PUBLISHED는 당일 활성 리비전 공개 완료, DELAYED는 당일 생성 지연과 직전 활성 리포트 반환 가능, " +
                                    "PREPARING은 당일 배치 실행 또는 재시도 중과 직전 활성 리포트 반환 가능, MARKET_CLOSED는 당일 휴장과 직전 활성 리포트 반환 가능, " +
                                    "NOT_PUBLISHED는 당일 리포트 공개 전 또는 배치 미실행과 직전 활성 리포트 반환 가능, EMPTY는 활성 리포트 없음이다.",
                            ),
                        fieldWithPath("asOfDate").type(JsonFieldType.STRING)
                            .description("서버가 조회 기준으로 사용한 Asia/Seoul 날짜이다."),
                        fieldWithPath("report").type(JsonFieldType.OBJECT)
                            .description("선택된 최신 활성 리비전 또는 정책상 fallback 리포트이다."),
                        fieldWithPath("report.reportDate").type(JsonFieldType.STRING)
                            .description("리포트 기준 거래일이다."),
                        fieldWithPath("report.revisionNo").type(JsonFieldType.NUMBER)
                            .description("거래일 내 리포트 리비전 번호이다."),
                        fieldWithPath("report.revisionType").type(JsonFieldType.STRING)
                            .description("리비전 유형이다."),
                        fieldWithPath("report.calculationVersion").type(JsonFieldType.STRING)
                            .description("리포트가 참조하는 계산 버전이다."),
                        fieldWithPath("report.publishedAt").type(JsonFieldType.STRING)
                            .description("리포트 공개 시각이다."),
                        fieldWithPath("report.analysisUniverse").type(JsonFieldType.OBJECT)
                            .description("분석 범위 정보이다."),
                        fieldWithPath("report.analysisUniverse.market").type(JsonFieldType.STRING)
                            .description("분석 대상 시장이다."),
                        fieldWithPath("report.analysisUniverse.selectionRule").type(JsonFieldType.STRING)
                            .description("분석 종목 선정 규칙이다."),
                        fieldWithPath("report.analysisUniverse.targetStockCount").type(JsonFieldType.NUMBER)
                            .description("분석 대상 종목 수이다."),
                        fieldWithPath("report.marketIndices").type(JsonFieldType.ARRAY)
                            .description("KOSPI, KOSDAQ 지수 요약 목록이다."),
                        fieldWithPath("report.marketIndices[].indexCode").type(JsonFieldType.STRING)
                            .description("지수 코드이다."),
                        fieldWithPath("report.marketIndices[].tradeDate").type(JsonFieldType.STRING)
                            .description("지수 거래일이다."),
                        fieldWithPath("report.marketIndices[].openPrice").type(JsonFieldType.NUMBER)
                            .description("시가이다."),
                        fieldWithPath("report.marketIndices[].highPrice").type(JsonFieldType.NUMBER)
                            .description("고가이다."),
                        fieldWithPath("report.marketIndices[].lowPrice").type(JsonFieldType.NUMBER)
                            .description("저가이다."),
                        fieldWithPath("report.marketIndices[].closePrice").type(JsonFieldType.NUMBER)
                            .description("종가이다."),
                        fieldWithPath("report.marketIndices[].volume").type(JsonFieldType.NUMBER)
                            .description("거래량이다."),
                        fieldWithPath("report.marketIndices[].changeRate").type(JsonFieldType.NUMBER)
                            .description("등락률이다."),
                        fieldWithPath("report.scannerStats").type(JsonFieldType.OBJECT)
                            .description("분석 종목 기준 스캐너 통계이다."),
                        fieldWithPath("report.scannerStats.targetStockCount").type(JsonFieldType.NUMBER)
                            .description("분석 대상 종목 수이다."),
                        fieldWithPath("report.scannerStats.completedStockCount").type(JsonFieldType.NUMBER)
                            .description("판정 완료 종목 수이다."),
                        fieldWithPath("report.scannerStats.failedStockCount").type(JsonFieldType.NUMBER)
                            .description("분석 실패 종목 수이다."),
                        fieldWithPath("report.scannerStats.insufficientStockCount").type(JsonFieldType.NUMBER)
                            .description("분석 데이터 부족 종목 수이다."),
                        fieldWithPath("report.scannerStats.noTradingStockCount").type(JsonFieldType.NUMBER)
                            .description("당일 거래 없음 종목 수이다."),
                        fieldWithPath("report.scannerStats.goldenCrossStockCount").type(JsonFieldType.NUMBER)
                            .description("골든크로스 신호 발생 종목 수이다."),
                        fieldWithPath("report.aiSummary").type(JsonFieldType.OBJECT)
                            .description("시장 AI 요약 상태와 본문이다."),
                        fieldWithPath("report.aiSummary.status").type(JsonFieldType.STRING)
                            .description("시장 AI 요약 상태이다."),
                        fieldWithPath("report.aiSummary.summaryText").type(JsonFieldType.STRING)
                            .description("시장 AI 요약 본문이다. 요약이 아직 없거나 PENDING 상태이면 null일 수 있다."),
                    ),
                ),
            )
    }

    @Test
    fun `EMPTY 응답 REST Docs 스니펫을 생성한다`() {
        mockMvc.perform(get("/api/reports/latest-close"))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/latest-close/empty",
                    responseFields(
                        fieldWithPath("status").type(JsonFieldType.STRING)
                            .description(
                                "API 표시 상태이다. PUBLISHED는 당일 활성 리비전 공개 완료, DELAYED는 당일 생성 지연과 직전 활성 리포트 반환 가능, " +
                                    "PREPARING은 당일 배치 실행 또는 재시도 중과 직전 활성 리포트 반환 가능, MARKET_CLOSED는 당일 휴장과 직전 활성 리포트 반환 가능, " +
                                    "NOT_PUBLISHED는 당일 리포트 공개 전 또는 배치 미실행과 직전 활성 리포트 반환 가능, EMPTY는 활성 리포트 없음이다.",
                            ),
                        fieldWithPath("asOfDate").type(JsonFieldType.STRING)
                            .description("서버가 조회 기준으로 사용한 Asia/Seoul 날짜이다."),
                        fieldWithPath("report").type(JsonFieldType.NULL)
                            .description("활성 리포트가 전혀 없을 때 null이다."),
                    ),
                ),
            )
    }

    @Test
    fun `과거 조회 PUBLISHED 응답 REST Docs 스니펫을 생성한다`() {
        val revisionId = insertReportRevision(reportDate = TODAY)
        insertMarketIndex("KOSPI", TODAY, "2700.5000")
        insertMarketIndex("KOSDAQ", TODAY, "920.1250")
        insertAiSummary(
            reportDate = TODAY,
            revisionId = revisionId,
            status = "COMPLETED",
            summaryText = "시장 요약 본문",
        )

        mockMvc.perform(get("/api/reports/close").param("tradeDate", TODAY))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/close/published",
                    responseFields(*historicalPublishedResponseFields()),
                ),
            )
    }

    @Test
    fun `과거 조회 MARKET_CLOSED 응답 REST Docs 스니펫을 생성한다`() {
        insertBatchJobRun(reportDate = TODAY, status = "SKIPPED_MARKET_CLOSED")

        mockMvc.perform(get("/api/reports/close").param("tradeDate", TODAY))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/close/market-closed",
                    responseFields(*historicalNoReportResponseFields("휴장일로 처리되어 리포트가 없는 상태이다.")),
                ),
            )
    }

    @Test
    fun `과거 조회 BEFORE_SERVICE_START 응답 REST Docs 스니펫을 생성한다`() {
        mockMvc.perform(get("/api/reports/close").param("tradeDate", BEFORE_SERVICE_START_DATE))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/close/before-service-start",
                    responseFields(*historicalNoReportResponseFields("서비스 운영 시작일 이전이라 리포트를 반환하지 않는 상태이다.")),
                ),
            )
    }

    @Test
    fun `과거 조회 NOT_PUBLISHED 응답 REST Docs 스니펫을 생성한다`() {
        mockMvc.perform(get("/api/reports/close").param("tradeDate", TODAY))
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "reports/close/not-published",
                    responseFields(*historicalNoReportResponseFields("서비스 시작일 이후이지만 사용자에게 제공할 활성 리포트가 없는 상태이다.")),
                ),
            )
    }

    private fun historicalPublishedResponseFields(): Array<FieldDescriptor> =
        arrayOf(
            *historicalBaseResponseFields(),
            fieldWithPath("report").type(JsonFieldType.OBJECT)
                .description("요청 거래일의 활성 리비전 기준 장 마감 리포트이다."),
            fieldWithPath("report.reportDate").type(JsonFieldType.STRING)
                .description("리포트 기준 거래일이다."),
            fieldWithPath("report.revisionNo").type(JsonFieldType.NUMBER)
                .description("거래일 내 리포트 리비전 번호이다."),
            fieldWithPath("report.revisionType").type(JsonFieldType.STRING)
                .description("리비전 유형이다."),
            fieldWithPath("report.calculationVersion").type(JsonFieldType.STRING)
                .description("리포트가 참조하는 계산 버전이다."),
            fieldWithPath("report.publishedAt").type(JsonFieldType.STRING)
                .description("리포트 공개 시각이다."),
            fieldWithPath("report.analysisUniverse").type(JsonFieldType.OBJECT)
                .description("분석 범위 정보이다."),
            fieldWithPath("report.analysisUniverse.market").type(JsonFieldType.STRING)
                .description("분석 대상 시장이다."),
            fieldWithPath("report.analysisUniverse.selectionRule").type(JsonFieldType.STRING)
                .description("분석 종목 선정 규칙이다."),
            fieldWithPath("report.analysisUniverse.targetStockCount").type(JsonFieldType.NUMBER)
                .description("분석 대상 종목 수이다."),
            fieldWithPath("report.marketIndices").type(JsonFieldType.ARRAY)
                .description("KOSPI, KOSDAQ 지수 요약 목록이다."),
            fieldWithPath("report.marketIndices[].indexCode").type(JsonFieldType.STRING)
                .description("지수 코드이다."),
            fieldWithPath("report.marketIndices[].tradeDate").type(JsonFieldType.STRING)
                .description("지수 거래일이다."),
            fieldWithPath("report.marketIndices[].openPrice").type(JsonFieldType.NUMBER)
                .description("시가이다."),
            fieldWithPath("report.marketIndices[].highPrice").type(JsonFieldType.NUMBER)
                .description("고가이다."),
            fieldWithPath("report.marketIndices[].lowPrice").type(JsonFieldType.NUMBER)
                .description("저가이다."),
            fieldWithPath("report.marketIndices[].closePrice").type(JsonFieldType.NUMBER)
                .description("종가이다."),
            fieldWithPath("report.marketIndices[].volume").type(JsonFieldType.NUMBER)
                .description("거래량이다."),
            fieldWithPath("report.marketIndices[].changeRate").type(JsonFieldType.NUMBER)
                .description("등락률이다."),
            fieldWithPath("report.scannerStats").type(JsonFieldType.OBJECT)
                .description("분석 종목 기준 스캐너 통계이다."),
            fieldWithPath("report.scannerStats.targetStockCount").type(JsonFieldType.NUMBER)
                .description("분석 대상 종목 수이다."),
            fieldWithPath("report.scannerStats.completedStockCount").type(JsonFieldType.NUMBER)
                .description("판정 완료 종목 수이다."),
            fieldWithPath("report.scannerStats.failedStockCount").type(JsonFieldType.NUMBER)
                .description("분석 실패 종목 수이다."),
            fieldWithPath("report.scannerStats.insufficientStockCount").type(JsonFieldType.NUMBER)
                .description("분석 데이터 부족 종목 수이다."),
            fieldWithPath("report.scannerStats.noTradingStockCount").type(JsonFieldType.NUMBER)
                .description("당일 거래 없음 종목 수이다."),
            fieldWithPath("report.scannerStats.goldenCrossStockCount").type(JsonFieldType.NUMBER)
                .description("골든크로스 신호 발생 종목 수이다."),
            fieldWithPath("report.aiSummary").type(JsonFieldType.OBJECT)
                .description("시장 AI 요약 상태와 본문이다."),
            fieldWithPath("report.aiSummary.status").type(JsonFieldType.STRING)
                .description("시장 AI 요약 상태이다."),
            fieldWithPath("report.aiSummary.summaryText").type(JsonFieldType.VARIES)
                .description("시장 AI 요약 본문이다. 요약이 아직 없거나 PENDING 상태이면 null일 수 있다."),
        )

    private fun historicalNoReportResponseFields(statusDescription: String): Array<FieldDescriptor> =
        arrayOf(
            *historicalBaseResponseFields(statusDescription),
            fieldWithPath("report").type(JsonFieldType.NULL)
                .description("요청 거래일에 사용자에게 제공할 장 마감 리포트가 없을 때 null이다."),
        )

    private fun historicalBaseResponseFields(
        statusDescription: String = "과거 장 마감 리포트 조회 상태이다. PUBLISHED, MARKET_CLOSED, BEFORE_SERVICE_START, NOT_PUBLISHED 중 하나이다.",
    ): Array<FieldDescriptor> =
        arrayOf(
            fieldWithPath("status").type(JsonFieldType.STRING)
                .description(statusDescription),
            fieldWithPath("tradeDate").type(JsonFieldType.STRING)
                .description("요청한 거래일 후보 날짜이다."),
            fieldWithPath("serviceStartDate").type(JsonFieldType.STRING)
                .description("장 마감 리포트 조회 가능 시작일이다."),
        )

    private fun insertReportRevision(reportDate: String): Long =
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
            values (?::date, 1, 'FINAL', true, 'close-v1', 200, 190, 3, 5, 2, '2026-07-09 19:15:00+09'::timestamptz)
            returning id
            """.trimIndent(),
            Long::class.java,
            reportDate,
        ) ?: error("report_revision insert failed")

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
