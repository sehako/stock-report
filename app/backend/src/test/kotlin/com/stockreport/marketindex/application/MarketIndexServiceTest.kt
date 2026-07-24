package com.stockreport.marketindex.application

import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexDailyPrice
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.springframework.http.HttpStatus
import org.springframework.web.server.ResponseStatusException
import java.math.BigDecimal
import java.time.LocalDate

@DisplayName("시장 지수 최신 수치 서비스 테스트")
class MarketIndexServiceTest {

    @Test
    @DisplayName("최신 두 거래일 데이터와 등락률이 있으면 AVAILABLE 상태와 계산된 수치를 반환한다")
    fun 최신_두_거래일_데이터_AVAILABLE_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                mapOf(
                    MarketIndexCode.KOSPI to listOf(
                        price(MarketIndexCode.KOSPI, "2026-07-16", "2705.4000", "0.0123"),
                        price(MarketIndexCode.KOSPI, "2026-07-15", "2700.0000", "-0.0020"),
                    ),
                    MarketIndexCode.KOSDAQ to listOf(
                        price(MarketIndexCode.KOSDAQ, "2026-07-16", "820.5000", "-0.0045"),
                        price(MarketIndexCode.KOSDAQ, "2026-07-15", "824.2000", "0.0010"),
                    ),
                ),
            ),
        )

        val response = service.getMarketIndexSummaries()

        assertEquals(2, response.items.size)
        response.items[0].also {
            assertEquals("KOSPI", it.indexCode)
            assertEquals("AVAILABLE", it.status)
            assertEquals(LocalDate.parse("2026-07-16"), it.tradeDate)
            assertEquals(BigDecimal("2705.4000"), it.closePrice)
            assertEquals(BigDecimal("5.4000"), it.changeValue)
            assertEquals(BigDecimal("1.2300"), it.changeRatePercent)
        }
        response.items[1].also {
            assertEquals("KOSDAQ", it.indexCode)
            assertEquals("AVAILABLE", it.status)
            assertEquals(LocalDate.parse("2026-07-16"), it.tradeDate)
            assertEquals(BigDecimal("820.5000"), it.closePrice)
            assertEquals(BigDecimal("-3.7000"), it.changeValue)
            assertEquals(BigDecimal("-0.4500"), it.changeRatePercent)
        }
    }

    @Test
    @DisplayName("최신 거래일 데이터만 있으면 PARTIAL 상태와 null 전일 대비 값을 반환한다")
    fun 최신_거래일만_있으면_PARTIAL_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                mapOf(
                    MarketIndexCode.KOSPI to listOf(
                        price(MarketIndexCode.KOSPI, "2026-07-16", "2705.4000", "0.0123"),
                    ),
                ),
            ),
        )

        val response = service.getMarketIndexSummaries()
        val kospi = response.items[0]
        val kosdaq = response.items[1]

        assertEquals("PARTIAL", kospi.status)
        assertEquals(LocalDate.parse("2026-07-16"), kospi.tradeDate)
        assertEquals(BigDecimal("2705.4000"), kospi.closePrice)
        assertNull(kospi.changeValue)
        assertEquals(BigDecimal("1.2300"), kospi.changeRatePercent)
        assertEquals("EMPTY", kosdaq.status)
    }

    @Test
    @DisplayName("최신 거래일 등락률이 없으면 PARTIAL 상태와 null 등락률 퍼센트를 반환한다")
    fun 최신_등락률이_없으면_PARTIAL_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                mapOf(
                    MarketIndexCode.KOSPI to listOf(
                        price(MarketIndexCode.KOSPI, "2026-07-16", "2705.4000", null),
                        price(MarketIndexCode.KOSPI, "2026-07-15", "2700.0000", "0.0020"),
                    ),
                ),
            ),
        )

        val response = service.getMarketIndexSummaries()
        val kospi = response.items[0]

        assertEquals("PARTIAL", kospi.status)
        assertEquals(BigDecimal("5.4000"), kospi.changeValue)
        assertNull(kospi.changeRatePercent)
    }

    @Test
    @DisplayName("저장된 데이터가 없으면 EMPTY 상태와 null 수치 필드를 반환한다")
    fun 저장된_데이터가_없으면_EMPTY_반환() {
        val service = MarketIndexService(FakeMarketIndexPriceRepository(emptyMap()))

        val response = service.getMarketIndexSummaries()

        response.items.forEach {
            assertEquals("EMPTY", it.status)
            assertNull(it.tradeDate)
            assertNull(it.closePrice)
            assertNull(it.changeValue)
            assertNull(it.changeRatePercent)
        }
    }

    @Test
    @DisplayName("저장된 최신 거래일 기준 3개월 일봉 목록을 거래일 오름차순으로 반환한다")
    fun 기간별_일봉_목록_오름차순_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                latestPrices = emptyMap(),
                latestTradeDates = mapOf(MarketIndexCode.KOSPI to LocalDate.parse("2026-07-22")),
                dailyPrices = mapOf(
                    MarketIndexCode.KOSPI to listOf(
                        dailyPrice(
                            indexCode = MarketIndexCode.KOSPI,
                            tradeDate = "2026-04-22",
                            openPrice = "2680.12345",
                            highPrice = "2700.11115",
                            lowPrice = "2670.55555",
                            closePrice = "2690.44445",
                            volume = 500_000_000L,
                            storedChangeRate = "0.0012",
                        ),
                        dailyPrice(
                            indexCode = MarketIndexCode.KOSPI,
                            tradeDate = "2026-07-22",
                            openPrice = "2780.0000",
                            highPrice = "2800.0000",
                            lowPrice = "2770.0000",
                            closePrice = "2790.0000",
                            volume = 600_000_000L,
                            storedChangeRate = "0.0123",
                        ),
                    ),
                ),
            ),
        )

        val response = service.getMarketIndexPrices("KOSPI", "3M")

        assertEquals("KOSPI", response.indexCode)
        assertEquals("3M", response.period)
        assertEquals(LocalDate.parse("2026-04-22"), response.startDate)
        assertEquals(LocalDate.parse("2026-07-22"), response.endDate)
        assertEquals(2, response.items.size)
        response.items[0].also {
            assertEquals(LocalDate.parse("2026-04-22"), it.tradeDate)
            assertEquals(BigDecimal("2680.1235"), it.openPrice)
            assertEquals(BigDecimal("2700.1112"), it.highPrice)
            assertEquals(BigDecimal("2670.5556"), it.lowPrice)
            assertEquals(BigDecimal("2690.4445"), it.closePrice)
            assertEquals(500_000_000L, it.volume)
            assertEquals(BigDecimal("0.1200"), it.changeRatePercent)
        }
        response.items[1].also {
            assertEquals(LocalDate.parse("2026-07-22"), it.tradeDate)
            assertEquals(BigDecimal("2790.0000"), it.closePrice)
            assertEquals(600_000_000L, it.volume)
            assertEquals(BigDecimal("1.2300"), it.changeRatePercent)
        }
    }

    @Test
    @DisplayName("유효한 지수에 저장된 데이터가 없으면 기간 메타데이터 없이 빈 일봉 목록을 반환한다")
    fun 저장된_일봉이_없으면_빈_목록_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                latestPrices = emptyMap(),
                latestTradeDates = emptyMap(),
                dailyPrices = emptyMap(),
            ),
        )

        val response = service.getMarketIndexPrices("KOSDAQ", "3M")

        assertEquals("KOSDAQ", response.indexCode)
        assertEquals("3M", response.period)
        assertNull(response.startDate)
        assertNull(response.endDate)
        assertEquals(emptyList<Any>(), response.items)
    }

    @Test
    @DisplayName("일봉 등락률이 null이면 응답의 등락률 퍼센트도 null이다")
    fun null_일봉_등락률_null_반환() {
        val service = MarketIndexService(
            FakeMarketIndexPriceRepository(
                latestPrices = emptyMap(),
                latestTradeDates = mapOf(MarketIndexCode.KOSPI to LocalDate.parse("2026-07-22")),
                dailyPrices = mapOf(
                    MarketIndexCode.KOSPI to listOf(
                        dailyPrice(
                            indexCode = MarketIndexCode.KOSPI,
                            tradeDate = "2026-07-22",
                            openPrice = "2780.0000",
                            highPrice = "2800.0000",
                            lowPrice = "2770.0000",
                            closePrice = "2790.0000",
                            volume = 600_000_000L,
                            storedChangeRate = null,
                        ),
                    ),
                ),
            ),
        )

        val response = service.getMarketIndexPrices("KOSPI", "1M")

        assertNull(response.items[0].changeRatePercent)
    }

    @Test
    @DisplayName("지원하지 않는 지수 코드는 404 예외로 처리한다")
    fun 지원하지_않는_지수_404_예외() {
        val service = MarketIndexService(FakeMarketIndexPriceRepository(emptyMap()))

        val exception = org.junit.jupiter.api.assertThrows<ResponseStatusException> {
            service.getMarketIndexPrices("INVALID", "3M")
        }

        assertEquals(HttpStatus.NOT_FOUND, exception.statusCode)
    }

    @Test
    @DisplayName("지원하지 않는 기간은 400 예외로 처리한다")
    fun 지원하지_않는_기간_400_예외() {
        val service = MarketIndexService(FakeMarketIndexPriceRepository(emptyMap()))

        val exception = org.junit.jupiter.api.assertThrows<ResponseStatusException> {
            service.getMarketIndexPrices("KOSPI", "2Y")
        }

        assertEquals(HttpStatus.BAD_REQUEST, exception.statusCode)
    }

    private fun price(
        indexCode: MarketIndexCode,
        tradeDate: String,
        closePrice: String,
        storedChangeRate: String?,
    ): MarketIndexPrice =
        MarketIndexPrice(
            indexCode = indexCode,
            tradeDate = LocalDate.parse(tradeDate),
            closePrice = BigDecimal(closePrice),
            storedChangeRate = storedChangeRate?.let(::BigDecimal),
        )

    private fun dailyPrice(
        indexCode: MarketIndexCode,
        tradeDate: String,
        openPrice: String,
        highPrice: String,
        lowPrice: String,
        closePrice: String,
        volume: Long,
        storedChangeRate: String?,
    ): MarketIndexDailyPrice =
        MarketIndexDailyPrice(
            indexCode = indexCode,
            tradeDate = LocalDate.parse(tradeDate),
            openPrice = BigDecimal(openPrice),
            highPrice = BigDecimal(highPrice),
            lowPrice = BigDecimal(lowPrice),
            closePrice = BigDecimal(closePrice),
            volume = volume,
            storedChangeRate = storedChangeRate?.let(::BigDecimal),
        )

    private class FakeMarketIndexPriceRepository(
        private val latestPrices: Map<MarketIndexCode, List<MarketIndexPrice>>,
        private val latestTradeDates: Map<MarketIndexCode, LocalDate> = emptyMap(),
        private val dailyPrices: Map<MarketIndexCode, List<MarketIndexDailyPrice>> = emptyMap(),
    ) : MarketIndexPriceRepository {
        override fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice> =
            latestPrices[indexCode].orEmpty()

        override fun findLatestTradeDateByIndexCode(indexCode: MarketIndexCode): LocalDate? =
            latestTradeDates[indexCode]

        override fun findDailyPricesByIndexCodeAndTradeDateBetween(
            indexCode: MarketIndexCode,
            startDate: LocalDate,
            endDate: LocalDate,
        ): List<MarketIndexDailyPrice> =
            dailyPrices[indexCode].orEmpty()
    }
}
