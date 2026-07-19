package com.stockreport

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class StockReportBackendApplication

fun main(args: Array<String>) {
    runApplication<StockReportBackendApplication>(*args)
}
