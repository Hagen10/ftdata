package com.hagen10.db

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
class PoliticianController(
    private val PoliticianService: PoliticianService,
) {
    @GetMapping("/politicians")
    fun getAllPeople(): List<PersonDTO> = PoliticianService.getAllPeople()

    @GetMapping("/politicianInfo/{id}")
    fun getPersonInfo(
        @PathVariable id: Int,
    ): PersonDTO? = PoliticianService.getPersonInfo(id)

    @GetMapping("/politicianVotes/{id}")
    fun getPersonVotes(
        @PathVariable id: Int,
    ): List<VoteInfoDTO> = PoliticianService.getPersonVotes(id)
}
