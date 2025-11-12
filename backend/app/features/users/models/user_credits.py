"""
UserCredits 모델
"""
from sqlalchemy import Column, Integer, TIMESTAMP, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db.base import Base


class UserCredits(Base):
    """사용자 크레딧 (버블) 테이블"""
    __tablename__ = "user_credits"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    bubble_count = Column(Integer, nullable=False, default=200, server_default="200")
    total_purchased = Column(Integer, nullable=False, default=200, server_default="200")
    total_consumed = Column(Integer, nullable=False, default=0, server_default="0")
    last_updated = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint('bubble_count >= 0', name='user_credits_bubble_count_check'),
        CheckConstraint('total_consumed >= 0', name='user_credits_total_consumed_check'),
        CheckConstraint('total_purchased >= 0', name='user_credits_total_purchased_check'),
    )
