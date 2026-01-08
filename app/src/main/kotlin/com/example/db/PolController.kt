package com.example.db

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
class PolController(
    private val PolService: PolService,
) {
    @GetMapping("/politicians")
    fun getAllPols(): List<PolDTO> = PolService.getAllPols()

    @GetMapping("/politicianInfo/{id}")
    fun getPolInfo(
        @PathVariable id: Int,
    ): PolDTO? = PolService.getPolInfo(id)

    @GetMapping("/politicianVotes/{id}")
    fun getPolVotes(
        @PathVariable id: Int,
    ): List<VoteDTO> = PolService.getPolVotes(id)
}
