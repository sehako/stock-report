package com.stockreport

import java.sql.Connection
import java.sql.SQLException
import javax.sql.DataSource
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.context.runner.ApplicationContextRunner
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.test.context.ActiveProfiles
import org.testcontainers.containers.PostgreSQLContainer
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class StockReportApplicationTests {

    @Autowired
    private lateinit var dataSource: DataSource

    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val postgres: PostgreSQLContainer<*> = PostgreSQLContainer("postgres:16-alpine")
    }

    @Test
    fun contextLoadsWithPostgres() {
        dataSource.connection.use { connection ->
            assertEquals("PostgreSQL", connection.metaData.databaseProductName)
        }
    }

    @Test
    fun contextFailsWithoutServiceStartDate() {
        ApplicationContextRunner()
            .withUserConfiguration(ServiceStartDateRequiredConfig::class.java)
            .run { context ->
                assertTrue(context.startupFailure != null)
            }
    }

    @Test
    fun flywayCreatesInitialDataModelTables() {
        val expectedTables = setOf(
            "stock",
            "daily_price",
            "daily_indicator",
            "market_index_price",
            "report_revision",
            "stock_analysis",
            "signal_event",
            "industry_analysis",
            "market_ai_summary",
            "batch_job_run",
            "batch_stock_run",
            "daily_stock_processing_status",
        )

        dataSource.connection.use { connection ->
            val actualTables = connection.prepareStatement(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                  and table_type = 'BASE TABLE'
                """.trimIndent(),
            ).use { statement ->
                statement.executeQuery().use { resultSet ->
                    buildSet {
                        while (resultSet.next()) {
                            add(resultSet.getString("table_name"))
                        }
                    }
                }
            }

            assertTrue(
                actualTables.containsAll(expectedTables),
                "missing tables: ${expectedTables - actualTables}",
            )
        }
    }

    @Test
    fun initialDataModelEnforcesDatabaseContracts() {
        dataSource.connection.use { connection ->
            val stockId = connection.insertStock("005930", "Samsung Electronics")
            val otherStockId = connection.insertStock("000660", "SK Hynix")
            val revisionId = connection.insertReportRevision("2026-07-03", 1, isActive = true)
            val signalEventId = connection.insertSignalEvent(stockId, "2026-07-03")
            val batchJobRunId = connection.insertBatchJobRun("2026-07-03")

            connection.executeUpdate(
                """
                insert into daily_price (stock_id, trade_date)
                values ($stockId, date '2026-07-03')
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_price (stock_id, trade_date)
                    values ($stockId, date '2026-07-03')
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into daily_indicator (stock_id, trade_date, calculation_version)
                values ($stockId, date '2026-07-03', 'v1')
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_indicator (stock_id, trade_date, calculation_version)
                    values ($stockId, date '2026-07-03', 'v1')
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.insertSignalEvent(stockId, "2026-07-03")
            }

            assertFailsWith<SQLException> {
                connection.insertReportRevision("2026-07-03", 2, isActive = true)
            }
            assertFailsWith<SQLException> {
                connection.insertReportRevision("2026-07-03", 1, isActive = false)
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into report_revision (
                        report_date,
                        revision_no,
                        revision_type,
                        is_active,
                        calculation_version
                    )
                    values (date '2026-07-04', 0, 'INITIAL', false, 'v1')
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into report_revision (
                        report_date,
                        revision_no,
                        revision_type,
                        is_active,
                        calculation_version
                    )
                    values (date '2026-07-04', 1, 'DRAFT', false, 'v1')
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into market_index_price (index_code, trade_date)
                values ('KOSPI', date '2026-07-03')
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_index_price (index_code, trade_date)
                    values ('KOSPI', date '2026-07-03')
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into signal_event (
                        stock_id,
                        signal_type,
                        cross_date,
                        calculation_version
                    )
                    values ($stockId, 'BUY_SIGNAL', date '2026-07-04', 'v1')
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into stock_analysis (
                    report_revision_id,
                    stock_id,
                    signal_event_id,
                    analysis_status,
                    stock_name_snapshot,
                    market_snapshot,
                    selection_rank,
                    selection_volume
                )
                values (
                    $revisionId,
                    $stockId,
                    $signalEventId,
                    'SIGNAL_FOUND',
                    'Samsung Electronics',
                    'KOSPI',
                    1,
                    1000
                )
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into stock_analysis (
                        report_revision_id,
                        stock_id,
                        analysis_status,
                        stock_name_snapshot,
                        market_snapshot,
                        selection_rank,
                        selection_volume
                    )
                    values (
                        $revisionId,
                        $stockId,
                        'NO_SIGNAL',
                        'Samsung Electronics',
                        'KOSPI',
                        2,
                        900
                    )
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into stock_analysis (
                        report_revision_id,
                        stock_id,
                        analysis_status,
                        stock_name_snapshot,
                        market_snapshot,
                        selection_rank,
                        selection_volume
                    )
                    values (
                        $revisionId,
                        $otherStockId,
                        'UNKNOWN',
                        'SK Hynix',
                        'KOSPI',
                        2,
                        900
                    )
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into stock_analysis (
                        report_revision_id,
                        stock_id,
                        analysis_status,
                        stock_name_snapshot,
                        market_snapshot,
                        selection_rank,
                        selection_volume
                    )
                    values (
                        $revisionId,
                        $otherStockId,
                        'NO_SIGNAL',
                        'SK Hynix',
                        'NYSE',
                        2,
                        900
                    )
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into stock_analysis (
                        report_revision_id,
                        stock_id,
                        analysis_status,
                        stock_name_snapshot,
                        market_snapshot,
                        selection_rank,
                        selection_volume
                    )
                    values (
                        $revisionId,
                        $otherStockId,
                        'NO_SIGNAL',
                        'KOSPI',
                        'KOSPI',
                        0,
                        900
                    )
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into industry_analysis (
                    report_revision_id,
                    industry_name,
                    area_basis,
                    stock_count,
                    signal_count,
                    signal_denominator_count,
                    excluded_count,
                    signal_ratio
                )
                values ($revisionId, 'Electronics', 'market_cap', 2, 1, 2, 0, 0.5)
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into industry_analysis (
                        report_revision_id,
                        industry_name,
                        area_basis,
                        stock_count,
                        signal_count,
                        signal_denominator_count,
                        excluded_count
                    )
                    values ($revisionId, 'Electronics', 'trade_value', 2, 1, 2, 0)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into industry_analysis (
                        report_revision_id,
                        industry_name,
                        area_basis,
                        stock_count,
                        signal_count,
                        signal_denominator_count,
                        excluded_count
                    )
                    values ($revisionId, 'Semiconductor', 'theme', 1, 0, 1, 0)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into industry_analysis (
                        report_revision_id,
                        industry_name,
                        area_basis,
                        stock_count,
                        signal_count,
                        signal_denominator_count,
                        excluded_count
                    )
                    values ($revisionId, 'Semiconductor', 'stock_count', -1, 0, 1, 0)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into industry_analysis (
                        report_revision_id,
                        industry_name,
                        area_basis,
                        stock_count,
                        signal_count,
                        signal_denominator_count,
                        excluded_count,
                        signal_ratio
                    )
                    values ($revisionId, 'Semiconductor', 'stock_count', 1, 0, 1, 0, 1.5)
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                values (date '2026-07-03', $revisionId, 'PENDING', 'hash-1')
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                    values (date '2026-07-03', $revisionId, 'PENDING', 'hash-2')
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                    values (date '2026-07-04', $revisionId, 'PENDING', 'hash-3')
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                    values (date '2026-07-04', $revisionId, 'FAILED', 'hash-3')
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                    values (date '2026-07-04', $revisionId, 'PENDING', null)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.insertBatchJobRun("2026-07-03")
            }

            connection.executeUpdate(
                """
                insert into daily_stock_processing_status (
                    report_date,
                    stock_id,
                    analysis_status,
                    last_batch_job_run_id
                )
                values (date '2026-07-03', $stockId, 'DATA_PREPARING', $batchJobRunId)
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_stock_processing_status (
                        report_date,
                        stock_id,
                        analysis_status,
                        last_batch_job_run_id
                    )
                    values (date '2026-07-04', $otherStockId, 'DATA_PREPARING', $batchJobRunId)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_stock_processing_status (report_date, stock_id, analysis_status)
                    values (date '2026-07-03', $stockId, 'NO_SIGNAL')
                    """.trimIndent(),
                )
            }

            connection.executeUpdate(
                """
                insert into batch_stock_run (
                    batch_job_run_id,
                    stock_id,
                    report_date,
                    status,
                    attempt_count
                )
                values ($batchJobRunId, $stockId, date '2026-07-03', 'PENDING', 0)
                """.trimIndent(),
            )
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into batch_stock_run (
                        batch_job_run_id,
                        stock_id,
                        report_date,
                        status,
                        attempt_count
                    )
                    values ($batchJobRunId, $stockId, date '2026-07-03', 'RUNNING', 1)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into batch_stock_run (
                        batch_job_run_id,
                        stock_id,
                        report_date,
                        status,
                        attempt_count
                    )
                    values ($batchJobRunId, $otherStockId, date '2026-07-04', 'PENDING', 0)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into batch_stock_run (
                        batch_job_run_id,
                        stock_id,
                        report_date,
                        status,
                        attempt_count
                    )
                    values ($batchJobRunId, $otherStockId, date '2026-07-03', 'UNKNOWN', 0)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into batch_stock_run (
                        batch_job_run_id,
                        stock_id,
                        report_date,
                        status,
                        attempt_count
                    )
                    values ($batchJobRunId, $otherStockId, date '2026-07-03', 'PENDING', -1)
                    """.trimIndent(),
                )
            }
            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into batch_stock_run (
                        batch_job_run_id,
                        stock_id,
                        report_date,
                        status,
                        attempt_count
                    )
                    values (999999, $otherStockId, date '2026-07-03', 'PENDING', 0)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into stock (stock_code, stock_name, market) values ('000000', 'INVALID', 'NYSE')")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into stock (stock_code, stock_name, market) values ('005930', 'DUPLICATE', 'KOSPI')")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into market_index_price (index_code, trade_date) values ('KRX100', date '2026-07-04')")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into stock (stock_code, stock_name, market) values (null, 'NULL', 'KOSPI')")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_indicator (stock_id, trade_date, calculation_version)
                    values ($stockId, date '2026-07-04', null)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into batch_job_run (report_date, status) values (null, 'RUNNING')")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate("insert into batch_job_run (report_date, status) values (date '2026-07-04', null)")
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_stock_processing_status (report_date, stock_id, analysis_status)
                    values (date '2026-07-04', $stockId, null)
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into daily_price (stock_id, trade_date)
                    values (999999, date '2026-07-04')
                    """.trimIndent(),
                )
            }

            assertFailsWith<SQLException> {
                connection.executeUpdate(
                    """
                    insert into market_ai_summary (report_date, report_revision_id, status, input_hash)
                    values (date '2026-07-04', 999999, 'PENDING', 'hash-3')
                    """.trimIndent(),
                )
            }

            val dailyIndicatorColumns = connection.columnNames("daily_indicator")
            assertFalse("rsi" in dailyIndicatorColumns)
            assertFalse("stoch_rsi" in dailyIndicatorColumns)
            assertFalse("ma10" in dailyIndicatorColumns)
            assertFalse("ma200" in dailyIndicatorColumns)
            assertTrue(connection.enumTypeNames().isEmpty(), "DB enum types must not be created")
        }
    }

    private fun Connection.insertStock(stockCode: String, stockName: String): Long =
        prepareStatement(
            """
            insert into stock (stock_code, stock_name, market, industry_name)
            values (?, ?, 'KOSPI', 'Electronics')
            returning id
            """.trimIndent(),
        ).use { statement ->
            statement.setString(1, stockCode)
            statement.setString(2, stockName)
            statement.executeQuery().use { resultSet ->
                resultSet.next()
                resultSet.getLong("id")
            }
        }

    private fun Connection.insertReportRevision(reportDate: String, revisionNo: Int, isActive: Boolean): Long =
        prepareStatement(
            """
            insert into report_revision (
                report_date,
                revision_no,
                revision_type,
                is_active,
                calculation_version
            )
            values (?::date, ?, 'INITIAL', ?, 'v1')
            returning id
            """.trimIndent(),
        ).use { statement ->
            statement.setString(1, reportDate)
            statement.setInt(2, revisionNo)
            statement.setBoolean(3, isActive)
            statement.executeQuery().use { resultSet ->
                resultSet.next()
                resultSet.getLong("id")
            }
        }

    private fun Connection.insertSignalEvent(stockId: Long, crossDate: String): Long =
        prepareStatement(
            """
            insert into signal_event (
                stock_id,
                signal_type,
                cross_date,
                calculation_version
            )
            values (?, 'STOCH_MACD_GOLDEN_CROSS', ?::date, 'v1')
            returning id
            """.trimIndent(),
        ).use { statement ->
            statement.setLong(1, stockId)
            statement.setString(2, crossDate)
            statement.executeQuery().use { resultSet ->
                resultSet.next()
                resultSet.getLong("id")
            }
        }

    private fun Connection.insertBatchJobRun(reportDate: String): Long =
        prepareStatement(
            """
            insert into batch_job_run (report_date, status)
            values (?::date, 'RUNNING')
            returning id
            """.trimIndent(),
        ).use { statement ->
            statement.setString(1, reportDate)
            statement.executeQuery().use { resultSet ->
                resultSet.next()
                resultSet.getLong("id")
            }
        }

    private fun Connection.executeUpdate(sql: String): Int =
        createStatement().use { statement -> statement.executeUpdate(sql) }

    private fun Connection.columnNames(tableName: String): Set<String> =
        prepareStatement(
            """
            select column_name
            from information_schema.columns
            where table_schema = 'public'
              and table_name = ?
            """.trimIndent(),
        ).use { statement ->
            statement.setString(1, tableName)
            statement.executeQuery().use { resultSet ->
                buildSet {
                    while (resultSet.next()) {
                        add(resultSet.getString("column_name"))
                    }
                }
            }
        }

    private fun Connection.enumTypeNames(): Set<String> =
        prepareStatement(
            """
            select typname
            from pg_type
            where typtype = 'e'
            """.trimIndent(),
        ).use { statement ->
            statement.executeQuery().use { resultSet ->
                buildSet {
                    while (resultSet.next()) {
                        add(resultSet.getString("typname"))
                    }
                }
            }
        }
}

@org.springframework.context.annotation.Configuration(proxyBeanMethods = false)
private class ServiceStartDateRequiredConfig(
    @org.springframework.beans.factory.annotation.Value("\${stock-report.service-start-date}")
    private val serviceStartDate: java.time.LocalDate,
)
