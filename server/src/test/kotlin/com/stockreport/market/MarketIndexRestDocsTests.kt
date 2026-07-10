package com.stockreport.market

import java.math.BigDecimal
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.extension.ExtendWith
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.http.MediaType
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.restdocs.RestDocumentationContextProvider
import org.springframework.restdocs.RestDocumentationExtension
import org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.document
import org.springframework.restdocs.mockmvc.MockMvcRestDocumentation.documentationConfiguration
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
class MarketIndexRestDocsTests {

    @Autowired
    private lateinit var webApplicationContext: WebApplicationContext

    private lateinit var mockMvc: MockMvc

    @Autowired
    private lateinit var jdbcTemplate: JdbcTemplate

    companion object {
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
    fun `지수 시계열 정상 응답 REST Docs 스니펫을 생성한다`() {
        insertMarketIndexWithNullValues("KOSPI", "2026-07-08")
        insertMarketIndex("KOSDAQ", "2026-07-08", "920.1250")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-08")
                .param("endDate", "2026-07-09"),
        )
            .andExpect(status().isOk)
            .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
            .andDo(
                document(
                    "market-indices/timeseries/success",
                    responseFields(
                        fieldWithPath("startDate").type(JsonFieldType.STRING)
                            .description("요청한 조회 시작 날짜이다."),
                        fieldWithPath("endDate").type(JsonFieldType.STRING)
                            .description("요청한 조회 종료 날짜이다."),
                        fieldWithPath("indices").type(JsonFieldType.ARRAY)
                            .description("KOSPI, KOSDAQ 순서로 고정된 시장 지수 시계열 목록이다."),
                        fieldWithPath("indices[].indexCode").type(JsonFieldType.STRING)
                            .description("지수 코드이다. KOSPI 또는 KOSDAQ이다."),
                        fieldWithPath("indices[].prices").type(JsonFieldType.ARRAY)
                            .description("요청 기간에 저장된 지수 일봉 목록이다. 휴장일이나 누락 거래일은 보간하지 않는다."),
                        fieldWithPath("indices[].prices[].tradeDate").type(JsonFieldType.STRING)
                            .description("지수 거래일이다."),
                        fieldWithPath("indices[].prices[].openPrice").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 시가이다. DB 값이 null이면 null이다."),
                        fieldWithPath("indices[].prices[].highPrice").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 고가이다. DB 값이 null이면 null이다."),
                        fieldWithPath("indices[].prices[].lowPrice").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 저가이다. DB 값이 null이면 null이다."),
                        fieldWithPath("indices[].prices[].closePrice").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 종가이다. DB 값이 null이면 null이다."),
                        fieldWithPath("indices[].prices[].volume").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 거래량이다. DB 값이 null이면 null이다."),
                        fieldWithPath("indices[].prices[].changeRate").type(JsonFieldType.VARIES)
                            .optional()
                            .description("저장된 등락률이다. DB 값이 null이면 null이다."),
                    ),
                ),
            )
    }

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

    private fun insertMarketIndexWithNullValues(indexCode: String, tradeDate: String) {
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
            values (?, ?::date, null, null, null, null, null, null)
            """.trimIndent(),
            indexCode,
            tradeDate,
        )
    }
}
