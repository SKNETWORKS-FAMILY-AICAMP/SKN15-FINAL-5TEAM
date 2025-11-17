"""
ShortTermMemory 모델 - 세션 전용 맥락 저장
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app.core.db.base import Base


class ShortTermMemory(Base):
    """단기 기억 (Short-term Memory)

    목적: 세션 전용 맥락 저장 (5턴 단위 chunk 요약)
    - 세션 내부의 디테일을 보강
    - 프롬프트에서 우선순위 높음
    - 세션 종료 시 삭제

    Schema: knowledge.short_term_memories

    chunk_summaries 구조:
    [
        {
            "chunk_id": 1,
            "turn_range": "1-5",
            "summary": "플레이어가 탄지로를 만나 자기소개...",
            "created_at": "2025-01-17T10:00:00Z"
        },
        ...
    ]
    """
    __tablename__ = "short_term_memories"
    __table_args__ = {"schema": "knowledge"}

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.user_id", ondelete="CASCADE"),
        nullable=False
    )

    # Session Identification
    scenario_id = Column(String(100), nullable=False, comment="시나리오 ID")
    session_id = Column(UUID(as_uuid=True), nullable=False, comment="세션 ID")

    # STM 내용
    stm_summary = Column(Text, nullable=True, comment="세션 전체 요약 (선택적)")
    chunk_summaries = Column(
        JSONB,
        nullable=True,
        default=[],
        comment="5턴 단위 chunk 요약 배열"
    )

    # 통계
    turn_count = Column(Integer, default=0, nullable=False, comment="현재 턴 수")
    last_turn_timestamp = Column(DateTime, nullable=True, comment="마지막 턴 시각")

    # 메타데이터
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ShortTermMemory(id={self.id}, session_id={self.session_id}, turn_count={self.turn_count})>"
