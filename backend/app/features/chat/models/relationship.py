"""
Relationship 모델 (엔티티 간 관계)
"""
from sqlalchemy import Column, String, Float, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class Relationship(Base):
    """엔티티 간 관계"""
    __tablename__ = "relationships"

    relationship_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)

    relationship_type = Column(String(100), nullable=False)  # knows, located_in, owns, etc.
    description = Column(String(500))
    strength = Column(Float, default=1.0)

    extra_metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="source_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="target_relationships")
