"""
Progression Feature Schemas
진행도 Pydantic 스키마
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== UserInput ====================

class UserInputResponse(BaseModel):
    """사용자 입력 응답"""
    id: int
    session_id: UUID4
    turn_number: int
    user_input: str
    timestamp: datetime

    model_config = {"from_attributes": True}


# ==================== UserProgression ====================

class UserProgressionResponse(BaseModel):
    """사용자 진행도 응답"""
    user_id: UUID4
    rank_code: str
    experience_points: int
    level: int
    total_messages: int
    total_sessions: int
    total_play_minutes: int
    scenarios_completed: int
    achievements_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AwardXPRequest(BaseModel):
    """경험치 지급 요청"""
    xp_amount: int = Field(..., ge=0, description="지급할 경험치")
    xp_type: str = Field(..., description="경험치 타입: message, session_complete, scenario_complete, achievement, daily_bonus, event")
    description: Optional[str] = Field(None, description="설명")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")


class AwardXPResponse(BaseModel):
    """경험치 지급 응답"""
    user_id: str
    experience_points: int
    level: int
    level_before: int
    level_after: int
    did_level_up: bool
    xp_balance_after: int


class XPTransactionResponse(BaseModel):
    """경험치 거래 내역 응답"""
    transaction_id: UUID4
    user_id: UUID4
    xp_amount: int
    xp_type: str
    xp_balance_after: int
    level_before: Optional[int] = None
    level_after: Optional[int] = None
    did_level_up: bool
    description: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncrementStatRequest(BaseModel):
    """통계 증가 요청"""
    stat_name: str = Field(..., description="통계 이름: total_messages, total_sessions, total_play_minutes, scenarios_completed, achievements_count")
    increment_by: int = Field(default=1, ge=1, description="증가량")


# ==================== UserScenarioProgress ====================

class ScenarioProgressResponse(BaseModel):
    """시나리오 진행도 응답"""
    user_id: UUID4
    scenario_id: str
    has_started: bool
    has_completed: bool
    completion_percentage: int
    last_session_id: Optional[str] = None
    last_played_at: Optional[datetime] = None
    total_messages: int
    total_play_time: int
    is_liked: bool
    liked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateScenarioProgressRequest(BaseModel):
    """시나리오 진행도 업데이트 요청"""
    has_started: Optional[bool] = None
    has_completed: Optional[bool] = None
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    last_session_id: Optional[str] = None
    last_played_at: Optional[datetime] = None
    total_messages: Optional[int] = Field(None, ge=0)
    total_play_time: Optional[int] = Field(None, ge=0)


class ToggleLikeResponse(BaseModel):
    """좋아요 토글 응답"""
    is_liked: bool
    was_created: bool = Field(..., description="진행도가 새로 생성되었는지 여부")


# ==================== StageProgression ====================

class StageProgressionResponse(BaseModel):
    """스테이지 진행 응답"""
    id: int
    session_id: UUID4
    stage_id: str
    stage_order: int
    entered_at: datetime
    exited_at: Optional[datetime] = None
    dialogue_count: int
    stage_turn_count: int

    model_config = {"from_attributes": True}


class CreateStageProgressionRequest(BaseModel):
    """스테이지 진행 시작 요청"""
    stage_id: str
    stage_order: int


class UpdateStageProgressionRequest(BaseModel):
    """스테이지 진행 업데이트 요청"""
    exited_at: Optional[datetime] = None
    dialogue_count: Optional[int] = Field(None, ge=0)
    stage_turn_count: Optional[int] = Field(None, ge=0)


# ==================== Combined Responses ====================

class UserProgressionWithRankResponse(BaseModel):
    """사용자 진행도 + 랭크 정보"""
    user_id: UUID4
    rank_code: str
    rank_name_ko: Optional[str] = None
    rank_icon_emoji: Optional[str] = None
    experience_points: int
    level: int
    total_messages: int
    total_sessions: int
    total_play_minutes: int
    scenarios_completed: int
    achievements_count: int
    created_at: datetime
    updated_at: datetime


class UserStatsResponse(BaseModel):
    """사용자 통계 종합"""
    progression: UserProgressionResponse
    recent_xp_transactions: list[XPTransactionResponse]
    scenario_progress_count: int
    total_likes: int
