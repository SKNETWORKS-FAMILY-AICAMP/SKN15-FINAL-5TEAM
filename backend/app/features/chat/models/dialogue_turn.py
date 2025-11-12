"""
DialogueTurn Model (대화 턴 기록)
"""
from sqlalchemy import Column, String, Text, Integer, Float, Index, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db.base import Base
from datetime import datetime


class DialogueTurn(Base):
    """
    대화 턴 기록

    각 대사를 개별 row로 저장
    Note: DB 테이블명은 dialogues이며, conversation 스키마에 있습니다.
    """
    __tablename__ = "dialogues"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Session & User Info
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scenario_id = Column(String(255), nullable=False)
    turn_number = Column(Integer, nullable=False)

    # 대사 내용
    speaker = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    emotion = Column(String(100))
    emotion_intensity = Column(String(50))

    # 메타데이터
    stage_tag = Column(String(100))
    affinity_delta = Column(Float, default=0.0)
    order_index = Column(Integer)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # 인덱스
    __table_args__ = (
        Index('idx_session_user', 'session_id', 'user_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_session_turn', 'session_id', 'turn_number'),
        {"schema": "conversation"}
    )

    def __repr__(self):
        return f"<DialogueTurn(id={self.id}, speaker={self.speaker}, session={self.session_id})>"
