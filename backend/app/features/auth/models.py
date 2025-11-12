"""
Auth Feature - Models
사용자 인증 관련 데이터베이스 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Index, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
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
    password_hash = Column(String(255), nullable=True)
    provider = Column(String(50), default='email', nullable=False)  # email, google, kakao, etc.

    # Profile
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="user", nullable=False)  # user, admin, moderator

    # Stats (denormalized for quick access)
    total_sessions = Column(Integer, default=0)
    total_bubbles = Column(Integer, default=0)  # 총 획득 버블 수

    # Last Activity
    last_login = Column(DateTime, nullable=True)

    # Relationships
    xp_transactions = relationship("XPTransaction", back_populates="user")

    # Indexes
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_is_active', 'is_active'),
        {"schema": "auth"}
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
    used = Column(Boolean, default=False, nullable=False)  # DB 컬럼명

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_password_reset_token', 'token'),
        Index('idx_password_reset_user_id', 'user_id'),
        Index('idx_password_reset_expires_at', 'expires_at'),
        {"schema": "auth"}
    )

    def __repr__(self):
        return f"<PasswordResetToken(id={self.token_id}, user_id={self.user_id}, used={self.used})>"


class UserCredits(Base):
    """
    사용자 크레딧(버블) 정보

    Note: DB 테이블명은 user_credits입니다.
    """
    __tablename__ = "user_credits"

    # Primary Key & Foreign Key
    user_id = Column(UUID(as_uuid=True), primary_key=True)

    # 크레딧 정보
    bubble_count = Column(Integer, default=100, nullable=False)
    total_purchased = Column(Integer, default=100, nullable=False)
    total_consumed = Column(Integer, default=0, nullable=False)

    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("bubble_count >= 0", name="positive_bubble_count"),
        CheckConstraint("total_purchased >= 0 AND total_consumed >= 0", name="positive_totals"),
        {"schema": "auth"}
    )

    def __repr__(self):
        return f"<UserCredits(user_id={self.user_id}, bubbles={self.bubble_count})>"


class UserSettings(Base):
    """
    사용자 설정

    사운드, 볼륨, 언어 등 개인 설정 정보를 관리합니다.
    """
    __tablename__ = "user_settings"
    __table_args__ = {"schema": "auth"}

    # Primary Key & Foreign Key
    user_id = Column(UUID(as_uuid=True), primary_key=True)

    # Sound Settings
    sound_enabled = Column(Boolean, default=True, nullable=False)
    bgm_volume = Column(Integer, default=80, nullable=False)
    sfx_volume = Column(Integer, default=100, nullable=False)

    # Language Settings
    language = Column(String(10), default='ko', nullable=False)

    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, language={self.language})>"


class CreditTransaction(Base):
    """
    크레딧 변동 기록

    Features:
    - 모든 크레딧 획득/소비 이력 추적
    - 거래 타입별 분류 (purchase, consume, refund, bonus, initial)
    - 변동 후 잔액 기록
    """
    __tablename__ = "credit_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # 크레딧 변동 정보
    amount = Column(Integer, nullable=False)  # 양수: 획득, 음수: 소비
    transaction_type = Column(String(50), nullable=False)  # purchase, consume, refund, bonus, initial
    balance_after = Column(Integer, nullable=False)

    # 추가 정보
    description = Column(Text)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('purchase', 'consume', 'refund', 'bonus', 'initial')",
            name='credit_transactions_transaction_type_check'
        ),
        {"schema": "auth"}
    )

    def __repr__(self):
        return f"<CreditTransaction(user={self.user_id}, amount={self.amount}, type={self.transaction_type})>"
