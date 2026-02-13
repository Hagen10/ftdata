package com.hagen10.db

import org.springframework.stereotype.Service

@Service
class ScoringService(
    private val QuizService: QuizService,
    private val PoliticianService: PoliticianService
) {
    // A match (e.g. both votes for) gives a "1" any other scenario (including the politician being absent) will give 0
    fun score(
        userVote: String,
        politicianVote: String
    ): Int = if (userVote == politicianVote) 1 else 0

    fun calculateScores(userVotes: List<UserAnswerDTO>): List<PoliticianScoreDTO> {
        val caseIds = userVotes.map { it.caseId }

        var caseCount = caseIds.size
        // Avoiding division with zero
        if (caseCount == 0) caseCount = 1

        val politicianVotes = QuizService.getAllPoliticianVotes(caseIds)

        val scores = mutableMapOf<Int, Double>()

        for ((politicianId, votesBySession) in politicianVotes) {
            var score = 0

            for (userVote in userVotes) {
                val politicianVote = votesBySession[userVote.caseId]
                    ?: continue // politician didn't vote, so go to next vote session

                score += score(userVote.vote, politicianVote)
            }
            // score / caseCount is multiplied with 1000 to turn it into percent and time it by 10 which is part of rounding to one decimal.
            scores[politicianId] = kotlin.math.round(score.toDouble() / caseCount * 1000) / 10
        }

        val people = PoliticianService.getPeopleByIds(scores.keys.toList())

        return scores.map { (personId, score) ->
            val person = people[personId]
            PoliticianScoreDTO(
                personId = personId,
                firstName = person?.firstName ?: "",
                lastName = person?.lastName ?: "",
                score = score
            )
        }.sortedByDescending { it.score }
    }
}
