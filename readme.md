

query: 

RESTORE DATABASE ODA
FROM DISK = '/var/opt/mssql/backup/oda.bak'
WITH MOVE 'ODA' TO '/var/opt/mssql/data/ODA.mdf',
MOVE 'ODA_log' TO '/var/opt/mssql/data/ODA_log.ldf',
REPLACE,
STATS=10


docker commands:

docker run -e 'ACCEPT_EULA=Y' -e 'SA_PASSWORD=DefaultStrong!Passw0rd' \
  -p 1433:1433 --name mssql -m 3G -d mcr.microsoft.com/azure-sql-edge


docker cp oda.bak mssql:/var/opt/mssql/backup


Example:

B 177 (borger forslag) about weapon's trade.

Finding specific vote that lead to rejecting the proposal (I assume you only need the sagstrinid really):
SELECT * FROM dbo.Afstemning
WHERE nummer = 512 AND sagstrinid = 265952
ORDER BY opdateringsdato DESC

Findin the Sag
SELECT * FROM dbo.Sag
WHERE titelkort LIKE '%Om at Danmark skal stoppe%'

Finding all Borgerforslag sager
SELECT * FROM dbo.Sag
WHERE nummer LIKE 'B %'
ORDER BY nummernumerisk + 0 DESC

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