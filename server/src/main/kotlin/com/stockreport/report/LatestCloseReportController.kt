package com.stockreport.report

import java.time.LocalDate
import org.springframework.format.annotation.DateTimeFormat
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/reports")
class LatestCloseReportController(
    private val latestCloseReportService: LatestCloseReportService,
) {

    @GetMapping("/latest-close")
    fun getLatestCloseReport(): LatestCloseReportResponse =
        latestCloseReportService.getLatestCloseReport()

    @GetMapping("/close")
    fun getHistoricalCloseReport(
        @RequestParam
        @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
        tradeDate: LocalDate,
    ): HistoricalCloseReportResponse =
        latestCloseReportService.getHistoricalCloseReport(tradeDate)
}
