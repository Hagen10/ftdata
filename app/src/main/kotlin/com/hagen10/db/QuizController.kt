package com.hagen10.db

import org.slf4j.LoggerFactory
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
class QuizController(
    private val QuizService: QuizService,
    private val ScoringService: ScoringService,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @GetMapping("/quiz")
    fun startQuiz(): List<PromptDTO> = QuizService.getPrompts()

    @PostMapping("/quiz/finish")
    fun finishQuiz(
        @RequestBody request: List<UserAnswerDTO>,
    ): List<PoliticianScoreDTO> {
        log.info("Received finish quiz request: $request")

        return ScoringService.calculateScores(request)
    }
}
