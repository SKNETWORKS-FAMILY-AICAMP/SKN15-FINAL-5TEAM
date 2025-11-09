#!/bin/bash
# ============================================================
# Database Restore Script
# ============================================================
# Purpose: Import PostgreSQL database data from backup
# Usage: ./scripts/restore_database.sh <backup_file>
# ============================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Backup file not specified${NC}"
    echo "Usage: ./scripts/restore_database.sh <backup_file>"
    echo "Example: ./scripts/restore_database.sh backups/database_backup_20250109.sql"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}🔄 Starting database restore...${NC}"

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

# Warning prompt
echo -e "${YELLOW}⚠️  WARNING: This will replace all data in database: ${DB_NAME}${NC}"
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Perform restore
echo -e "${YELLOW}📥 Restoring database from: ${BACKUP_FILE}${NC}"
cat "$BACKUP_FILE" | docker exec -i $CONTAINER_NAME psql \
    -U "${DB_USER}" \
    -d "${DB_NAME}"

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Restore successful!${NC}"
    echo -e "${GREEN}📁 Data restored from: ${BACKUP_FILE}${NC}"
else
    echo -e "${RED}❌ Restore failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo "   1. Restart backend container: docker-compose restart backend"
echo "   2. Clear Redis cache: docker-compose exec redis redis-cli FLUSHALL"
