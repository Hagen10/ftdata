# To do
- What could be nice is to somehow compare the newest downloaded database with the previous one to ensure that data isn't all of a sudden lost.
- authentication with perhaps Oauth2
- dockerize kotlin application
- harden security wise. Should the communication between frontend and backend be mtls? Likely. Also, the application.yml file should be fed the password instead of hardcoding. Applies anywhere where the password is appearing at present.
- create a new repo for the frontend written in Typescript
- testing?

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