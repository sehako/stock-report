package com.stockreport

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class StockReportApplication

fun main(args: Array<String>) {
    runApplication<StockReportApplication>(*args)
}
