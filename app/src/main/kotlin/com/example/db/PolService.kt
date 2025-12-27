package com.example.db

import com.example.config.dbQuery
import org.jetbrains.exposed.sql.select
import org.jetbrains.exposed.sql.selectAll
import org.springframework.stereotype.Service

data class PolDTO(
    val id: Int,
    val typeId: Int,
    val firstName: String?,
    val lastName: String?,
)

data class VotesDTO(
    val titleShort: String?,
    val resume: String?,
    val votingConclusion: String?,
    val vote: String,
)

@Service
class PolService {
    fun getAllPols(): List<PolDTO> =
        dbQuery {
            Pols
                .slice(Pols.id, Pols.typeId, Pols.firstName, Pols.lastName)
                .selectAll()
                .map {
                    PolDTO(
                        id = it[Pols.id],
                        typeId = it[Pols.typeId],
                        firstName = it[Pols.firstName],
                        lastName = it[Pols.lastName],
                    )
                }
        }

    fun getPolVotes(polId: Int): List<VotesDTO> =
        dbQuery {
            (Case innerJoin CaseStage innerJoin Voting innerJoin Vote innerJoin Pols innerJoin VoteType)
                .slice(Case.titleShort, Case.resume, Case.votingConclusion, VoteType.voteType)
                .select { Pols.id eq polId }
                .map {
                    VotesDTO(
                        titleShort = it[Case.titleShort],
                        resume = it[Case.resume],
                        votingConclusion = it[Case.votingConclusion],
                        vote = it[VoteType.voteType],
                    )
                }
        }
}
