package com.example.config

import jakarta.annotation.PostConstruct
import javax.sql.DataSource
import org.jetbrains.exposed.sql.Database
import org.springframework.context.annotation.Configuration
import org.slf4j.LoggerFactory

import com.zaxxer.hikari.HikariDataSource

@Configuration
class ExposedConfig(
    private val dataSource: DataSource
) {

    private val log = LoggerFactory.getLogger(javaClass)

    @PostConstruct
    fun init() {
        log.info("Initializing Exposed database connection")

        Database.connect(dataSource)
    }
}
