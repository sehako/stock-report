package com.stockreport.report

import org.springframework.web.bind.annotation.GetMapping
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
}
