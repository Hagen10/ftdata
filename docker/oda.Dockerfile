# Use the azure sql edge because it supports arm. the mssql images do not.
FROM mcr.microsoft.com/azure-sql-edge:latest

USER root

# Set environment variables
ENV ACCEPT_EULA=Y \
    MSSQL_PID=Developer \
    SA_PASSWORD=YourStrong!Passw0rd

# Allow arguments for build-time customization
ARG BAK_URL
ARG BAK_USER
ARG BAK_PASS

# add sqlcmd from https://github.com/microsoft/go-sqlcmd
# we add this to /opt/mssql-tools/bin which completely overrides the
# sqlcmd from the base image. Read up on why we do this here:
# https://github.com/microsoft/go-sqlcmd/discussions/501#discussion-6088877
WORKDIR /opt/mssql-tools/bin
ENV GOSQLCMD_VERSION=v1.5.0
ARG TARGETPLATFORM
RUN case ${TARGETPLATFORM} in \
    "linux/amd64")  GOSQLCMD_ARCH=amd64 ;; \
    "linux/arm64")  GOSQLCMD_ARCH=arm64 ;; \
    *) echo "Unsupported platform: ${TARGETPLATFORM}"; exit 1 ;; \
    esac \
 && wget https://github.com/microsoft/go-sqlcmd/releases/download/${GOSQLCMD_VERSION}/sqlcmd-${GOSQLCMD_VERSION}-linux-${GOSQLCMD_ARCH}.tar.bz2 \
 && tar -xjf sqlcmd-${GOSQLCMD_VERSION}-linux-${GOSQLCMD_ARCH}.tar.bz2

WORKDIR /app

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
