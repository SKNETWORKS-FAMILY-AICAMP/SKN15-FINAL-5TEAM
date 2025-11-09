"""
Core DB Models
공통으로 사용되는 DB 모델들
"""
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.db.base import Base


class Session(Base):
    """
    세션 정보 (PostgreSQL 저장용)
    """
    __tablename__ = "sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True)
    scenario_id = Column(String(255), nullable=False, index=True)
    user_name = Column(String(255))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), index=True)

    # 세션 상태
    current_stage = Column(String(255))
    turn_count = Column(Integer, default=0)
    stage_turn = Column(Integer, default=0)
    final_ending = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)

    # 요약 정보
    conversation_summary = Column(Text, default="")
    summary_updated_at = Column(DateTime)
    summary_turn_count = Column(Integer, default=0)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_sessions_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Session(id={self.session_id}, scenario={self.scenario_id}, user={self.user_name})>"
