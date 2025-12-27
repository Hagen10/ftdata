package com.example.config

import com.zaxxer.hikari.HikariDataSource
import jakarta.annotation.PostConstruct
import org.jetbrains.exposed.sql.Database
import org.slf4j.LoggerFactory
import org.springframework.context.annotation.Configuration
import javax.sql.DataSource

@Configuration
class ExposedConfig(
    private val dataSource: DataSource,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @PostConstruct
    fun init() {
        log.info("Initializing Exposed database connection")

        Database.connect(dataSource)
    }
}
