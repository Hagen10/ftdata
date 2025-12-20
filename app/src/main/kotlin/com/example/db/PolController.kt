package com.example.db

import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api/politicians")
class PolController(
    private val PolService: PolService
) {

    @GetMapping
    fun getPols(): List<PolDTO> =
        PolService.getAllPols()
}
