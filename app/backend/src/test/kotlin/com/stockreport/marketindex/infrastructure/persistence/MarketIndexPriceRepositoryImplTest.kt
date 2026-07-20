package com.stockreport.marketindex.infrastructure.persistence

import com.stockreport.marketindex.domain.MarketIndexCode
import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Assertions.assertEquals
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
        update(
            """
            INSERT INTO market_index_price (
                index_code, trade_date, open_price, high_price,
                low_price, close_price, volume, change_rate
            )
            VALUES (?, ?::DATE, 1.0000, 1.0000, 1.0000, ?::NUMERIC, 1000, ?::NUMERIC)
            """.trimIndent(),
            indexCode,
            tradeDate,
            closePrice,
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
