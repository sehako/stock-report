package com.stockreport.marketindex.infrastructure.persistence

import com.stockreport.marketindex.domain.MarketIndexCode
import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.datasource.DriverManagerDataSource
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.math.BigDecimal
import java.time.LocalDate

@DisplayName("시장 지수 가격 JDBC Repository 테스트")
@Testcontainers
class MarketIndexPriceRepositoryImplTest {

    @Test
    @DisplayName("요청한 지수의 최신 두 거래일 데이터를 최신순으로 조회한다")
    fun 최신_두_거래일_최신순_조회() {
        withRepository { repository, jdbcTemplate ->
            jdbcTemplate.insertMarketIndexPrice("KOSPI", "2026-07-14", "2680.0000", "0.0010")
            jdbcTemplate.insertMarketIndexPrice("KOSPI", "2026-07-16", "2705.4000", "0.0123")
            jdbcTemplate.insertMarketIndexPrice("KOSPI", "2026-07-15", "2700.0000", "-0.0020")
            jdbcTemplate.insertMarketIndexPrice("KOSDAQ", "2026-07-16", "820.5000", "-0.0045")

            val prices = repository.findLatestTwoByIndexCode(MarketIndexCode.KOSPI)

            assertEquals(2, prices.size)
            assertEquals(MarketIndexCode.KOSPI, prices[0].indexCode)
            assertEquals(LocalDate.parse("2026-07-16"), prices[0].tradeDate)
            assertEquals(BigDecimal("2705.4000"), prices[0].closePrice)
            assertEquals(BigDecimal("0.0123"), prices[0].storedChangeRate)
            assertEquals(LocalDate.parse("2026-07-15"), prices[1].tradeDate)
            assertEquals(BigDecimal("2700.0000"), prices[1].closePrice)
            assertEquals(BigDecimal("-0.0020"), prices[1].storedChangeRate)
        }
    }

    @Test
    @DisplayName("등락률이 null인 행도 최신 수치로 조회한다")
    fun null_등락률_조회() {
        withRepository { repository, jdbcTemplate ->
            jdbcTemplate.insertMarketIndexPrice("KOSDAQ", "2026-07-16", "820.5000", null)

            val prices = repository.findLatestTwoByIndexCode(MarketIndexCode.KOSDAQ)

            assertEquals(1, prices.size)
            assertEquals(MarketIndexCode.KOSDAQ, prices[0].indexCode)
            assertEquals(LocalDate.parse("2026-07-16"), prices[0].tradeDate)
            assertEquals(BigDecimal("820.5000"), prices[0].closePrice)
            assertEquals(null, prices[0].storedChangeRate)
        }
    }

    @Test
    @DisplayName("요청한 지수의 최신 거래일만 조회하고 데이터가 없으면 null을 반환한다")
    fun 최신_거래일_조회() {
        withRepository { repository, jdbcTemplate ->
            jdbcTemplate.insertMarketIndexPrice("KOSPI", "2026-07-20", "2700.0000", "0.0010")
            jdbcTemplate.insertMarketIndexPrice("KOSPI", "2026-07-22", "2790.0000", "0.0123")
            jdbcTemplate.insertMarketIndexPrice("KOSDAQ", "2026-07-23", "820.0000", "-0.0045")

            val kospiLatestTradeDate = repository.findLatestTradeDateByIndexCode(MarketIndexCode.KOSPI)
            val kosdaqLatestTradeDate = repository.findLatestTradeDateByIndexCode(MarketIndexCode.KOSDAQ)

            assertEquals(LocalDate.parse("2026-07-22"), kospiLatestTradeDate)
            assertEquals(LocalDate.parse("2026-07-23"), kosdaqLatestTradeDate)
        }
        withRepository { repository, _ ->
            assertNull(repository.findLatestTradeDateByIndexCode(MarketIndexCode.KOSPI))
        }
    }

    @Test
    @DisplayName("요청한 지수와 기간에 해당하는 일봉을 거래일 오름차순으로 조회한다")
    fun 기간별_일봉_오름차순_조회() {
        withRepository { repository, jdbcTemplate ->
            jdbcTemplate.insertMarketIndexPrice(
                indexCode = "KOSPI",
                tradeDate = "2026-04-21",
                openPrice = "2670.0000",
                highPrice = "2680.0000",
                lowPrice = "2660.0000",
                closePrice = "2675.0000",
                volume = 400_000_000L,
                changeRate = "0.0010",
            )
            jdbcTemplate.insertMarketIndexPrice(
                indexCode = "KOSPI",
                tradeDate = "2026-07-22",
                openPrice = "2780.0000",
                highPrice = "2800.0000",
                lowPrice = "2770.0000",
                closePrice = "2790.0000",
                volume = 600_000_000L,
                changeRate = null,
            )
            jdbcTemplate.insertMarketIndexPrice(
                indexCode = "KOSDAQ",
                tradeDate = "2026-05-01",
                openPrice = "800.0000",
                highPrice = "810.0000",
                lowPrice = "790.0000",
                closePrice = "805.0000",
                volume = 100_000_000L,
                changeRate = "-0.0045",
            )
            jdbcTemplate.insertMarketIndexPrice(
                indexCode = "KOSPI",
                tradeDate = "2026-04-22",
                openPrice = "2680.0000",
                highPrice = "2700.0000",
                lowPrice = "2670.0000",
                closePrice = "2690.0000",
                volume = 500_000_000L,
                changeRate = "0.0012",
            )
            jdbcTemplate.insertMarketIndexPrice(
                indexCode = "KOSPI",
                tradeDate = "2026-07-23",
                openPrice = "2790.0000",
                highPrice = "2810.0000",
                lowPrice = "2780.0000",
                closePrice = "2800.0000",
                volume = 700_000_000L,
                changeRate = "0.0020",
            )

            val prices = repository.findDailyPricesByIndexCodeAndTradeDateBetween(
                indexCode = MarketIndexCode.KOSPI,
                startDate = LocalDate.parse("2026-04-22"),
                endDate = LocalDate.parse("2026-07-22"),
            )

            assertEquals(2, prices.size)
            prices[0].also {
                assertEquals(MarketIndexCode.KOSPI, it.indexCode)
                assertEquals(LocalDate.parse("2026-04-22"), it.tradeDate)
                assertEquals(BigDecimal("2680.0000"), it.openPrice)
                assertEquals(BigDecimal("2700.0000"), it.highPrice)
                assertEquals(BigDecimal("2670.0000"), it.lowPrice)
                assertEquals(BigDecimal("2690.0000"), it.closePrice)
                assertEquals(500_000_000L, it.volume)
                assertEquals(BigDecimal("0.0012"), it.storedChangeRate)
            }
            prices[1].also {
                assertEquals(LocalDate.parse("2026-07-22"), it.tradeDate)
                assertEquals(BigDecimal("2790.0000"), it.closePrice)
                assertEquals(600_000_000L, it.volume)
                assertNull(it.storedChangeRate)
            }
        }
    }

    private fun withRepository(block: (MarketIndexPriceRepositoryImpl, JdbcTemplate) -> Unit) {
        val dataSource = DriverManagerDataSource(postgres.jdbcUrl, postgres.username, postgres.password)
        Flyway.configure()
            .dataSource(dataSource)
            .cleanDisabled(false)
            .load()
            .apply {
                clean()
                migrate()
            }
        val jdbcTemplate = JdbcTemplate(dataSource)
        block(MarketIndexPriceRepositoryImpl(jdbcTemplate), jdbcTemplate)
    }

    private fun JdbcTemplate.insertMarketIndexPrice(
        indexCode: String,
        tradeDate: String,
        closePrice: String,
        changeRate: String?,
    ) {
        insertMarketIndexPrice(
            indexCode = indexCode,
            tradeDate = tradeDate,
            openPrice = "1.0000",
            highPrice = "1.0000",
            lowPrice = "1.0000",
            closePrice = closePrice,
            volume = 1000L,
            changeRate = changeRate,
        )
    }

    private fun JdbcTemplate.insertMarketIndexPrice(
        indexCode: String,
        tradeDate: String,
        openPrice: String,
        highPrice: String,
        lowPrice: String,
        closePrice: String,
        volume: Long,
        changeRate: String?,
    ) {
        update(
            """
            INSERT INTO market_index_price (
                index_code, trade_date, open_price, high_price,
                low_price, close_price, volume, change_rate
            )
            VALUES (?, ?::DATE, ?::NUMERIC, ?::NUMERIC, ?::NUMERIC, ?::NUMERIC, ?, ?::NUMERIC)
            """.trimIndent(),
            indexCode,
            tradeDate,
            openPrice,
            highPrice,
            lowPrice,
            closePrice,
            volume,
            changeRate,
        )
    }

    companion object {
        @Container
        @JvmStatic
        val postgres: KPostgreSQLContainer = KPostgreSQLContainer("postgres:16-alpine")
            .withDatabaseName("stock_report")
            .withUsername("stock_report")
            .withPassword("stock_report")
    }

    class KPostgreSQLContainer(imageName: String) : PostgreSQLContainer<KPostgreSQLContainer>(imageName)
}
