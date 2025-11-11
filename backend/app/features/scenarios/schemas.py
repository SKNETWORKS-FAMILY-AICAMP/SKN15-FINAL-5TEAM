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
    username: str
    display_name: str
    content: str
    parent_comment_id: Optional[int]
    like_count: int
    is_liked: bool = False
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


# ============================================================
# Stage Schemas
# ============================================================

class MicroBeatResponse(BaseModel):
    """마이크로 비트 응답"""
    beat_id: str
    beat_order: int
    goal: str
    speaker_hint: Optional[List[str]]
    fx: Optional[str]
    i18n_key: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class StageResponse(BaseModel):
    """스테이지 응답"""
    stage_id: str
    scenario_id: str
    stage_order: int
    stage_type: str  # scene, mission, router, free_intent, open_narrative
    config: Dict[str, Any]
    title: Optional[str]
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class StageDetailResponse(BaseModel):
    """스테이지 상세 응답 (타입별 세부 정보 포함)"""
    stage: StageResponse
    # scene 타입인 경우 micro_beats 포함
    micro_beats: Optional[List[MicroBeatResponse]] = None
    # mission 타입인 경우 미션 정보
    mission: Optional[Dict[str, Any]] = None
    # router 타입인 경우 라우팅 정보
    router: Optional[Dict[str, Any]] = None
    # free_intent 타입인 경우 인텐트 매핑
    intent_mappings: Optional[List[Dict[str, Any]]] = None


class StageListResponse(BaseModel):
    """스테이지 목록 응답"""
    stages: List[StageResponse]
    total: int


class StageCreateRequest(BaseModel):
    """스테이지 생성 요청"""
    stage_id: str = Field(..., description="스테이지 ID")
    scenario_id: str = Field(..., description="시나리오 ID")
    stage_order: int = Field(..., description="스테이지 순서")
    stage_type: str = Field(..., description="스테이지 타입")
    config: Dict[str, Any] = Field(default_factory=dict, description="스테이지 설정")
    title: Optional[str] = Field(None, description="스테이지 제목")
    description: Optional[str] = Field(None, description="스테이지 설명")
