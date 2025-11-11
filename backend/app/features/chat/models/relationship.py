"""
Relationship Model (기존 DB 구조 - entity_relationships)
"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.core.db.base import Base
from datetime import datetime


class Relationship(Base):
    """
    엔티티 간 관계
    """
    __tablename__ = "entity_relationships"

    relationship_id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity_id = Column(Integer, ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    strength = Column(Float, default=0.5)
    context = Column(Text)
    properties = Column(JSONB, default={})
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('source_entity_id', 'target_entity_id', 'relationship_type'),
        CheckConstraint('strength >= 0.0 AND strength <= 1.0', name='valid_strength'),
        Index('idx_relationships_source', 'source_entity_id'),
        Index('idx_relationships_target', 'target_entity_id'),
        Index('idx_relationships_type', 'relationship_type'),
        Index('idx_relationships_strength', 'strength'),
    )

    def __repr__(self):
        return f"<Relationship(source={self.source_entity_id}, target={self.target_entity_id}, type={self.relationship_type})>"
