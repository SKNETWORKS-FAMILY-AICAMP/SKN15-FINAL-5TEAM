"""
DialogueTurn 모델
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class DialogueTurn(Base):
    """대화 턴"""
    __tablename__ = "dialogue_turns"

    turn_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    turn_number = Column(Integer, nullable=False)

    user_input = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    speaker = Column(String(100))
    emotion = Column(String(50))

    stage_id = Column(String(100))
    stage_type = Column(String(50))

    image_url = Column(Text)
    thumbnail_url = Column(Text)

    affinity_change = Column(Float, default=0.0)
    xp_earned = Column(Integer, default=0)

    extra_metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships (commented out - Session model doesn't have back_populates defined)
    # session = relationship("Session", back_populates="dialogue_turns")
