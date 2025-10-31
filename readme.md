

query: 

RESTORE DATABASE ODA
FROM DISK = '/var/opt/mssql/backup/oda.bak'
WITH MOVE 'ODA' TO '/var/opt/mssql/data/ODA.mdf',
MOVE 'ODA_log' TO '/var/opt/mssql/data/ODA_log.ldf',
REPLACE,
STATS=10


docker commands:

docker run -e 'ACCEPT_EULA=Y' -e 'SA_PASSWORD=YourStrong!Passw0rd' \
  -p 1433:1433 --name mssql -m 3G -d mcr.microsoft.com/azure-sql-edge


docker cp oda.bak mssql:/var/opt/mssql/backup

