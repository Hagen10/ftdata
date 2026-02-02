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

data class UserAnswerDTO(
    val caseId: Int,
    val vote: String
)

data class PersonResultDTO(
    val firstName: String?,
    val lastName: String?,
    val percentage: String?,
)

data class CaseVoteDTO(
    val personId: Int,
    val voteType: String?,
)

@Service
class QuizService {
    fun getPrompts(): List<PromptDTO> =
        dbQuery {
            (Case innerJoin CaseTopic)
                .slice(Case.id, Case.title, Case.titleShort, Case.resume)
                .select { CaseTopic.caseTopicId eq 84443 } // 84443 = Borgerforslag
                .map {
                    PromptDTO(
                        id = it[Case.id],
                        title = it[Case.title],
                        titleShort = it[Case.titleShort],
                        resume = it[Case.resume],
                    )
                }
        }

    fun getCaseVotes(caseId: Int): List<CaseVoteDTO> =
        dbQuery {
            (Vote innerJoin VoteSession innerJoin CaseStage innerJoin VoteType)
                .slice(Vote.personId, VoteType.voteType)
                .select { CaseStage.id eq caseId }
                .map {
                    CaseVoteDTO(
                        personId = it[Vote.id],
                        voteType = it[VoteType.voteType],
                    )
                }
        }
}
