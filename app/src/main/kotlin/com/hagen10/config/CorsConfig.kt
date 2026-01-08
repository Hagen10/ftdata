package com.hagen10.config

import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.CorsRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class CorsConfig : WebMvcConfigurer {

    override fun addCorsMappings(registry: CorsRegistry) {
        registry.addMapping("/**")
            .allowedOrigins(
                "http://localhost:4200",          // dev
                "https://app.hagen10.com"         // prod (future)
            )
            .allowedMethods("GET", "OPTIONS")
            .allowedHeaders("*")
            .maxAge(3600)
    }
}
