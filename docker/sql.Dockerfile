# Use the official Microsoft SQL Server image
FROM mcr.microsoft.com/mssql/server:2022-latest

# Set environment variables
ENV ACCEPT_EULA=Y \
    MSSQL_PID=Developer \
    SA_PASSWORD=YourStrong!Passw0rd

# Allow arguments for build-time customization
ARG BAK_URL
ARG BAK_USER
ARG BAK_PASS
ARG DB_NAME=MyDatabase

USER root

# Create directories for backup and restore scripts
RUN mkdir -p /var/opt/mssql/backup /docker-entrypoint-initdb.d

# Install wget for downloading the backup file
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Download the .bak file using credentials
# The credentials will be embedded in the image (not ideal for production, better to pass via secrets)
RUN wget --user=${BAK_USER} --password=${BAK_PASS} -O /var/opt/mssql/backup/backup.bak ${BAK_URL}

# Copy the restore script into the container
COPY docker/restore-database.sh /docker-entrypoint-initdb.d/restore-database.sh
RUN chmod +x /docker-entrypoint-initdb.d/restore-database.sh

# Expose the SQL Server port
EXPOSE 1433

# Start SQL Server and run the restore script
CMD /opt/mssql/bin/sqlservr & sleep 30 && /docker-entrypoint-initdb.d/restore-database.sh && tail -f /dev/null
