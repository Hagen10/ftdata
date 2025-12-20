

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

