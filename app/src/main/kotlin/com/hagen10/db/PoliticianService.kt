package com.hagen10.db

import com.hagen10.config.dbQuery
import org.jetbrains.exposed.sql.SortOrder
import org.jetbrains.exposed.sql.select
import org.jetbrains.exposed.sql.selectAll
import org.springframework.stereotype.Service

data class PersonDTO(
    val id: Int,
    val typeId: Int,
    val firstName: String?,
    val lastName: String?,
)

data class PersonVoteDTO(
    val id: Int,
    val titleShort: String?,
    val resume: String?,
    val conclusion: String?,
    val vote: String,
    val timestamp: String?,
    val voteResult: Boolean,
)

data class QuizPromptDTO(
    val id: Int,
    val title: String?,
    val titleShort: String?,
    val resume: String?,
)

@Service
class PoliticianService {
    fun getAllPeople(): List<PersonDTO> =
        dbQuery {
            Person
                .slice(Person.id, Person.typeId, Person.firstName, Person.lastName)
                .select { Person.typeId eq 5 } // 5 = Politiker
                .orderBy(Person.lastName)
                .map {
                    PersonDTO(
                        id = it[Person.id],
                        typeId = it[Person.typeId],
                        firstName = it[Person.firstName],
                        lastName = it[Person.lastName],
                    )
                }
        }

    fun getPersonInfo(personId: Int): PersonDTO? =
        dbQuery {
            Person
                .slice(Person.id, Person.typeId, Person.firstName, Person.lastName)
                .select { Person.id eq personId }
                .mapNotNull {
                    PersonDTO(
                        id = it[Person.id],
                        typeId = it[Person.typeId],
                        firstName = it[Person.firstName],
                        lastName = it[Person.lastName],
                    )
                }.singleOrNull()
        }

    fun getPeopleByIds(personIds: List<Int>): Map<Int, PersonDTO> =
        if (personIds.isEmpty()) emptyMap()
        else dbQuery {
            Person
                .slice(Person.id, Person.typeId, Person.firstName, Person.lastName)
                .select { Person.id inList personIds }
                .associate { row ->
                    val id = row[Person.id]
                    id to PersonDTO(
                        id = id,
                        typeId = row[Person.typeId],
                        firstName = row[Person.firstName],
                        lastName = row[Person.lastName],
                    )
                }
        }

    fun getPersonVotes(personId: Int): List<PersonVoteDTO> =
        dbQuery {
            (Case innerJoin CaseStage innerJoin VoteSession innerJoin Vote innerJoin Person innerJoin VoteType)
                .slice(VoteSession.id, VoteSession.voteResult, VoteSession.timestamp, Case.titleShort, Case.resume, Case.conclusion, VoteType.voteType)
                .select { Person.id eq personId }
                .orderBy(VoteSession.timestamp to SortOrder.DESC)
                .map {
                    PersonVoteDTO(
                        id = it[VoteSession.id],
                        titleShort = it[Case.titleShort],
                        resume = it[Case.resume],
                        conclusion = it[Case.conclusion],
                        voteResult = it[VoteSession.voteResult],
                        vote = it[VoteType.voteType],
                        timestamp = it[VoteSession.timestamp].toString(),
                    )
                }
        }
}
