package com.stockreport.marketindex.application

import com.stockreport.marketindex.application.response.MarketIndexPriceResponse
import com.stockreport.marketindex.application.response.MarketIndexPricesResponse
import com.stockreport.marketindex.application.response.MarketIndexSummariesResponse
import com.stockreport.marketindex.application.response.MarketIndexSummaryResponse
import com.stockreport.marketindex.domain.MarketIndexCode
import com.stockreport.marketindex.domain.MarketIndexDailyPrice
import com.stockreport.marketindex.domain.MarketIndexPrice
import com.stockreport.marketindex.domain.MarketIndexPricePeriod
import com.stockreport.marketindex.domain.MarketIndexPriceRepository
import com.stockreport.marketindex.domain.MarketIndexSummary
import com.stockreport.marketindex.domain.MarketIndexSummaryStatus
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.web.server.ResponseStatusException
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

    fun getMarketIndexPrices(
        indexCode: String,
        period: String,
    ): MarketIndexPricesResponse {
        val parsedIndexCode = MarketIndexCode.from(indexCode)
            ?: throw ResponseStatusException(HttpStatus.NOT_FOUND, "지원하지 않는 시장 지수 코드입니다.")
        val parsedPeriod = MarketIndexPricePeriod.from(period)
            ?: throw ResponseStatusException(HttpStatus.BAD_REQUEST, "지원하지 않는 기간입니다.")
        val endDate = marketIndexPriceRepository.findLatestTradeDateByIndexCode(parsedIndexCode)
            ?: return MarketIndexPricesResponse(
                indexCode = parsedIndexCode.name,
                period = parsedPeriod.value,
                startDate = null,
                endDate = null,
                items = emptyList(),
            )
        val startDate = parsedPeriod.startDateFrom(endDate)
        val prices = marketIndexPriceRepository.findDailyPricesByIndexCodeAndTradeDateBetween(
            indexCode = parsedIndexCode,
            startDate = startDate,
            endDate = endDate,
        )

        return MarketIndexPricesResponse(
            indexCode = parsedIndexCode.name,
            period = parsedPeriod.value,
            startDate = startDate,
            endDate = endDate,
            items = prices.map { it.toResponse() },
        )
    }

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

    private fun MarketIndexDailyPrice.toResponse(): MarketIndexPriceResponse =
        MarketIndexPriceResponse(
            tradeDate = tradeDate,
            openPrice = openPrice.toApiScale(),
            highPrice = highPrice.toApiScale(),
            lowPrice = lowPrice.toApiScale(),
            closePrice = closePrice.toApiScale(),
            volume = volume,
            changeRatePercent = storedChangeRate?.multiply(PERCENT)?.toApiScale(),
        )

    private fun BigDecimal.toApiScale(): BigDecimal = setScale(API_SCALE, RoundingMode.HALF_UP)

    companion object {
        private const val API_SCALE = 4
        private val PERCENT = BigDecimal("100")
    }
}
