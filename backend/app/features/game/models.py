"""
Game Feature Models
게임 요소 모델 (tm_work 브랜치에서 마이그레이션)
"""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.db.base import Base
from datetime import datetime
import uuid


class UserEquipment(Base):
    """
    사용자 장비 상태

    칼, 제복, 까마귀 등 사용자 장비의 상태를 관리
    """
    __tablename__ = "user_equipment"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)

    # 장비 상태
    sword_status = Column(String(50), default="good")  # excellent, good, fair, poor, broken
    uniform_status = Column(String(50), default="worn")  # pristine, worn, equipped, damaged, torn
    crow_status = Column(String(50), default="waiting")  # waiting, active, resting, absent

    # 장비 세부 정보
    sword_type = Column(String(100))
    uniform_color = Column(String(50))
    crow_name = Column(String(100))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "sword_status IN ('excellent', 'good', 'fair', 'poor', 'broken')",
            name="user_equipment_sword_status_check"
        ),
        CheckConstraint(
            "uniform_status IN ('pristine', 'worn', 'equipped', 'damaged', 'torn')",
            name="user_equipment_uniform_status_check"
        ),
        CheckConstraint(
            "crow_status IN ('waiting', 'active', 'resting', 'absent')",
            name="user_equipment_crow_status_check"
        ),
    )

    def __repr__(self):
        return f"<UserEquipment(user_id={self.user_id}, sword={self.sword_status})>"


class UserUnlockedImage(Base):
    """
    사용자가 잠금 해제한 이미지

    스토리 진행, 미션 완료 등으로 획득한 이미지 기록
    """
    __tablename__ = "user_unlocked_images"

    unlock_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    image_id = Column(UUID(as_uuid=True), nullable=False)

    # 언락 정보
    unlocked_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    scenario_id = Column(String(50))
    session_id = Column(UUID(as_uuid=True))
    stage_id = Column(String(100))
    unlock_method = Column(String(50), default="story_progress")  # story_progress, mission_complete, achievement

    def __repr__(self):
        return f"<UserUnlockedImage(user_id={self.user_id}, image_id={self.image_id})>"


class RankDefinition(Base):
    """
    랭크 정의

    사용자 레벨에 따른 랭크 시스템 (계급, 갑, 을, 병, 정 등)
    """
    __tablename__ = "rank_definitions"

    rank_code = Column(String(50), primary_key=True)

    # 다국어 지원
    rank_name_ko = Column(String(100), nullable=False)
    rank_name_en = Column(String(100))
    rank_name_ja = Column(String(100))

    # 랭크 조건
    min_xp = Column(Integer, nullable=False)
    level_range_start = Column(Integer, nullable=False)
    level_range_end = Column(Integer, nullable=False)

    # 표시
    icon_emoji = Column(String(10))
    description_ko = Column(Text)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<RankDefinition(rank_code={self.rank_code}, name={self.rank_name_ko})>"


class GameEvent(Base):
    """
    게임 이벤트 로그

    게임 내에서 발생하는 주요 이벤트 기록
    """
    __tablename__ = "game_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)

    event_type = Column(String(100), nullable=False)  # mission_start, mission_complete, rank_up, item_acquired
    event_data = Column(JSONB, nullable=False)

    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<GameEvent(id={self.id}, type={self.event_type})>"


class MissionRecord(Base):
    """
    미션 완료 기록

    사용자가 완료한 미션 기록
    """
    __tablename__ = "mission_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)

    mission_type = Column(String(100), nullable=False)  # persuade, investigate, battle, protect
    target_character = Column(String(255))

    attempt_count = Column(Integer, default=0)
    success = Column(Boolean)

    completed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<MissionRecord(id={self.id}, type={self.mission_type}, success={self.success})>"
