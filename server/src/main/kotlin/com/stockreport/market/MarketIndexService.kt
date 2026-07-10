package com.stockreport.market

import java.time.LocalDate
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.web.server.ResponseStatusException

@Service
class MarketIndexService(
    private val marketIndexRepository: MarketIndexRepository,
) {

    fun getTimeseries(startDate: LocalDate, endDate: LocalDate): MarketIndexTimeseriesResponse {
        if (startDate > endDate) {
            throw ResponseStatusException(HttpStatus.BAD_REQUEST, "startDate must be before or equal to endDate")
        }

        val pricesByIndexCode = marketIndexRepository.findPrices(startDate, endDate, INDEX_CODES)
            .groupBy { it.indexCode }

        return MarketIndexTimeseriesResponse(
            startDate = startDate,
            endDate = endDate,
            indices = INDEX_CODES.map { indexCode ->
                MarketIndexSeriesDto(
                    indexCode = indexCode,
                    prices = pricesByIndexCode.orEmpty(indexCode).map { it.toDto() },
                )
            },
        )
    }

    private fun Map<String, List<MarketIndexPriceRow>>.orEmpty(indexCode: String): List<MarketIndexPriceRow> =
        this[indexCode] ?: emptyList()

    private fun MarketIndexPriceRow.toDto(): MarketIndexPricePointDto =
        MarketIndexPricePointDto(
            tradeDate = tradeDate,
            openPrice = openPrice,
            highPrice = highPrice,
            lowPrice = lowPrice,
            closePrice = closePrice,
            volume = volume,
            changeRate = changeRate,
        )

    companion object {
        val INDEX_CODES = listOf("KOSPI", "KOSDAQ")
    }
}
