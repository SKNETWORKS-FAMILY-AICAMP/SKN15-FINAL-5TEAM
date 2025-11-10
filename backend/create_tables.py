"""
임시 스크립트: SQLAlchemy 모델에서 테이블 생성
"""
import asyncio
from app.core.database import engine
from app.core.db.base import Base

# Import all models to register them with Base
from app.features.auth.models import User, PasswordResetToken
from app.features.sessions.models import Session
from app.features.scenarios.models import ScenarioComment, ScenarioLike, CommentLike
from app.features.galleries.models import GalleryImage


async def create_tables():
    """Create all tables"""
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    print("✅ All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
