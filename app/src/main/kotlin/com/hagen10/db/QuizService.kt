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
    val vote: String,
)

data class PoliticianScoreDTO(
    val personId: Int,
    val score: Double,
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

    fun getAllPoliticianVotes(caseIds: List<Int>): Map<Int, Map<Int, String>> =
        dbQuery {
            (Vote innerJoin VoteSession innerJoin CaseStage innerJoin VoteType)
                .slice(CaseStage.caseId, Vote.personId, VoteType.voteType)
                .select { CaseStage.caseId inList caseIds }
                .groupBy { it[Vote.personId] }
                .mapValues { (_, rows) -> 
                    rows.associate { row ->
                        val caseId = row[CaseStage.caseId]
                        // Creating a map with caseId as key and the politician vote as value
                        caseId to row[VoteType.voteType]
                    }
                }
        }
}
