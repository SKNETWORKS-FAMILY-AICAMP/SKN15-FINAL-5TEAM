#!/bin/bash
# Docker Entrypoint Script for KIME Backend
# 안전하게 마이그레이션을 실행하고 서버를 시작합니다.

set -e  # 에러 발생 시 스크립트 중단

echo "============================================================"
echo "🚀 KIME Backend Starting..."
echo "============================================================"

# 1. PostgreSQL 연결 대기 (최대 30초)
echo "⏳ Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

# Build sync DATABASE_URL for connection check (psycopg2 instead of asyncpg)
SYNC_DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

while ! python -c "
import sys
from sqlalchemy import create_engine, text
try:
    engine = create_engine('${SYNC_DB_URL}', pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ PostgreSQL is ready!')
    sys.exit(0)
except Exception as e:
    print(f'⏳ PostgreSQL not ready yet: {e}')
    sys.exit(1)
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ PostgreSQL connection timeout after ${MAX_RETRIES} attempts"
        exit 1
    fi
    echo "   Attempt ${RETRY_COUNT}/${MAX_RETRIES}..."
    sleep 1
done

echo ""

# 2. Alembic 마이그레이션 자동 실행 (DISABLED - using SQL init scripts instead)
echo "📦 Skipping Alembic migrations..."
echo "   - Using PostgreSQL init scripts (database/postgres/init/*.sql)"
echo "   - Alembic is disabled to prevent duplicate table creation"
echo ""

# Alembic 마이그레이션 실행 (주석 처리)
# if alembic upgrade head; then
#     echo "✅ Database migrations completed successfully"
# else
#     echo "⚠️  Migration failed, but continuing to start server..."
#     echo "   (Server will start, but some features may not work)"
# fi

echo ""

# 3. 초기 데이터 임포트 (선택적 - 개발 환경에서만)
if [ "${ENVIRONMENT}" = "development" ]; then
    echo "🔧 Development mode: Checking if initial data import is needed..."

    # scenarios 테이블에 데이터가 있는지 확인
    HAS_SCENARIOS=$(python -c "
from sqlalchemy import create_engine, text
engine = create_engine('${SYNC_DB_URL}')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM scenarios'))
    count = result.scalar()
    print(count)
" 2>/dev/null || echo "0")

    if [ "$HAS_SCENARIOS" = "0" ]; then
        echo "   📊 No scenarios found, importing initial content data..."
        if python scripts/import_content_data.py 2>&1 | grep -q "SUCCESS"; then
            echo "   ✅ Initial content data imported"
        else
            echo "   ⚠️  Content import skipped or failed (non-critical)"
        fi
    else
        echo "   ✓ Scenarios already exist (count: $HAS_SCENARIOS), skipping import"
    fi
fi

echo ""

# 4. 서버 시작
echo "============================================================"
echo "🎯 Starting FastAPI Server..."
echo "============================================================"
echo "   Environment: ${ENVIRONMENT}"
echo "   Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "   LLM Enabled: ${USE_LLM}"
echo "   LangGraph Enabled: ${USE_LANGGRAPH}"
echo "============================================================"
echo ""

# Uvicorn으로 서버 시작
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
