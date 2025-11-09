#!/bin/bash

# RDS 마이그레이션 실행 스크립트
# 사용법: ./run_migrations.sh [environment]
# 예시: ./run_migrations.sh production

set -e  # 에러 발생 시 즉시 중단

# 환경 설정
ENV=${1:-production}
echo "=========================================="
echo "RDS Migration Script"
echo "Environment: $ENV"
echo "=========================================="

# .env 파일 로드
if [ "$ENV" = "production" ]; then
    ENV_FILE="../.env.production"
else
    ENV_FILE="../.env.local"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found!"
    exit 1
fi

echo "Loading environment from $ENV_FILE..."
export $(grep -v '^#' $ENV_FILE | xargs)

# DB 연결 정보 확인
echo ""
echo "Database Connection Info:"
echo "- Host: $DB_HOST"
echo "- Port: $DB_PORT"
echo "- Database: $DB_NAME"
echo "- User: $DB_USER"
echo ""

# PostgreSQL 접속 확인
echo "Testing database connection..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Database connection successful!"
else
    echo "❌ Failed to connect to database. Please check your credentials."
    exit 1
fi

# 마이그레이션 디렉토리
MIGRATION_DIR="../database/migrations"

if [ ! -d "$MIGRATION_DIR" ]; then
    echo "❌ Error: Migration directory not found: $MIGRATION_DIR"
    exit 1
fi

# 마이그레이션 파일 목록 (순서대로)
MIGRATIONS=(
    "001_initial_schema.sql"
    "002_add_embeddings.sql"
    "003_users_table.sql"
    "004_password_reset_tokens.sql"
    "005_conversation_summary.sql"
    "006_entities_and_relationships.sql"
    "007_user_memories.sql"
    "008_training_log_enhancements.sql"
    "009_scenarios_table.sql"
    "010_user_progress.sql"
    "011_user_scenario_progress.sql"
)

echo ""
echo "=========================================="
echo "Running Migrations..."
echo "=========================================="
echo ""

# 각 마이그레이션 실행
for migration in "${MIGRATIONS[@]}"; do
    migration_file="$MIGRATION_DIR/$migration"

    if [ ! -f "$migration_file" ]; then
        echo "⚠️  Warning: Migration file not found: $migration"
        continue
    fi

    echo "📄 Running: $migration"

    # 마이그레이션 실행
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration_file"

    if [ $? -eq 0 ]; then
        echo "   ✅ Success"
    else
        echo "   ❌ Failed"
        echo ""
        echo "Migration failed at: $migration"
        echo "Please check the error messages above."
        exit 1
    fi

    echo ""
done

echo "=========================================="
echo "✅ All migrations completed successfully!"
echo "=========================================="
echo ""

# 테이블 목록 확인
echo "Verifying tables..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt *"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt public.*"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt *"

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "Next Steps:"
echo "1. Run seed_scenarios.py to load scenario data"
echo "2. Deploy backend to AWS EC2"
echo "=========================================="
