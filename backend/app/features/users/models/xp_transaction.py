"""
XPTransaction 모델
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.db.base import Base
import uuid
from datetime import datetime


class XPTransaction(Base):
    """XP 트랜잭션 로그"""
    __tablename__ = "xp_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    # session_id removed - not in DB schema

    xp_amount = Column(Integer, nullable=False)  # 양수: 획득, 음수: 소비
    xp_type = Column(String(50), nullable=False)  # message, scenario_complete, achievement, etc.

    xp_balance_after = Column(Integer, nullable=False)
    level_before = Column(Integer)
    level_after = Column(Integer)
    did_level_up = Column(Boolean, default=False)

    description = Column(String)  # Match DB schema
    extra_metadata = Column("metadata", JSONB, default={})  # DB column name is "metadata"

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="xp_transactions")
    # session = relationship("Session")  # commented out - Session model doesn't have back_populates
