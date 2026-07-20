package com.stockreport.marketindex.application

import com.stockreport.marketindex.application.response.MarketIndexSummariesResponse
import com.stockreport.marketindex.application.response.MarketIndexSummaryResponse
import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import com.stockreport.marketindex.domain.MarketIndexSummary
import com.stockreport.marketindex.domain.MarketIndexSummaryStatus
import org.springframework.stereotype.Service
import java.math.BigDecimal
import java.math.RoundingMode

@Service
class MarketIndexService(
    private val marketIndexPriceRepository: MarketIndexPriceRepository,
) {
    fun getMarketIndexSummaries(): MarketIndexSummariesResponse =
        MarketIndexSummariesResponse(
            items = MarketIndexCode.entries.map { indexCode ->
                summarize(indexCode, marketIndexPriceRepository.findLatestTwoByIndexCode(indexCode))
            }.map { it.toResponse() },
        )

    private fun summarize(
        indexCode: MarketIndexCode,
        prices: List<MarketIndexPrice>,
    ): MarketIndexSummary {
        val latest = prices.firstOrNull()
            ?: return MarketIndexSummary(
                indexCode = indexCode,
                status = MarketIndexSummaryStatus.EMPTY,
                tradeDate = null,
                closePrice = null,
                changeValue = null,
                changeRatePercent = null,
            )
        val previous = prices.getOrNull(1)
        val changeValue = previous?.let { latest.closePrice.subtract(it.closePrice).toApiScale() }
        val changeRatePercent = latest.storedChangeRate?.multiply(PERCENT)?.toApiScale()
        val status = if (changeValue != null && changeRatePercent != null) {
            MarketIndexSummaryStatus.AVAILABLE
        } else {
            MarketIndexSummaryStatus.PARTIAL
        }

        return MarketIndexSummary(
            indexCode = indexCode,
            status = status,
            tradeDate = latest.tradeDate,
            closePrice = latest.closePrice.toApiScale(),
            changeValue = changeValue,
            changeRatePercent = changeRatePercent,
        )
    }

    private fun MarketIndexSummary.toResponse(): MarketIndexSummaryResponse =
        MarketIndexSummaryResponse(
            indexCode = indexCode.name,
            status = status.name,
            tradeDate = tradeDate,
            closePrice = closePrice,
            changeValue = changeValue,
            changeRatePercent = changeRatePercent,
        )

    private fun BigDecimal.toApiScale(): BigDecimal = setScale(API_SCALE, RoundingMode.HALF_UP)

    companion object {
        private const val API_SCALE = 4
        private val PERCENT = BigDecimal("100")
    }
}
