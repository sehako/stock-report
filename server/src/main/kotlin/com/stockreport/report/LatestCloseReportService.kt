package com.stockreport.report

import java.time.Clock
import java.time.LocalDate
import org.springframework.stereotype.Service

@Service
class LatestCloseReportService(
    private val repository: LatestCloseReportRepository,
    private val clock: Clock,
) {

    fun getLatestCloseReport(): LatestCloseReportResponse {
        val today = LocalDate.now(clock)
        val todayRevision = repository.findActiveRevisionByReportDate(today)

        val status = if (todayRevision != null) {
            LatestCloseReportStatus.PUBLISHED
        } else {
            displayStatus(repository.findBatchStatusByReportDate(today))
        }

        val selectedRevision = todayRevision ?: repository.findLatestActiveRevision()

        if (selectedRevision == null) {
            return LatestCloseReportResponse(
                status = LatestCloseReportStatus.EMPTY,
                asOfDate = today,
                report = null,
            )
        }

        return LatestCloseReportResponse(
            status = status,
            asOfDate = today,
            report = selectedRevision.toDto(),
        )
    }

    private fun displayStatus(batchStatus: String?): LatestCloseReportStatus =
        when (batchStatus) {
            "DELAYED", "FAILED" -> LatestCloseReportStatus.DELAYED
            "RUNNING", "RETRYING" -> LatestCloseReportStatus.PREPARING
            "SKIPPED_MARKET_CLOSED" -> LatestCloseReportStatus.MARKET_CLOSED
            else -> LatestCloseReportStatus.NOT_PUBLISHED
        }

    private fun ReportRevisionRow.toDto(): LatestCloseReportDto {
        val goldenCrossStockCount = repository.countGoldenCrossStocks(id, calculationVersion)
        val aiSummary = repository.findAiSummary(reportDate, id)

        return LatestCloseReportDto(
            reportDate = reportDate,
            revisionNo = revisionNo,
            revisionType = revisionType,
            calculationVersion = calculationVersion,
            publishedAt = publishedAt,
            analysisUniverse = AnalysisUniverseDto(
                market = "KRX",
                selectionRule = "종가 1,000원 이상 종목 중 거래량 상위 200개",
                targetStockCount = targetStockCount ?: 0,
            ),
            marketIndices = repository.findMarketIndices(reportDate).map {
                MarketIndexDto(
                    indexCode = it.indexCode,
                    tradeDate = it.tradeDate,
                    openPrice = it.openPrice,
                    highPrice = it.highPrice,
                    lowPrice = it.lowPrice,
                    closePrice = it.closePrice,
                    volume = it.volume,
                    changeRate = it.changeRate,
                )
            },
            scannerStats = ScannerStatsDto(
                targetStockCount = targetStockCount ?: 0,
                completedStockCount = completedStockCount ?: 0,
                failedStockCount = failedStockCount ?: 0,
                insufficientStockCount = insufficientStockCount ?: 0,
                noTradingStockCount = noTradingStockCount ?: 0,
                goldenCrossStockCount = goldenCrossStockCount,
            ),
            aiSummary = AiSummaryDto(
                status = aiSummary?.status ?: "PENDING",
                summaryText = aiSummary?.summaryText,
            ),
        )
    }
}
