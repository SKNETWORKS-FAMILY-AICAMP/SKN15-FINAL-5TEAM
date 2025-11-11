"""
User Character Affinity Model
사용자별 캐릭터 친밀도 (글로벌)
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.db.base import Base


class UserCharacterAffinity(Base):
    """
    사용자별 캐릭터 친밀도 (글로벌)
    """
    __tablename__ = "user_character_affinity"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_name = Column(String(255), nullable=False)
    total_affinity_score = Column(Integer, nullable=False, default=0)
    affinity_level = Column(Integer, nullable=False, default=1)
    total_interactions = Column(Integer, nullable=False, default=0)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'character_name'),
        CheckConstraint('total_affinity_score >= 0 AND total_affinity_score <= 1000'),
        CheckConstraint('affinity_level >= 1 AND affinity_level <= 10'),
        Index('idx_user_character_affinity_character', 'character_name'),
        Index('idx_user_character_affinity_score', 'user_id', 'total_affinity_score'),
    )

    def __repr__(self):
        return f"<UserCharacterAffinity(user={self.user_id}, character={self.character_name}, level={self.affinity_level})>"
