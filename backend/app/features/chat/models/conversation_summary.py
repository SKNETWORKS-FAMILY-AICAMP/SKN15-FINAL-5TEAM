"""
ConversationSummary 모델
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class ConversationSummary(Base):
    """대화 요약"""
    __tablename__ = "conversation_summaries"

    summary_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)

    summary_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))

    message_count = Column(Integer, default=0)
    last_turn_number = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (commented out - Session model doesn't have back_populates defined)
    # session = relationship("Session")
