"""
EntityMention 모델 (대화 턴에서 엔티티 언급)
"""
from sqlalchemy import Column, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class EntityMention(Base):
    """엔티티 언급 (대화 턴에서)"""
    __tablename__ = "entity_mentions"

    mention_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    dialogue_turn_id = Column(UUID(as_uuid=True), ForeignKey("dialogue_turns.turn_id"), nullable=False)

    mention_text = Column(Text, nullable=False)
    context = Column(Text)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    entity = relationship("Entity", back_populates="mentions")
    dialogue_turn = relationship("DialogueTurn")
