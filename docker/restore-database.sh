#!/bin/bash
set -e

echo "Restoring database from backup..."

# Wait until SQL Server is ready to accept connections
echo "Waiting for SQL Server to start..."
sleep 15

# Restore the database
/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$SA_PASSWORD" -Q "
RESTORE DATABASE [$DB_NAME]
FROM DISK = N'/var/opt/mssql/backup/backup.bak'
WITH MOVE '$DB_NAME' TO '/var/opt/mssql/data/$DB_NAME.mdf',
     MOVE '${DB_NAME}_log' TO '/var/opt/mssql/data/${DB_NAME}_log.ldf',
     REPLACE;
"

echo "Database [$DB_NAME] restored successfully!"
