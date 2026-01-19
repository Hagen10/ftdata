package com.hagen10.config

import org.jetbrains.exposed.sql.transactions.transaction

fun <T> dbQuery(block: () -> T): T = transaction { block() }
