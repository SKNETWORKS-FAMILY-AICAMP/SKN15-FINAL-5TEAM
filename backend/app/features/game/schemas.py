"""
Game Feature Schemas
게임 요소 Pydantic 스키마
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== UserEquipment ====================

class UserEquipmentResponse(BaseModel):
    """사용자 장비 상태 응답"""
    user_id: UUID4
    sword_status: str = Field(..., description="칼 상태: excellent, good, fair, poor, broken")
    uniform_status: str = Field(..., description="제복 상태: pristine, worn, equipped, damaged, torn")
    crow_status: str = Field(..., description="까마귀 상태: waiting, active, resting, absent")
    sword_type: Optional[str] = Field(None, description="칼 종류")
    uniform_color: Optional[str] = Field(None, description="제복 색상")
    crow_name: Optional[str] = Field(None, description="까마귀 이름")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserEquipmentUpdateRequest(BaseModel):
    """사용자 장비 업데이트 요청"""
    sword_status: Optional[str] = Field(None, description="칼 상태")
    uniform_status: Optional[str] = Field(None, description="제복 상태")
    crow_status: Optional[str] = Field(None, description="까마귀 상태")
    sword_type: Optional[str] = Field(None, description="칼 종류")
    uniform_color: Optional[str] = Field(None, description="제복 색상")
    crow_name: Optional[str] = Field(None, description="까마귀 이름")


# ==================== UserUnlockedImage ====================

class UnlockedImageResponse(BaseModel):
    """획득한 이미지 응답"""
    unlock_id: UUID4
    user_id: UUID4
    image_id: UUID4
    scenario_id: Optional[str] = None
    session_id: Optional[UUID4] = None
    stage_id: Optional[str] = None
    unlock_method: str = Field(..., description="획득 방법: story_progress, mission_complete, achievement")
    unlocked_at: datetime

    model_config = {"from_attributes": True}


class UnlockImageRequest(BaseModel):
    """이미지 획득 요청"""
    image_id: UUID4
    scenario_id: Optional[str] = None
    session_id: Optional[UUID4] = None
    stage_id: Optional[str] = None
    unlock_method: str = Field(default="story_progress", description="획득 방법")


class UnlockImageResponse(BaseModel):
    """이미지 획득 응답"""
    newly_unlocked: bool = Field(..., description="새로 획득 여부")
    unlock: Optional[UnlockedImageResponse] = None


class GalleryStatsResponse(BaseModel):
    """갤러리 통계 응답"""
    total_unlocked: int = Field(..., description="획득한 이미지 수")
    total_available: int = Field(..., description="전체 이미지 수")
    unlock_percentage: float = Field(..., description="획득 비율 (0-100)")


# ==================== RankDefinition ====================

class RankDefinitionResponse(BaseModel):
    """랭크 정의 응답"""
    rank_code: str
    rank_name_ko: str
    rank_name_en: Optional[str] = None
    rank_name_ja: Optional[str] = None
    min_xp: int
    level_range_start: int
    level_range_end: int
    icon_emoji: Optional[str] = None
    description_ko: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== GameEvent ====================

class GameEventResponse(BaseModel):
    """게임 이벤트 응답"""
    id: int
    session_id: UUID4
    turn_number: int
    event_type: str = Field(..., description="이벤트 타입: mission_start, mission_complete, rank_up, item_acquired, character_recruited")
    event_data: Dict[str, Any]
    timestamp: datetime

    model_config = {"from_attributes": True}


class CreateGameEventRequest(BaseModel):
    """게임 이벤트 생성 요청"""
    event_type: str = Field(..., description="이벤트 타입")
    event_data: Dict[str, Any] = Field(..., description="이벤트 데이터 (JSONB)")


# ==================== MissionRecord ====================

class MissionRecordResponse(BaseModel):
    """미션 기록 응답"""
    id: int
    session_id: UUID4
    mission_type: str = Field(..., description="미션 타입: persuade, investigate, battle, protect")
    target_character: Optional[str] = None
    attempt_count: int
    success: Optional[bool] = None
    completed_at: datetime

    model_config = {"from_attributes": True}


class CreateMissionRecordRequest(BaseModel):
    """미션 기록 생성 요청"""
    mission_type: str = Field(..., description="미션 타입")
    target_character: Optional[str] = Field(None, description="대상 캐릭터")
    attempt_count: int = Field(default=1, description="시도 횟수")
    success: Optional[bool] = Field(None, description="성공 여부")


class MissionStatsResponse(BaseModel):
    """미션 통계 응답"""
    total_missions: int
    successful_missions: int
    failed_missions: int
    success_rate: float = Field(..., description="성공률 (0-100)")
