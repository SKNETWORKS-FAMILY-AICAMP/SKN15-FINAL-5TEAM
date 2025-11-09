#!/bin/bash
# ============================================================
# Database Backup Script
# ============================================================
# Purpose: Export PostgreSQL database data for team sharing
# Usage: ./scripts/backup_database.sh [output_file]
# ============================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default output file
OUTPUT_FILE="${1:-database_backup_$(date +%Y%m%d_%H%M%S).sql}"

echo -e "${YELLOW}🔄 Starting database backup...${NC}"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Check if Docker container is running
CONTAINER_NAME="kime-postgres"
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${RED}❌ Error: PostgreSQL container is not running${NC}"
    echo "Please start containers with: docker-compose up -d"
    exit 1
fi

# Create backups directory
mkdir -p backups

# Perform backup
echo -e "${YELLOW}📦 Backing up database: ${DB_NAME}${NC}"
docker exec -t $CONTAINER_NAME pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > "backups/${OUTPUT_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup successful!${NC}"
    echo -e "${GREEN}📁 File: backups/${OUTPUT_FILE}${NC}"
    echo -e "${GREEN}📊 Size: $(du -h "backups/${OUTPUT_FILE}" | cut -f1)${NC}"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}💡 To share this backup with team members:${NC}"
echo "   1. Share the file: backups/${OUTPUT_FILE}"
echo "   2. Team members can restore using: ./scripts/restore_database.sh backups/${OUTPUT_FILE}"
