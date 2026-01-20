# commands
- Check dependencies: ´gradle dependencyUpdates´

# Notes
- HikariCP: is a connection pool framework for handling multiple connections to a database at once rather than establishing a new TCP connection every time the database needs to be queried (slow)
- Exposed: is a Kotlin-first framework specifically for SQL to make it type safe and avoid raw query strings
- Spring Boot: is a framework for building production-ready backend applications on the JVM

example of logging:
// log.info(
        //     "Hikari config - jdbcUrl={}, user={}, poolSize={}",
        //     dataSource.jdbcUrl,
        //     dataSource.username,
        //     dataSource.maximumPoolSize
        // )