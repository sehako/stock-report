package com.stockreport.marketindex.presentation

import com.stockreport.marketindex.application.MarketIndexService
import com.stockreport.marketindex.domain.MarketIndexCode
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

    @TestConfiguration
    class TestConfig {
        @Bean
        fun marketIndexService(): MarketIndexService =
            MarketIndexService(EmptyMarketIndexPriceRepository())
    }

    private class EmptyMarketIndexPriceRepository : MarketIndexPriceRepository {
        override fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice> = emptyList()
    }
}
