"""
Galleries Feature - Schemas
Pydantic 모델 (Request/Response DTO)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ============================================================
# Image Schemas
# ============================================================

class ImageResponse(BaseModel):
    """이미지 응답"""
    image_id: str
    user_id: str
    scenario_id: str
    session_id: str
    stage_tag: str
    image_url: str
    image_type: str = Field(..., description="generated, unlocked, default")
    extra_metadata: Optional[Dict[str, Any]]
    created_at: str
    like_count: int = Field(default=0, description="좋아요 개수")
    view_count: int = Field(default=0, description="조회수")
    user_liked: bool = Field(default=False, description="사용자 좋아요 여부")

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    """이미지 목록 응답"""
    images: List[ImageResponse]
    total: int


class ImageSaveRequest(BaseModel):
    """이미지 저장 요청"""
    scenario_id: str = Field(..., description="시나리오 ID")
    session_id: str = Field(..., description="세션 ID")
    stage_tag: str = Field(..., description="스테이지 태그")
    image_url: str = Field(..., description="이미지 URL")
    image_type: str = Field(default="generated", description="이미지 타입")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class ImageUnlockResponse(BaseModel):
    """이미지 언락 응답"""
    image_id: str
    user_id: str
    scenario_id: str
    unlocked_at: str

    class Config:
        from_attributes = True
