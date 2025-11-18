"""
UserMemory 모델 - 실제 DB 스키마에 정확히 일치
"""
from sqlalchemy import Column, String, Text, Float, Integer, ForeignKey, BigInteger, DateTime, Boolean, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from app.core.db.base import Base


class UserMemory(Base):
    """사용자 메모리 (장기 기억)

    실제 DB 스키마:
    - PK: id (bigint, auto-increment)
    - memory_key: 메모리 키 (VARCHAR(100))
    - memory_value: 실제 메모리 내용 (TEXT)
    - importance: 중요도 (FLOAT, 0.0-1.0)
    - memory_type: 메모리 타입 (fact, event, relationship, preference, etc.)
    """
    __tablename__ = "user_memories"
    __table_args__ = (
        CheckConstraint('importance >= 0.0 AND importance <= 1.0', name='user_memories_importance_check'),
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='user_memories_confidence_check'),
        {"schema": "knowledge"}
    )

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="CASCADE"), nullable=False)

    # Memory Content
    memory_key = Column(String(100), nullable=False)  # 메모리 키 (예: "favorite_food", "hometown")
    memory_value = Column(Text, nullable=False)       # 실제 값 (예: "라면", "부산")
    memory_type = Column(String(50), nullable=True, default='fact')  # fact, event, relationship, preference

    # Metadata
    context = Column(JSONB, nullable=True)  # 추가 컨텍스트 정보
    importance = Column(Float, nullable=True, default=0.5)
    confidence = Column(Float, nullable=True)
    tags = Column(ARRAY(String(50)), nullable=True)

    # Embeddings
    embedding = Column(Vector(1536), nullable=True)

    # Scenario Tracking (v2: LTM은 free-talk 전용)
    scenario_id = Column(String(100), nullable=False, default='free-talk', comment="시나리오 ID (LTM은 free-talk만)")

    # Session Tracking
    source_session_id = Column(UUID(as_uuid=True), nullable=True)
    related_session_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    related_entity_ids = Column(ARRAY(Integer), nullable=True, default=[])

    # Access Tracking
    access_count = Column(Integer, nullable=True, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    # Lifecycle
    is_active = Column(Boolean, nullable=True, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
