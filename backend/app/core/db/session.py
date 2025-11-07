"""
Database Session Management
AsyncSession 생성 및 의존성 주입
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import get_settings

settings = get_settings()

# ============================================================
# Async Engine 생성
# ============================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # SQL 로그 출력 (개발 환경에서만)
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 연결 체크
)

# ============================================================
# Async Session Factory
# ============================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================
# FastAPI Dependency
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입용 DB 세션

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================
# 수동 세션 컨텍스트 (테스트용)
# ============================================================

async def get_db_context():
    """
    수동으로 세션을 관리할 때 사용

    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
