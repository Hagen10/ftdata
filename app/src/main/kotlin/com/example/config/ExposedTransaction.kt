package com.example.config

import org.jetbrains.exposed.sql.transactions.transaction

fun <T> dbQuery(block: () -> T): T =
    transaction { block() }
