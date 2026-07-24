package com.stockreport.marketindex.presentation

import com.stockreport.marketindex.application.MarketIndexService
import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexDailyPrice
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest
import org.springframework.boot.test.context.TestConfiguration
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Import
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get
import java.math.BigDecimal
import java.time.LocalDate

@DisplayName("시장 지수 최신 수치 Controller 테스트")
@WebMvcTest(MarketIndexController::class)
@Import(MarketIndexControllerTest.TestConfig::class)
class MarketIndexControllerTest(
    @Autowired
    private val mockMvc: MockMvc,
) {

    @Test
    @DisplayName("GET /api/market-indexes는 KOSPI와 KOSDAQ 항목을 포함한 200 응답을 반환한다")
    fun 시장_지수_최신_수치_조회_성공() {
        mockMvc.get("/api/market-indexes")
            .andExpect {
                status { isOk() }
                jsonPath("$.items[0].indexCode") { value("KOSPI") }
                jsonPath("$.items[0].status") { value("EMPTY") }
                jsonPath("$.items[1].indexCode") { value("KOSDAQ") }
                jsonPath("$.items[1].status") { value("EMPTY") }
            }
    }

    @Test
    @DisplayName("GET /api/market-indexes/{indexCode}/prices는 기간별 일봉 목록을 반환한다")
    fun 시장_지수_기간별_일봉_조회_성공() {
        mockMvc.get("/api/market-indexes/KOSPI/prices") {
            param("period", "3M")
        }.andExpect {
            status { isOk() }
            jsonPath("$.indexCode") { value("KOSPI") }
            jsonPath("$.period") { value("3M") }
            jsonPath("$.startDate") { value("2026-04-22") }
            jsonPath("$.endDate") { value("2026-07-22") }
            jsonPath("$.items[0].tradeDate") { value("2026-04-22") }
            jsonPath("$.items[0].openPrice") { value(2680.0) }
            jsonPath("$.items[0].highPrice") { value(2700.0) }
            jsonPath("$.items[0].lowPrice") { value(2670.0) }
            jsonPath("$.items[0].closePrice") { value(2690.0) }
            jsonPath("$.items[0].volume") { value(500000000) }
            jsonPath("$.items[0].changeRatePercent") { value(0.12) }
            jsonPath("$.items[1].tradeDate") { value("2026-07-22") }
            jsonPath("$.items[1].changeRatePercent") { value(1.23) }
        }
    }

    @Test
    @DisplayName("유효한 지수에 저장된 데이터가 없으면 기간별 일봉 조회는 빈 목록을 반환한다")
    fun 시장_지수_기간별_일봉_빈_목록_반환() {
        mockMvc.get("/api/market-indexes/KOSDAQ/prices") {
            param("period", "3M")
        }.andExpect {
            status { isOk() }
            jsonPath("$.indexCode") { value("KOSDAQ") }
            jsonPath("$.period") { value("3M") }
            jsonPath("$.startDate") { value(null) }
            jsonPath("$.endDate") { value(null) }
            jsonPath("$.items") { isEmpty() }
        }
    }

    @Test
    @DisplayName("존재하지 않는 지수 코드의 기간별 일봉 조회는 404 응답을 반환한다")
    fun 시장_지수_기간별_일봉_존재하지_않는_지수_404() {
        mockMvc.get("/api/market-indexes/INVALID/prices") {
            param("period", "3M")
        }.andExpect {
            status { isNotFound() }
        }
    }

    @Test
    @DisplayName("지원하지 않는 기간의 기간별 일봉 조회는 400 응답을 반환한다")
    fun 시장_지수_기간별_일봉_지원하지_않는_기간_400() {
        mockMvc.get("/api/market-indexes/KOSPI/prices") {
            param("period", "2Y")
        }.andExpect {
            status { isBadRequest() }
        }
    }

    @Test
    @DisplayName("기간이 누락된 기간별 일봉 조회는 400 응답을 반환한다")
    fun 시장_지수_기간별_일봉_기간_누락_400() {
        mockMvc.get("/api/market-indexes/KOSPI/prices")
            .andExpect {
                status { isBadRequest() }
            }
    }

    @TestConfiguration
    class TestConfig {
        @Bean
        fun marketIndexService(): MarketIndexService =
            MarketIndexService(FakeMarketIndexPriceRepository())
    }

    private class FakeMarketIndexPriceRepository : MarketIndexPriceRepository {
        override fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice> = emptyList()

        override fun findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate? =
            when (indexCode) {
                MarketIndexCode.KOSPI -> LocalDate.parse("2026-07-22")
                MarketIndexCode.KOSDAQ -> null
            }

        override fun findDailyPricesByIndexCodeAndTradeDateBetween(
            indexCode: MarketIndexCode,
            startDate: LocalDate,
            endDate: LocalDate,
        ): List<MarketIndexDailyPrice> =
            when (indexCode) {
                MarketIndexCode.KOSPI -> listOf(
                    MarketIndexDailyPrice(
                        indexCode = MarketIndexCode.KOSPI,
                        tradeDate = LocalDate.parse("2026-04-22"),
                        openPrice = BigDecimal("2680.0000"),
                        highPrice = BigDecimal("2700.0000"),
                        lowPrice = BigDecimal("2670.0000"),
                        closePrice = BigDecimal("2690.0000"),
                        volume = 500_000_000L,
                        storedChangeRate = BigDecimal("0.0012"),
                    ),
                    MarketIndexDailyPrice(
                        indexCode = MarketIndexCode.KOSPI,
                        tradeDate = LocalDate.parse("2026-07-22"),
                        openPrice = BigDecimal("2780.0000"),
                        highPrice = BigDecimal("2800.0000"),
                        lowPrice = BigDecimal("2770.0000"),
                        closePrice = BigDecimal("2790.0000"),
                        volume = 600_000_000L,
                        storedChangeRate = BigDecimal("0.0123"),
                    ),
                )
                MarketIndexCode.KOSDAQ -> emptyList()
            }
    }
}
