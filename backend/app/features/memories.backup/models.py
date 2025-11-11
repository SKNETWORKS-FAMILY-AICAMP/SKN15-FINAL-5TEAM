"""
Memories Feature - Models
사용자 기억 관련 데이터베이스 모델 (pgvector 지원)
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, BigInteger, Text, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.core.db.base import Base


class UserMemory(Base):
    """
    사용자 기억 저장 (pgvector 지원)

    Features:
    - 에피소드 기억 (episodic): 특정 사건/대화
    - 의미 기억 (semantic): 캐릭터 정보, 관계
    - 절차 기억 (procedural): 게임 규칙, 패턴
    """
    __tablename__ = "user_memories"

    memory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id = Column(String(50), index=True)

    # 기억 유형
    memory_type = Column(
        String(50),
        nullable=False,
        index=True
    )  # 'episodic', 'semantic', 'procedural'

    # 기억 내용
    content = Column(Text, nullable=False)

    # 임베딩 벡터 (1536차원 - OpenAI text-embedding-3-small)
    embedding = Column(Vector(1536), nullable=True)

    # 중요도 점수 (0.0 ~ 1.0)
    importance_score = Column(Float, nullable=True)

    # 액세스 통계
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('episodic', 'semantic', 'procedural')",
            name='valid_memory_type'
        ),
        CheckConstraint(
            'importance_score >= 0.0 AND importance_score <= 1.0',
            name='valid_memory_importance'
        ),
        Index('idx_memories_user', 'user_id', 'created_at'),
        Index('idx_memories_scenario', 'scenario_id'),
        Index('idx_memories_type', 'memory_type'),
        Index('idx_memories_importance', 'importance_score'),
    )

    def __repr__(self):
        return f"<UserMemory(id={self.memory_id}, user={self.user_id}, type={self.memory_type})>"
