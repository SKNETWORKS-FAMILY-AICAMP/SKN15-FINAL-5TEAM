"""
Sessions Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ============================================================
# Session Schemas
# ============================================================

class SessionListItemResponse(BaseModel):
    """세션 목록 아이템 응답"""
    session_id: str
    scenario_id: str
    scenario_title: Optional[str] = None
    scenario_thumbnail: Optional[str] = None
    current_stage: str
    turn_count: int
    last_message_speaker: Optional[str] = None
    last_message_content: Optional[str] = None
    last_dialogue: str  # 하위 호환성 유지
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: List[SessionListItemResponse]
    total: int


class SessionDetailResponse(BaseModel):
    """세션 상세 응답"""
    session_id: str
    user_id: str
    scenario_id: str
    scenario_title: str
    current_stage: str
    turn_count: int
    state: Dict[str, Any] = Field(..., description="전체 게임 상태")
    created_at: str
    updated_at: str
    dialogues: List[Dict[str, Any]] = Field(..., description="최근 대화")

    class Config:
        from_attributes = True


class SessionCreateRequest(BaseModel):
    """세션 생성 요청"""
    scenario_id: str = Field(..., description="시나리오 ID")


class SessionCreateResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    user_id: str
    scenario_id: str
    state: Dict[str, Any]
    created_at: str

    class Config:
        from_attributes = True
