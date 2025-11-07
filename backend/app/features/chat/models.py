"""
Chat Feature - SQLAlchemy Models
DB 테이블 정의
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from app.core.db.base import Base, TimestampMixin


class DialogueTurn(Base, TimestampMixin):
    """
    대화 턴 기록

    각 대사를 개별 row로 저장
    """
    __tablename__ = "dialogue_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    scenario_id = Column(String(255), nullable=False)
    turn_count = Column(Integer, nullable=False)

    # 대사 내용
    speaker = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)  # ✅ text로 통일 (content 아님!)
    emotion = Column(String(50), default="neutral")

    # 메타데이터
    stage_tag = Column(String(100))
    affinity_delta = Column(Float, default=0.0)

    # 인덱스
    __table_args__ = (
        Index('idx_session_user', 'session_id', 'user_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<DialogueTurn(id={self.id}, speaker={self.speaker}, session={self.session_id})>"
