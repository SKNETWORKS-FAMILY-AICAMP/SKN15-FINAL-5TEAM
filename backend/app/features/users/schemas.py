"""
Users Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# ============================================================
# Profile Schemas
# ============================================================

class UserProfileResponse(BaseModel):
    """사용자 프로필 응답"""
    user_id: str
    username: str
    display_name: str
    email: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    total_sessions: int = 0
    total_bubbles: int = 0
    last_login_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """프로필 수정 요청"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=50, description="표시 이름")
    email: Optional[EmailStr] = Field(None, description="이메일")


# ============================================================
# Stats Schemas
# ============================================================

class UserStatsResponse(BaseModel):
    """사용자 통계 응답"""
    total_dialogues: int = Field(..., description="총 대화 수")
    total_sessions: int = Field(..., description="총 세션 수")
    completed_scenarios: int = Field(..., description="완료한 시나리오 수")
    total_credits_used: int = Field(..., description="사용한 크레딧")
    total_affinity_points: int = Field(..., description="총 친밀도 점수")
    achievements: List[str] = Field(default_factory=list, description="달성한 업적")
    rank: str = Field(..., description="사용자 등급")
    created_at: str = Field(..., description="가입일")
    last_active_at: str = Field(..., description="마지막 활동")

    class Config:
        from_attributes = True


# ============================================================
# Credits Schemas
# ============================================================

class UserCreditsResponse(BaseModel):
    """사용자 크레딧 조회 응답"""
    current_credits: int = Field(..., description="현재 보유 크레딧")
    total_earned: int = Field(default=0, description="총 획득 크레딧")
    total_consumed: int = Field(default=0, description="총 사용 크레딧")

    class Config:
        from_attributes = True


class ConsumeCreditsRequest(BaseModel):
    """크레딧 소비 요청"""
    amount: int = Field(..., ge=1, description="소비할 크레딧 양")
    description: str = Field(..., min_length=1, max_length=200, description="사용 목적")


class ConsumeCreditsResponse(BaseModel):
    """크레딧 소비 응답"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    remaining_credits: int = Field(..., description="남은 크레딧")

    class Config:
        from_attributes = True
