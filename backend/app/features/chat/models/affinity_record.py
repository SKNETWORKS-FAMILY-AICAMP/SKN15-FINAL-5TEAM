"""
Affinity Record Model
세션별 친밀도 변화 기록
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.db.base import Base


class AffinityRecord(Base):
    """
    세션별 친밀도 변화 기록
    """
    __tablename__ = "affinity_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    character_name = Column(String(255), nullable=False)
    affinity_score = Column(Integer, nullable=False)
    change_amount = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_affinity_session', 'session_id', 'character_name'),
        Index('idx_affinity_character', 'character_name'),
        Index('idx_affinity_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AffinityRecord(session={self.session_id}, character={self.character_name}, score={self.affinity_score})>"
