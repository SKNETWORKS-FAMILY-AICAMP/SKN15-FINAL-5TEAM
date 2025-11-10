"""
Auth Feature - Models
사용자 인증 관련 데이터베이스 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    사용자 정보

    Note: 이 모델은 app/core/db/models.py에서 이동했습니다.
    Gemini 피드백에 따라 feature별로 모델을 구성하는 패턴을 따릅니다.
    """
    __tablename__ = "users"

    # Primary Key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Authentication
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="user", nullable=False)  # user, admin, moderator

    # Stats (denormalized for quick access)
    total_sessions = Column(Integer, default=0)
    total_bubbles = Column(Integer, default=0)  # 총 획득 버블 수

    # Last Activity
    last_login_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"


class PasswordResetToken(Base):
    """
    비밀번호 재설정 토큰

    일회용 토큰으로 비밀번호 재설정에 사용됩니다.
    """
    __tablename__ = "password_reset_tokens"

    # Primary Key
    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Token Data
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_password_reset_token', 'token'),
        Index('idx_password_reset_user_id', 'user_id'),
        Index('idx_password_reset_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f"<PasswordResetToken(id={self.token_id}, user_id={self.user_id}, used={self.is_used})>"
