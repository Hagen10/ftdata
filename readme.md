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


Testing post api:
curl -i -X POST http://localhost:8080/api/quiz/answer -H "Content-Type: application/json" -d '{"caseId":75724,"vote":"For"}'

Finishing quiz:
curl -i -X POST http://localhost:8080/api/quiz/finish -H "Content-Type: application/json" -d '[{"caseId":75724,"vote":"For"},{"caseId":78379,"vote":"Imod"},{"caseId":77413,"vote":"For"},{"caseId":78735,"vote":"For"},{"caseId":77414,"vote":"For"},{"caseId":78863,"vote":"For"},{"caseId":84990,"vote":"Imod"},{"caseId":85022,"vote":"For"},{"caseId":86509,"vote":"For"},{"caseId":86904,"vote":"Imod"}]'

which should give the results:
"[{"personId":55,"score":4},{"personId":199,"score":3},{"personId":263,"score":3},{"personId":119,"score":3},{"personId":78,"score":3},{"personId":59,"score":3},{"personId":112,"score":3}..."

We need to filter by 4 year periods I reckon because if the quiz includes questions for multiple governments, I imagine that the politicians who were elected both times have an easier time getting higher scores than those who have been absent for 4 years, that is if we think that an absence due to not being part of the parliament should be considered as a different vote than the users.

the individual answers should just be collected in rails and then send as a list when clicking finish.

Now we are only sending politician ids, but rails already knows the names of the politicians. So it could just match them with the incoming results, or maybe the results should be extended...