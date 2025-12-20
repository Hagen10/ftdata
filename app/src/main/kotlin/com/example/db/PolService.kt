package com.example.db

import com.example.config.dbQuery
import org.jetbrains.exposed.sql.selectAll
import org.springframework.stereotype.Service

data class PolDTO(val id: Int, val typeid: Int, val fornavn: String?, val efternavn: String?)

@Service
class PolService {

    fun getAllPols(): List<PolDTO> = dbQuery {
        Pols
            .slice(Pols.id, Pols.typeid, Pols.fornavn, Pols.efternavn)
            .selectAll().map {
            PolDTO(
                id = it[Pols.id],
                typeid = it[Pols.typeid],
                fornavn = it[Pols.fornavn],
                efternavn = it[Pols.efternavn]
            )
        }
    }
}
