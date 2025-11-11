"""
UserMemory 모델
"""
from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class UserMemory(Base):
    """사용자 메모리 (장기 기억)"""
    __tablename__ = "user_memories"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    memory_text = Column(Text, nullable=False)
    memory_type = Column(String(50))  # preference, fact, goal, etc.
    importance = Column(Float, default=0.5)

    embedding = Column(Vector(1536))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_accessed = Column(TIMESTAMP, default=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # Relationships
    session = relationship("GameSession")
    user = relationship("User")
