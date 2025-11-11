"""
Progression Feature - Models
사용자 진행 시스템 관련 데이터베이스 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
import uuid
from app.core.db.base import Base


class UserProgression(Base):
    """
    사용자 진행 정보

    Features:
    - 레벨 시스템 (1-99)
    - 경험치 (XP)
    - 랭크 (novice/explorer/veteran/master/legend)
    - 플레이 통계 (메시지 수, 세션 수, 플레이 시간, 시나리오 완료 수)
    """
    __tablename__ = "user_progression"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)

    # 진행 상태
    rank_code = Column(String(50), default="novice")  # novice, explorer, veteran, master, legend
    experience_points = Column(Integer, default=0)
    level = Column(Integer, default=1)

    # 플레이 통계
    total_messages = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    total_play_minutes = Column(Integer, default=0)
    scenarios_completed = Column(Integer, default=0)
    achievements_count = Column(Integer, default=0)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('level >= 1 AND level <= 99', name='user_progression_level_check'),
        CheckConstraint('experience_points >= 0', name='user_progression_experience_points_check'),
        CheckConstraint('total_messages >= 0', name='user_progression_total_messages_check'),
        CheckConstraint('total_sessions >= 0', name='user_progression_total_sessions_check'),
        CheckConstraint('total_play_minutes >= 0', name='user_progression_total_play_minutes_check'),
        CheckConstraint('scenarios_completed >= 0', name='user_progression_scenarios_completed_check'),
        CheckConstraint('achievements_count >= 0', name='user_progression_achievements_count_check'),
    )

    def __repr__(self):
        return f"<UserProgression(user={self.user_id}, level={self.level}, xp={self.experience_points}, rank={self.rank_code})>"


class XPTransaction(Base):
    """
    XP 변동 기록

    Features:
    - 모든 XP 획득/소비 이력 추적
    - 레벨업 기록
    - XP 타입별 분류 (message, session_complete, scenario_complete, achievement, daily_bonus, event)
    """
    __tablename__ = "xp_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    # XP 변동 정보
    xp_amount = Column(Integer, nullable=False)  # 양수: 획득, 음수: 소비
    xp_type = Column(String(50), nullable=False)  # message, session_complete, scenario_complete, achievement, daily_bonus, event
    xp_balance_after = Column(Integer, nullable=False)

    # 레벨 변동 기록
    level_before = Column(Integer)
    level_after = Column(Integer)
    did_level_up = Column(Boolean, default=False)

    # 추가 정보
    description = Column(Text)
    extra_metadata = Column(JSONB, default={})

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint(
            "xp_type IN ('message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event')",
            name='xp_transactions_xp_type_check'
        ),
        CheckConstraint('xp_balance_after >= 0', name='xp_transactions_xp_balance_after_check'),
    )

    def __repr__(self):
        return f"<XPTransaction(user={self.user_id}, xp={self.xp_amount}, type={self.xp_type}, level_up={self.did_level_up})>"
