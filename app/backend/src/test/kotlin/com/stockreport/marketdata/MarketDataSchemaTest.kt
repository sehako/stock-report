package com.stockreport.marketdata

import org.flywaydb.core.Flyway
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.sql.Connection
import java.sql.DriverManager
import java.sql.SQLException

@DisplayName("시장 데이터 스키마 테스트")
@Testcontainers
class MarketDataSchemaTest {

    @Test
    @DisplayName("마이그레이션을 적용하면 시장 데이터 테이블이 생성된다")
    fun 마이그레이션_시장_데이터_테이블_생성() {
        withMigratedConnection { connection ->
            assertTrue(connection.tableExists("stock"))
            assertTrue(connection.tableExists("stock_price"))
            assertTrue(connection.tableExists("market_index_price"))
        }
    }

    @Test
    @DisplayName("tracked 종목 시장 조회를 위한 인덱스가 생성된다")
    fun tracked_시장_조회_인덱스_생성() {
        withMigratedConnection { connection ->
            assertTrue(connection.indexExists("stock", "idx_stock_tracked_market"))
        }
    }

    @Test
    @DisplayName("같은 시장의 같은 종목코드는 중복 저장할 수 없다")
    fun 같은_시장_종목코드_중복_저장_실패() {
        withMigratedConnection { connection ->
            connection.createStatement().use { statement ->
                statement.executeUpdate(
                    """
                    INSERT INTO stock (market, stock_code, stock_name, tracked)
                    VALUES ('KOSPI', '005930', '삼성전자', true)
                    """.trimIndent(),
                )
            }

            assertThrows<SQLException> {
                connection.createStatement().use { statement ->
                    statement.executeUpdate(
                        """
                        INSERT INTO stock (market, stock_code, stock_name, tracked)
                        VALUES ('KOSPI', '005930', '삼성전자', false)
                        """.trimIndent(),
                    )
                }
            }
        }
    }

    @Test
    @DisplayName("같은 종목의 같은 거래일 일봉은 중복 저장할 수 없다")
    fun 같은_종목_거래일_일봉_중복_저장_실패() {
        withMigratedConnection { connection ->
            val stockId = connection.insertStock()
            connection.insertStockPrice(stockId)

            assertThrows<SQLException> {
                connection.insertStockPrice(stockId)
            }
        }
    }

    @Test
    @DisplayName("같은 지수의 같은 거래일 일봉은 중복 저장할 수 없다")
    fun 같은_지수_거래일_일봉_중복_저장_실패() {
        withMigratedConnection { connection ->
            connection.insertMarketIndexPrice()

            assertThrows<SQLException> {
                connection.insertMarketIndexPrice()
            }
        }
    }

    @Test
    @DisplayName("허용되지 않은 시장과 지수 코드는 저장할 수 없다")
    fun 허용되지_않은_시장_지수코드_저장_실패() {
        withMigratedConnection { connection ->
            assertThrows<SQLException> {
                connection.createStatement().use { statement ->
                    statement.executeUpdate(
                        """
                        INSERT INTO stock (market, stock_code, stock_name)
                        VALUES ('NYSE', 'AAPL', 'Apple')
                        """.trimIndent(),
                    )
                }
            }

            assertThrows<SQLException> {
                connection.createStatement().use { statement ->
                    statement.executeUpdate(
                        """
                        INSERT INTO market_index_price (
                            index_code, trade_date, open_price, high_price,
                            low_price, close_price, volume, change_rate
                        )
                        VALUES ('S&P500', DATE '2026-07-16', 1, 1, 1, 1, 1, 0.0000)
                        """.trimIndent(),
                    )
                }
            }
        }
    }

    private fun withMigratedConnection(block: (Connection) -> Unit) {
        DriverManager.getConnection(postgres.jdbcUrl, postgres.username, postgres.password).use { connection ->
            Flyway.configure()
                .dataSource(postgres.jdbcUrl, postgres.username, postgres.password)
                .cleanDisabled(false)
                .load()
                .apply {
                    clean()
                    migrate()
                }
            block(connection)
        }
    }

    private fun Connection.tableExists(tableName: String): Boolean =
        metaData.getTables(null, "public", tableName, arrayOf("TABLE")).use { resultSet ->
            resultSet.next()
        }

    private fun Connection.indexExists(tableName: String, indexName: String): Boolean =
        metaData.getIndexInfo(null, "public", tableName, false, false).use { resultSet ->
            generateSequence { if (resultSet.next()) resultSet.getString("INDEX_NAME") else null }
                .any { it.equals(indexName, ignoreCase = true) }
        }

    private fun Connection.insertStock(): Long =
        prepareStatement(
            """
            INSERT INTO stock (market, stock_code, stock_name, tracked)
            VALUES ('KOSPI', '005930', '삼성전자', true)
            """.trimIndent(),
            arrayOf("id"),
        ).use { statement ->
            statement.executeUpdate()
            statement.generatedKeys.use { resultSet ->
                resultSet.next()
                resultSet.getLong(1)
            }
        }

    private fun Connection.insertStockPrice(stockId: Long) {
        createStatement().use { statement ->
            statement.executeUpdate(
                """
                INSERT INTO stock_price (
                    stock_id, trade_date, open_price, high_price,
                    low_price, close_price, volume, change_rate
                )
                VALUES ($stockId, DATE '2026-07-16', 1000, 1100, 900, 1050, 1000000, 1.5000)
                """.trimIndent(),
            )
        }
    }

    private fun Connection.insertMarketIndexPrice() {
        createStatement().use { statement ->
            statement.executeUpdate(
                """
                INSERT INTO market_index_price (
                    index_code, trade_date, open_price, high_price,
                    low_price, close_price, volume, change_rate
                )
                VALUES ('KOSPI', DATE '2026-07-16', 2700.1000, 2710.2000, 2690.3000, 2705.4000, 500000000, 0.2500)
                """.trimIndent(),
            )
        }
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
