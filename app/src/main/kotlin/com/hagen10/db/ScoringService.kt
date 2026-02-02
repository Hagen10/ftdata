package com.hagen10.db

import org.springframework.stereotype.Service

@Service
class ScoringService(
    private val QuizService: QuizService
) {
    // A match (e.g. both votes for) gives a "1" any other scenario (including the politician being absent) will give 0
    fun score(
        userVote: String,
        politicianVote: String
    ): Int = if (userVote == politicianVote) 1 else 0

    fun calculateScores(userVotes: List<UserAnswerDTO>): List<PoliticianScoreDTO> {
        val caseIds = userVotes.map { it.caseId }

        val politicianVotes = QuizService.getAllPoliticianVotes(caseIds)

        val scores = mutableMapOf<Int, Int>()

        for ((politicianId, votesBySession) in politicianVotes) {
            var score = 0

            for (userVote in userVotes) {
                val politicianVote = votesBySession[userVote.caseId]
                    ?: continue // politician didn't vote, so go to next vote session

                score += score(userVote.vote, politicianVote)
            }

            scores[politicianId] = score
        }

        return scores.map { (personId, score) -> PoliticianScoreDTO(personId = personId, score = score)}
                     .sortedByDescending { it.score }
    }
}
