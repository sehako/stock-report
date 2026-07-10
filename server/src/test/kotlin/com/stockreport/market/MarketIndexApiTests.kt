package com.stockreport.market

import java.math.BigDecimal
import org.hamcrest.Matchers.nullValue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.ValueSource
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath
import org.springframework.test.web.servlet.result.MockMvcResultMatchers.status
import org.springframework.test.web.servlet.setup.MockMvcBuilders
import org.springframework.web.context.WebApplicationContext
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class MarketIndexApiTests {

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
    fun `요청 기간의 KOSPI와 KOSDAQ 지수 일봉을 series로 반환한다`() {
        insertMarketIndex("KOSDAQ", "2026-07-08", "920.1250")
        insertMarketIndex("KOSPI", "2026-07-09", "2710.0000")
        insertMarketIndex("KOSPI", "2026-07-08", "2700.5000")
        insertMarketIndex("KOSDAQ", "2026-07-07", "910.0000")
        insertMarketIndex("KOSPI", "2026-07-07", "2690.0000")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-07")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.startDate").value("2026-07-07"))
            .andExpect(jsonPath("$.endDate").value("2026-07-08"))
            .andExpect(jsonPath("$.indices.length()").value(2))
            .andExpect(jsonPath("$.indices[0].indexCode").value("KOSPI"))
            .andExpect(jsonPath("$.indices[0].prices.length()").value(2))
            .andExpect(jsonPath("$.indices[0].prices[0].tradeDate").value("2026-07-07"))
            .andExpect(jsonPath("$.indices[0].prices[0].closePrice").value(2690.0000))
            .andExpect(jsonPath("$.indices[0].prices[1].tradeDate").value("2026-07-08"))
            .andExpect(jsonPath("$.indices[0].prices[1].closePrice").value(2700.5000))
            .andExpect(jsonPath("$.indices[1].indexCode").value("KOSDAQ"))
            .andExpect(jsonPath("$.indices[1].prices.length()").value(2))
            .andExpect(jsonPath("$.indices[1].prices[0].tradeDate").value("2026-07-07"))
            .andExpect(jsonPath("$.indices[1].prices[0].closePrice").value(910.0000))
            .andExpect(jsonPath("$.indices[1].prices[1].tradeDate").value("2026-07-08"))
            .andExpect(jsonPath("$.indices[1].prices[1].closePrice").value(920.1250))
    }

    @Test
    fun `한쪽 지수 데이터가 없으면 빈 prices 배열로 반환한다`() {
        insertMarketIndex("KOSPI", "2026-07-08", "2700.5000")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-08")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.indices[0].indexCode").value("KOSPI"))
            .andExpect(jsonPath("$.indices[0].prices.length()").value(1))
            .andExpect(jsonPath("$.indices[1].indexCode").value("KOSDAQ"))
            .andExpect(jsonPath("$.indices[1].prices.length()").value(0))
    }

    @Test
    fun `기간 내 데이터가 없으면 두 지수 모두 빈 prices 배열로 반환한다`() {
        insertMarketIndex("KOSPI", "2026-07-07", "2690.0000")
        insertMarketIndex("KOSDAQ", "2026-07-09", "920.1250")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-08")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.indices[0].indexCode").value("KOSPI"))
            .andExpect(jsonPath("$.indices[0].prices.length()").value(0))
            .andExpect(jsonPath("$.indices[1].indexCode").value("KOSDAQ"))
            .andExpect(jsonPath("$.indices[1].prices.length()").value(0))
    }

    @Test
    fun `요청 기간 내 일부 날짜가 누락되어도 저장된 일봉만 반환한다`() {
        insertMarketIndex("KOSPI", "2026-07-07", "2690.0000")
        insertMarketIndex("KOSPI", "2026-07-09", "2710.0000")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-07")
                .param("endDate", "2026-07-09"),
        )
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.indices[0].prices.length()").value(2))
            .andExpect(jsonPath("$.indices[0].prices[0].tradeDate").value("2026-07-07"))
            .andExpect(jsonPath("$.indices[0].prices[1].tradeDate").value("2026-07-09"))
    }

    @Test
    fun `저장된 지수 일봉의 null 값은 보정하지 않고 반환한다`() {
        insertMarketIndexWithNullValues("KOSPI", "2026-07-08")

        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-08")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isOk)
            .andExpect(jsonPath("$.indices[0].prices[0].openPrice").value(nullValue()))
            .andExpect(jsonPath("$.indices[0].prices[0].highPrice").value(nullValue()))
            .andExpect(jsonPath("$.indices[0].prices[0].lowPrice").value(nullValue()))
            .andExpect(jsonPath("$.indices[0].prices[0].closePrice").value(nullValue()))
            .andExpect(jsonPath("$.indices[0].prices[0].volume").value(nullValue()))
            .andExpect(jsonPath("$.indices[0].prices[0].changeRate").value(nullValue()))
    }

    @Test
    fun `startDate가 누락되면 HTTP 400을 반환한다`() {
        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `endDate가 누락되면 HTTP 400을 반환한다`() {
        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-08"),
        )
            .andExpect(status().isBadRequest)
    }

    @ParameterizedTest
    @ValueSource(strings = ["2026/07/08", "invalid"])
    fun `날짜 형식이 잘못되면 HTTP 400을 반환한다`(startDate: String) {
        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", startDate)
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isBadRequest)
    }

    @Test
    fun `startDate가 endDate보다 늦으면 HTTP 400을 반환한다`() {
        mockMvc.perform(
            get("/api/market-indices/timeseries")
                .param("startDate", "2026-07-09")
                .param("endDate", "2026-07-08"),
        )
            .andExpect(status().isBadRequest)
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
