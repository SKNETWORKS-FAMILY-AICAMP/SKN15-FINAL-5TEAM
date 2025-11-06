FROM ankane/pgvector:latest

# PostgreSQL with pgvector extension for KIME Chat
LABEL maintainer="KIME Chat"
LABEL description="PostgreSQL 15 with pgvector extension for vector similarity search"

# Set environment variables
ENV POSTGRES_INITDB_ARGS="--encoding=UTF-8 --locale=C"

# Copy initialization scripts
COPY init/*.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD pg_isready -U ${POSTGRES_USER:-kime} -d ${POSTGRES_DB:-kimedb} || exit 1
