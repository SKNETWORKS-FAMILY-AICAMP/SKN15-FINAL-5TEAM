"""
Admin Feature - Schemas
관리자 API 요청/응답 스키마
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DialogueSessionInfoResponse(BaseModel):
    """
    대화 세션 정보 응답 (목록용)
    """
    session_id: str = Field(..., description="세션 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    username: str = Field(..., description="사용자명")
    scenario_id: str = Field(..., description="시나리오 ID")
    current_stage: Optional[str] = Field(None, description="현재 스테이지")
    turn_count: int = Field(default=0, description="총 턴 수")
    is_active: bool = Field(default=True, description="활성 세션 여부")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

    class Config:
        from_attributes = True


class DialogueSessionListResponse(BaseModel):
    """
    대화 세션 목록 응답
    """
    sessions: List[DialogueSessionInfoResponse] = Field(..., description="세션 목록")
    total: int = Field(..., description="총 세션 개수")


class DialogueTurnResponse(BaseModel):
    """
    대화 턴 응답 (상세 내용)
    """
    id: int = Field(..., description="턴 ID")
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    scenario_id: str = Field(..., description="시나리오 ID")
    turn_count: int = Field(..., description="턴 번호")
    speaker: str = Field(..., description="화자")
    text: str = Field(..., description="대사 내용")
    emotion: Optional[str] = Field(None, description="감정")
    stage_tag: Optional[str] = Field(None, description="스테이지 태그")
    affinity_delta: Optional[float] = Field(None, description="호감도 변화")
    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        from_attributes = True


class DialogueTurnListResponse(BaseModel):
    """
    대화 턴 목록 응답
    """
    session_id: str = Field(..., description="세션 ID")
    turns: List[DialogueTurnResponse] = Field(..., description="턴 목록")
    total: int = Field(..., description="총 턴 개수")


# ============================================================
# User Management Schemas
# ============================================================

class AdminUserResponse(BaseModel):
    """
    사용자 정보 응답 (관리자용)
    """
    user_id: str = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    display_name: str = Field(..., description="표시 이름")
    email: Optional[str] = Field(None, description="이메일")
    role: str = Field(..., description="역할 (user, admin, moderator)")
    is_active: bool = Field(..., description="활성 계정 여부")
    is_verified: bool = Field(..., description="이메일 인증 여부")
    total_sessions: int = Field(default=0, description="총 세션 수")
    total_bubbles: int = Field(default=0, description="총 버블 수")
    last_login_at: Optional[datetime] = Field(None, description="마지막 로그인 시간")
    created_at: datetime = Field(..., description="가입 시간")
    updated_at: datetime = Field(..., description="수정 시간")

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    """
    사용자 목록 응답
    """
    users: List[AdminUserResponse] = Field(..., description="사용자 목록")
    total: int = Field(..., description="총 사용자 개수")
