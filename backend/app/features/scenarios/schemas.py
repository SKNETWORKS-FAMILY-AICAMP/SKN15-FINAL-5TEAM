"""
Scenarios Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# Comment Schemas
# ============================================================

class CommentCreateRequest(BaseModel):
    """댓글 작성 요청"""
    content: str = Field(..., min_length=1, max_length=500, description="댓글 내용")
    parent_comment_id: Optional[int] = Field(None, description="부모 댓글 ID (대댓글인 경우)")


class CommentUpdateRequest(BaseModel):
    """댓글 수정 요청"""
    content: str = Field(..., min_length=1, max_length=500, description="새 댓글 내용")


class CommentResponse(BaseModel):
    """댓글 응답"""
    id: int
    scenario_id: str
    user_id: str
    content: str
    parent_comment_id: Optional[int]
    like_count: int
    is_edited: bool
    is_deleted: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    """댓글 목록 응답"""
    comments: List[CommentResponse]
    total: int


# ============================================================
# Like Schemas
# ============================================================

class LikeResponse(BaseModel):
    """좋아요 응답"""
    is_liked: bool = Field(..., description="좋아요 여부")
    like_count: int = Field(..., description="총 좋아요 수")


# ============================================================
# Scenario Schemas
# ============================================================

class ScenarioListResponse(BaseModel):
    """시나리오 목록 응답"""
    scenarios: List[Dict[str, Any]]
    total: int


class ScenarioDetailResponse(BaseModel):
    """시나리오 상세 응답"""
    scenario_id: str
    title: str
    description: Optional[str]
    world_id: Optional[str]
    like_count: int
    user_liked: bool
    comment_count: int
    # 기타 시나리오 메타데이터
    metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
