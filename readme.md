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

## Questions from politicians to politicians and the answers
Queries.sql contains a query to get all the questions posed by politicians either through what's called paragraph 20 questions or through udvalg or samråd (not sure what these are called in English, but they are essentially smaller gatherings where politicians can ask questions to different ministers and party representatives - typically the opposition attempting to get answers from the government). Unfortunately, the answers themselves are not contained in the database, but it provides a link to pdf files containing both the question and the answer, so we would need a way to scrape the pdf files. Below is an example output of the query found in queries.sql

| titel | spørgsmålstitel | dato | filurl |
|----------|----------|----------|----------|
| Svar på spm. nr. S 725: Er ministeren enig i vurderingen af, at grønlandske mineralprojekter vækker interesse i udlandet, og kan ministeren i denne forbindelse garantere, at der ikke er foregået NSA-aflytninger eller aflytninger fra andre interessenter af grønlandske politikere og embedsfolk? | Er ministeren enig i vurderingen af, at grønlandske mineralprojekter vækker interesse i udlandet, og kan ministeren i denne forbindelse garantere, at der ikke er foregået NSA-aflytninger eller aflytninger fra andre interessenter af grønlandske politikere og embedsfolk? | 2014-01-09 00.00.00.000 | https://www.ft.dk/samling/20131/spoergsmaal/S725/svar/1102491/1320529.pdf | 
| Svar på spm. nr. S 726: Hvad agter ministeren at foretage sig, så kostskoler m.m. fortsat har mulighed for at bortvise elever, der har indtaget ulovlige stoffer, og som ikke er synligt påvirkede? | Hvad agter ministeren at foretage sig, så kostskoler m.m. fortsat har mulighed for at bortvise elever, der har indtaget ulovlige stoffer, og som ikke er synligt påvirkede? | 2014-01-08 00.00.00.0000 | https://www.ft.dk/samling/20131/spoergsmaal/S726/svar/1102053/1319828.pdf |

As for debates/question sessions taking place in the big parliament hall, this doesn't appear to exist in the database. Here, you would rather find information via: https://www.ft.dk/da/dokumenter/dokumentlister/referater where each link would take you to a summary for a given session including all questions and answers given. Again some sort of scraping is probably required.

## Vector embedding test
The `vectors` repository contains everything to set up a vector embedding generation and search environment. Solr is the search engine that is capable of indexing data based on vector embeddings. The `indexer` is the test container that generates embeddings on some test data and commits it to the solr container (see the test data in `index.py`). Afterwards, the `api` container can send queries to `solr`. Moving forward, the ftdata backend should then be responsible for the requests being send to `api`. For now, testing is done manually with commands such as below. To run everything use `make run`.

Testing solr directly: 
`curl "http://localhost:8983/solr/vector_test/select?q=*:*&wt=json"`
`curl "http://localhost:8983/solr/vector_test/select?q=title:shoes&wt=json"`

Testing solr through the api:
`curl -X POST http://localhost:8000/search -H "Content-Type: application/json" -d '{"query": "running shoes"}'`