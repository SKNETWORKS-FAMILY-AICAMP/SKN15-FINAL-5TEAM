"""
Entity Model (기존 DB 구조)
"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.core.db.base import Base
from datetime import datetime


class Entity(Base):
    """
    엔티티 (캐릭터, 장소, 이벤트, 아이템, 스킬)
    """
    __tablename__ = "entities"

    entity_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_name = Column(String(255), nullable=False)
    canonical_name = Column(String(255))
    description = Column(Text)
    properties = Column(JSONB, default={})
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small
    importance_score = Column(Float, default=0.5)
    community_id = Column(Integer)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('entity_type', 'canonical_name'),
        CheckConstraint("entity_type IN ('character', 'location', 'event', 'item', 'skill')", name='valid_entity_type'),
        CheckConstraint('importance_score >= 0.0 AND importance_score <= 1.0', name='valid_importance'),
        Index('idx_entities_type', 'entity_type'),
        Index('idx_entities_canonical_name', 'canonical_name'),
        Index('idx_entities_importance', 'importance_score'),
        Index('idx_entities_mention_count', 'mention_count'),
        Index('idx_entities_community', 'community_id'),
        {"schema": "knowledge"}
    )

    def __repr__(self):
        return f"<Entity(id={self.entity_id}, type={self.entity_type}, name={self.entity_name})>"
