"""
Images Feature - Schemas
이미지 매핑 요청/응답 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ImageMappingCreate(BaseModel):
    """이미지 매핑 생성 요청"""
    scenario_id: Optional[str] = Field(None, description="시나리오 ID (전역 이미지는 None)")
    mapping_category: str = Field(..., description="카테고리: character, bg, cutscene, stage")
    image_key: str = Field(..., description="이미지 키 (예: rengoku_normal, train_bg_1)")
    image_url: str = Field(..., description="이미지 URL (S3 또는 로컬 경로)")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")


class ImageMappingUpdate(BaseModel):
    """이미지 매핑 수정 요청"""
    image_url: Optional[str] = Field(None, description="새 이미지 URL")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")


class ImageMappingResponse(BaseModel):
    """이미지 매핑 응답"""
    id: int
    scenario_id: Optional[str]
    mapping_category: str
    image_key: str
    image_url: str
    extra_data: Dict[str, Any]

    class Config:
        from_attributes = True


class ImageQueryRequest(BaseModel):
    """이미지 조회 요청"""
    scenario_id: Optional[str] = Field(None, description="시나리오 ID")
    mapping_category: Optional[str] = Field(None, description="카테고리 필터")
    image_key: Optional[str] = Field(None, description="이미지 키 필터")


class ImageQueryResponse(BaseModel):
    """이미지 조회 응답"""
    images: List[ImageMappingResponse]
    total_count: int
