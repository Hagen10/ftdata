package com.example.db

import org.jetbrains.exposed.sql.Table

object Pols : Table("ODA.dbo.aktør") {
    val id = integer("id")
    val typeId = integer ("typeid")
    val firstName = varchar("fornavn", 100)
    val lastName = varchar("efternavn", 100)

    override val primaryKey = PrimaryKey(id)
}

object Case : Table("ODA.dbo.sag") {
    val id = integer("id")
    val titleShort = varchar("titelkort", 500)
    val resume = varchar("resume", 500)
    val votingConclusion = varchar("afstemningskonklusion", 500)

    override val primaryKey = PrimaryKey(id)
}

object CaseStage : Table("ODA.dbo.sagstrin") {
    val id = integer("id")
    val caseId = integer("sagid").references(Case.id)

    override val primaryKey = PrimaryKey(id)
}

object Voting : Table("ODA.dbo.afstemning") {
    val id = integer("id")
    val caseStageId = integer("sagstrinid").references(CaseStage.id)

    override val primaryKey = PrimaryKey(id)
}

object Vote : Table("ODA.dbo.stemme") {
    val id = integer("id")
    val votingId = integer("afstemningid").references(Voting.id)
    val polId = integer("aktørid").references(Pols.id)
    val voteTypeId = integer("typeid").references(VoteType.id)

    override val primaryKey = PrimaryKey(id)
}

object VoteType : Table("ODA.dbo.stemmetype") {
    val id = integer("id")
    val voteType = varchar("type", 10)

    override val primaryKey = PrimaryKey(id)
}
