package com.example.db

import com.example.config.dbQuery
import org.jetbrains.exposed.sql.select
import org.jetbrains.exposed.sql.selectAll
import org.jetbrains.exposed.sql.SortOrder
import org.springframework.stereotype.Service

data class PolDTO(
    val id: Int,
    val typeId: Int,
    val firstName: String?,
    val lastName: String?,
)

data class VoteDTO(
    val id: Int,
    val titleShort: String?,
    val resume: String?,
    val conclusion: String?,
    val vote: String,
    val timestamp: String?,
)

@Service
class PolService {
    fun getAllPols(): List<PolDTO> =
        dbQuery {
            Pols
                .slice(Pols.id, Pols.typeId, Pols.firstName, Pols.lastName)
                .select { Pols.typeId eq 5 } // 5 = Politiker
                .orderBy(Pols.lastName)
                .map {
                    PolDTO(
                        id = it[Pols.id],
                        typeId = it[Pols.typeId],
                        firstName = it[Pols.firstName],
                        lastName = it[Pols.lastName],
                    )
                }
        }

    fun getPolInfo(polId: Int): PolDTO? =
        dbQuery {
            Pols
                .slice(Pols.id, Pols.typeId, Pols.firstName, Pols.lastName)
                .select { Pols.id eq polId }
                .mapNotNull {
                    PolDTO(
                        id = it[Pols.id],
                        typeId = it[Pols.typeId],
                        firstName = it[Pols.firstName],
                        lastName = it[Pols.lastName],
                    )
                }
                .singleOrNull()
        }

    fun getPolVotes(polId: Int): List<VoteDTO> =
        dbQuery {
            (Case innerJoin CaseStage innerJoin Voting innerJoin Vote innerJoin Pols innerJoin VoteType)
                .slice(Voting.id, Voting.timestamp, Case.titleShort, Case.resume, Case.conclusion, VoteType.voteType)
                .select { Pols.id eq polId }
                .orderBy(Voting.timestamp to SortOrder.DESC)
                .map {
                    VoteDTO(
                        id = it[Voting.id],
                        titleShort = it[Case.titleShort],
                        resume = it[Case.resume],
                        conclusion = it[Case.conclusion],
                        vote = it[VoteType.voteType],
                        timestamp = it[Voting.timestamp].toString(),
                    )
                }
        }
}
