package com.hagen10.db

import org.jetbrains.exposed.sql.Table
import org.jetbrains.exposed.sql.javatime.timestamp

object Person : Table("ODA.dbo.aktør") {
    val id = integer("id")
    val typeId = integer("typeid")
    val firstName = varchar("fornavn", 100)
    val lastName = varchar("efternavn", 100)

    override val primaryKey = PrimaryKey(id)
}

object Case : Table("ODA.dbo.sag") {
    val id = integer("id")
    val titleShort = varchar("titelkort", 500)
    val resume = varchar("resume", 500)
    val conclusion = varchar("afstemningskonklusion", 500)
    val period = integer("periodeid")

    override val primaryKey = PrimaryKey(id)
}

object CaseStage : Table("ODA.dbo.sagstrin") {
    val id = integer("id")
    val caseId = integer("sagid").references(Case.id)

    override val primaryKey = PrimaryKey(id)
}

object CaseTopic : Table("ODA.dbo.emneordsag") {
    val id = integer("id")
    val caseTopicId = integer("emneordid")
    val caseId = integer("sagid")

    override val primaryKey = PrimaryKey(id)
}

// This is for the voting session, not sure if there is a better name?
object VoteSession : Table("ODA.dbo.afstemning") {
    val id = integer("id")
    val caseStageId = integer("sagstrinid").references(CaseStage.id)
    val timestamp = timestamp("opdateringsdato")
    val voteResult = bool("vedtaget")

    override val primaryKey = PrimaryKey(id)
}

// This is each vote that has been cast by a politician
object Vote : Table("ODA.dbo.stemme") {
    val id = integer("id")
    val votingId = integer("afstemningid").references(VoteSession.id)
    val personId = integer("aktørid").references(Person.id)
    val voteTypeId = integer("typeid").references(VoteType.id)

    override val primaryKey = PrimaryKey(id)
}

object VoteType : Table("ODA.dbo.stemmetype") {
    val id = integer("id")
    val voteType = varchar("type", 10)

    override val primaryKey = PrimaryKey(id)
}

object Period : Table("ODA.dbo.periode") {
    val id = integer("id")
    val startDate = varchar("startdato", 25)
    val endDate = varchar("slutdato", 25)
    val title = varchar("titel", 25)

    override val primaryKey = PrimaryKey(id)
}
