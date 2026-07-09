package com.stockreport.config

import java.time.Clock
import java.time.ZoneId
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class TimeConfig {

    @Bean
    fun clock(): Clock = Clock.system(ZoneId.of("Asia/Seoul"))
}
