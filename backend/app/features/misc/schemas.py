"""
Misc Feature Schemas
기타 기능 Pydantic 스키마
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== SessionSnapshot ====================

class SessionSnapshotResponse(BaseModel):
    """세션 스냅샷 응답"""
    id: int
    session_id: UUID4
    turn_number: int
    state_json: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== ScenarioStatistics ====================

class ScenarioStatisticsResponse(BaseModel):
    """시나리오 통계 응답"""
    scenario_id: str
    total_likes: int
    total_comments: int
    total_views: int
    total_completions: int
    total_sessions: int
    avg_session_duration: int
    last_updated: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== UserFeedback ====================

class CreateFeedbackRequest(BaseModel):
    """피드백 생성 요청"""
    feedback_type: str = Field(..., description="bug_report, feature_request, general, rating")
    feedback_text: Optional[str] = None
    training_log_id: Optional[int] = None


class UserFeedbackResponse(BaseModel):
    """사용자 피드백 응답"""
    id: int
    training_log_id: Optional[int] = None
    feedback_type: str
    feedback_text: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
