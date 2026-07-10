package com.stockreport.report

import java.math.BigDecimal
import java.time.LocalDate
import java.time.OffsetDateTime

data class LatestCloseReportResponse(
    val status: LatestCloseReportStatus,
    val asOfDate: LocalDate,
    val report: LatestCloseReportDto?,
)

data class HistoricalCloseReportResponse(
    val status: HistoricalCloseReportStatus,
    val tradeDate: LocalDate,
    val serviceStartDate: LocalDate,
    val report: LatestCloseReportDto?,
)

data class LatestCloseReportDto(
    val reportDate: LocalDate,
    val revisionNo: Int,
    val revisionType: String,
    val calculationVersion: String,
    val publishedAt: OffsetDateTime?,
    val analysisUniverse: AnalysisUniverseDto,
    val marketIndices: List<MarketIndexDto>,
    val scannerStats: ScannerStatsDto,
    val aiSummary: AiSummaryDto,
)

data class AnalysisUniverseDto(
    val market: String,
    val selectionRule: String,
    val targetStockCount: Int,
)

data class MarketIndexDto(
    val indexCode: String,
    val tradeDate: LocalDate,
    val openPrice: BigDecimal?,
    val highPrice: BigDecimal?,
    val lowPrice: BigDecimal?,
    val closePrice: BigDecimal?,
    val volume: Long?,
    val changeRate: BigDecimal?,
)

data class ScannerStatsDto(
    val targetStockCount: Int,
    val completedStockCount: Int,
    val failedStockCount: Int,
    val insufficientStockCount: Int,
    val noTradingStockCount: Int,
    val goldenCrossStockCount: Int,
)

data class AiSummaryDto(
    val status: String,
    val summaryText: String?,
)

enum class LatestCloseReportStatus {
    PUBLISHED,
    DELAYED,
    PREPARING,
    MARKET_CLOSED,
    NOT_PUBLISHED,
    EMPTY,
}

enum class HistoricalCloseReportStatus {
    PUBLISHED,
    MARKET_CLOSED,
    NOT_PUBLISHED,
    BEFORE_SERVICE_START,
}
