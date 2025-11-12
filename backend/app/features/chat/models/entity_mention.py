"""
EntityMention Model (기존 DB 구조)
"""
from sqlalchemy import Column, Text, Integer, Float, ForeignKey, Index, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.base import Base
from datetime import datetime


class EntityMention(Base):
    """
    대화 턴별 엔티티 언급 기록
    """
    __tablename__ = "entity_mentions"

    mention_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("knowledge.entities.entity_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation.sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    mention_text = Column(Text)
    context_window = Column(Text)
    sentiment_score = Column(Float)
    mentioned_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('sentiment_score >= -1.0 AND sentiment_score <= 1.0', name='valid_sentiment'),
        Index('idx_mentions_entity', 'entity_id', 'mentioned_at'),
        Index('idx_mentions_session', 'session_id', 'turn_number'),
        {"schema": "knowledge"}
    )

    def __repr__(self):
        return f"<EntityMention(id={self.mention_id}, entity={self.entity_id}, text={self.mention_text[:20]}...)>"
