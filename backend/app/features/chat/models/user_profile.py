"""
UserProfile 모델 - 사용자 프로필 (최소 기억 유지)
"""
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from app.core.db.base import Base


class UserProfile(Base):
    """사용자 프로필

    목적: 최소 기억 유지 (이름, 호칭, 말투, 취향 등)
    - 시나리오 모드에서도 항상 접근 가능
    - LTM과 분리되어 독립적으로 관리

    Schema: auth.user_profiles
    """
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "auth"}

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # 기본 정보
    display_name = Column(String(100), nullable=True, comment="선호하는 호칭")
    speaking_style = Column(String(50), nullable=True, comment="말투 (formal, casual, playful 등)")

    # 고정 취향
    likes = Column(ARRAY(String), nullable=True, default=[], comment="좋아하는 것들")
    dislikes = Column(ARRAY(String), nullable=True, default=[], comment="싫어하는 것들")

    # 안정적 성격 태그
    personality_traits = Column(
        JSONB,
        nullable=True,
        default={},
        comment="성격 특성 (예: {\"friendly\": 0.8, \"curious\": 0.6})"
    )

    # 메타데이터
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, display_name={self.display_name})>"
