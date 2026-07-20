package com.stockreport.marketindex.application

import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
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

    private class FakeMarketIndexPriceRepository(
        private val prices: Map<MarketIndexCode, List<MarketIndexPrice>>,
    ) : MarketIndexPriceRepository {
        override fun findLatestTwoByIndexCode(indexCode: MarketIndexCode): List<MarketIndexPrice> =
            prices[indexCode].orEmpty()
    }
}
