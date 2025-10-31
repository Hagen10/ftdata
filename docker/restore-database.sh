#!/bin/bash
set -e

DB_NAME="ODA"

echo "Restoring database from backup..."

# Wait until SQL Server is ready to accept connections
echo "Waiting for SQL Server to start..."
sleep 15

# Restore the database
/opt/mssql-tools/bin/sqlcmd -S 127.0.0.1 -U SA -P "$SA_PASSWORD" -Q "
RESTORE DATABASE [${DB_NAME}]
FROM DISK = N'/var/opt/mssql/backup/backup.bak'
WITH MOVE '${DB_NAME}' TO '/var/opt/mssql/data/${DB_NAME}.mdf',
     MOVE '${DB_NAME}_log' TO '/var/opt/mssql/data/${DB_NAME}_log.ldf',
     REPLACE,
     STATS=10;
"

echo "Database [${DB_NAME}] restored successfully!"
