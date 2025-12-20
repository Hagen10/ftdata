package com.example.db

import org.jetbrains.exposed.sql.Table

object Pols : Table("ODA.dbo.aktør") {
    val id = integer("id")
    val typeid = integer ("typeid")
    val fornavn = varchar("fornavn", 100)
    val efternavn = varchar("efternavn", 100)

    override val primaryKey = PrimaryKey(id)
}
