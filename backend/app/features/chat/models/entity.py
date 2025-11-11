"""
Entity 모델 (Graph RAG)
"""
from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class Entity(Base):
    """엔티티 (인물, 장소, 사물, 개념)"""
    __tablename__ = "entities"

    entity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(100), nullable=False)

    entity_type = Column(String(50), nullable=False)  # person, place, thing, concept
    entity_name = Column(String(255), nullable=False)
    description = Column(Text)

    properties = Column(JSONB, default={})
    embedding = Column(Vector(1536))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mentions = relationship("EntityMention", back_populates="entity", cascade="all, delete-orphan")
    source_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    target_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )
