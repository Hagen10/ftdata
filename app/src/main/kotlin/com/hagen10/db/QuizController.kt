package com.hagen10.db

import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.concurrent.CopyOnWriteArrayList

@RestController
@RequestMapping("/api")
class QuizController(
    private val QuizService: QuizService,
) {
    // Thread-safe in-memory store
    private val results = CopyOnWriteArrayList<PersonResultDTO>()

    @GetMapping("/quiz")
    fun startQuiz(): List<PromptDTO> = QuizService.getPrompts()

    @PostMapping("/quiz/answer")
    fun processAnswer(
        @RequestBody request: UserAnswerDTO,
    ): ResponseEntity<Void> {
        //PoliticianService.getPersonInfo(id)

        return ResponseEntity.ok().build()
    }

    @PostMapping("/quiz/finish")
    fun finishQuiz(
        @RequestBody request: UserAnswerDTO,
    ): List<PersonResultDTO> {
        //PoliticianService.getPersonInfo(id)

        return results
    }
}
