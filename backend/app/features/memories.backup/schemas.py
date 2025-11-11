"""
Memories Feature - Schemas
사용자 기억 관련 Request/Response DTO
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MemoryResponse(BaseModel):
    """사용자 기억 응답"""
    memory_id: int = Field(..., description="기억 ID")
    user_id: str = Field(..., description="사용자 ID")
    scenario_id: Optional[str] = Field(None, description="시나리오 ID")
    memory_type: str = Field(..., description="기억 유형 (episodic/semantic/procedural)")
    content: str = Field(..., description="기억 내용")
    importance_score: Optional[float] = Field(None, description="중요도 점수 (0.0-1.0)")
    access_count: int = Field(default=0, description="액세스 횟수")
    last_accessed_at: Optional[str] = Field(None, description="마지막 액세스 시간")
    created_at: Optional[str] = Field(None, description="생성일시")
    updated_at: Optional[str] = Field(None, description="수정일시")

    class Config:
        from_attributes = True
