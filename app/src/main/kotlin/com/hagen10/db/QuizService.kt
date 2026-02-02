package com.hagen10.db

import com.hagen10.config.dbQuery
import org.jetbrains.exposed.sql.SortOrder
import org.jetbrains.exposed.sql.select
import org.jetbrains.exposed.sql.selectAll
import org.springframework.stereotype.Service

data class PromptDTO(
    val id: Int,
    val title: String?,
    val titleShort: String?,
    val resume: String?,
)

@Service
class QuizService {
    fun getPrompts(): List<PromptDTO> =
        dbQuery {
            (Case innerJoin Period)
                .slice(Case.id, Case.title, Case.titleShort, Case.resume, Period.id)
                .select { Period.id eq 84443 } // 84443 = Borgerforslag
                .map {
                    PromptDTO(
                        id = it[Case.id],
                        title = it[Case.title],
                        titleShort = it[Case.titleShort],
                        resume = it[Case.resume],
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

    // fun getPersonVotes(personId: Int): List<VoteInfoDTO> =
    //     dbQuery {
    //         (Case innerJoin CaseStage innerJoin VoteSession innerJoin Vote innerJoin Person innerJoin VoteType)
    //             .slice(VoteSession.id, VoteSession.voteResult, VoteSession.timestamp, Case.titleShort, Case.resume, Case.conclusion, VoteType.voteType)
    //             .select { Person.id eq personId }
    //             .orderBy(VoteSession.timestamp to SortOrder.DESC)
    //             .map {
    //                 VoteInfoDTO(
    //                     id = it[VoteSession.id],
    //                     titleShort = it[Case.titleShort],
    //                     resume = it[Case.resume],
    //                     conclusion = it[Case.conclusion],
    //                     voteResult = it[VoteSession.voteResult],
    //                     vote = it[VoteType.voteType],
    //                     timestamp = it[VoteSession.timestamp].toString(),
    //                 )
    //             }
    //     }
}
