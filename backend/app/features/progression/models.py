"""
Progression Models
사용자 진행도 모델 (tm_work 브랜치에서 마이그레이션)
"""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.db.base import Base
from datetime import datetime
import uuid


class UserInput(Base):
    """
    사용자 입력 기록

    세션별 사용자 입력을 기록
    """
    __tablename__ = "user_inputs"
    __table_args__ = {"schema": "conversation"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation.sessions.session_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="SET NULL"))
    turn_number = Column(Integer, nullable=False)
    user_input = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<UserInput(id={self.id}, session={self.session_id}, turn={self.turn_number})>"


class UserProgression(Base):
    """
    사용자 전체 진행도

    레벨, XP, 랭크, 통계 등 전체 진행도 관리
    """
    __tablename__ = "user_progression"

    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="CASCADE"), primary_key=True)

    # 랭크 및 레벨
    rank_code = Column(String(50), default="novice")
    experience_points = Column(Integer, default=0)
    level = Column(Integer, default=1)

    # 통계
    total_messages = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    total_play_minutes = Column(Integer, default=0)
    scenarios_completed = Column(Integer, default=0)
    achievements_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("experience_points >= 0", name="user_progression_experience_points_check"),
        CheckConstraint("level >= 1 AND level <= 99", name="user_progression_level_check"),
        CheckConstraint("total_messages >= 0", name="user_progression_total_messages_check"),
        CheckConstraint("total_sessions >= 0", name="user_progression_total_sessions_check"),
        CheckConstraint("total_play_minutes >= 0", name="user_progression_total_play_minutes_check"),
        CheckConstraint("scenarios_completed >= 0", name="user_progression_scenarios_completed_check"),
        CheckConstraint("achievements_count >= 0", name="user_progression_achievements_count_check"),
        {"schema": "progression"}
    )

    def __repr__(self):
        return f"<UserProgression(user_id={self.user_id}, level={self.level}, xp={self.experience_points})>"


class UserScenarioProgress(Base):
    """
    시나리오별 진행도

    각 시나리오에 대한 사용자의 진행 상태 및 통계
    """
    __tablename__ = "user_scenario_progress"

    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.user_id", ondelete="CASCADE"), primary_key=True)
    scenario_id = Column(String(50), primary_key=True)

    # 진행 상태
    has_started = Column(Boolean, default=False)
    has_completed = Column(Boolean, default=False)
    completion_percentage = Column(Integer, default=0)

    # 세션 정보
    last_session_id = Column(String(100))
    last_played_at = Column(DateTime(timezone=True))

    # 통계
    total_messages = Column(Integer, default=0)
    total_play_time = Column(Integer, default=0)  # seconds

    # 좋아요
    is_liked = Column(Boolean, default=False)
    liked_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("completion_percentage >= 0 AND completion_percentage <= 100",
                        name="user_scenario_progress_completion_percentage_check"),
        CheckConstraint("total_messages >= 0", name="user_scenario_progress_total_messages_check"),
        CheckConstraint("total_play_time >= 0", name="user_scenario_progress_total_play_time_check"),
        {"schema": "progression"}
    )

    def __repr__(self):
        return f"<UserScenarioProgress(user_id={self.user_id}, scenario={self.scenario_id}, complete={self.completion_percentage}%)>"


class StageProgression(Base):
    """
    스테이지 진행 기록

    세션 내에서 각 스테이지의 진입/이탈 시간 및 통계
    """
    __tablename__ = "stage_progression"
    __table_args__ = {"schema": "progression"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation.sessions.session_id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(String(255), nullable=False)
    stage_order = Column(Integer, nullable=False)

    # 타이밍
    entered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    exited_at = Column(DateTime(timezone=True))

    # 통계
    dialogue_count = Column(Integer, default=0)
    stage_turn_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<StageProgression(id={self.id}, stage={self.stage_id}, session={self.session_id})>"
