"""
Entities Feature - Schemas
Graph RAG 엔티티 요청/응답 스키마
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EntityCreate(BaseModel):
    """엔티티 생성 요청"""
    entity_type: str = Field(..., description="엔티티 타입: character, location, event, item, skill")
    entity_name: str = Field(..., description="엔티티 이름")
    canonical_name: Optional[str] = Field(None, description="정규화된 이름")
    description: Optional[str] = Field(None, description="엔티티 설명")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 속성")
    importance_score: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="중요도 점수")
    community_id: Optional[int] = Field(None, description="커뮤니티 ID")


class EntityUpdate(BaseModel):
    """엔티티 수정 요청"""
    description: Optional[str] = Field(None, description="엔티티 설명")
    properties: Optional[Dict[str, Any]] = Field(None, description="추가 속성")
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="중요도 점수")
    community_id: Optional[int] = Field(None, description="커뮤니티 ID")


class EntityResponse(BaseModel):
    """엔티티 응답"""
    entity_id: int
    entity_type: str
    entity_name: str
    canonical_name: Optional[str]
    description: Optional[str]
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    importance_score: Optional[float]
    community_id: Optional[int]
    mention_count: Optional[int]
    first_seen_at: Optional[datetime]
    last_updated_at: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class EntityWithEmbedding(EntityResponse):
    """임베딩 포함 엔티티 응답"""
    embedding: Optional[List[float]] = None
    similarity: Optional[float] = None


class RelationshipCreate(BaseModel):
    """엔티티 관계 생성 요청"""
    source_entity_id: int = Field(..., description="소스 엔티티 ID")
    target_entity_id: int = Field(..., description="타겟 엔티티 ID")
    relationship_type: str = Field(..., description="관계 타입 (예: knows, located_at, participates_in)")
    strength: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="관계 강도")
    context: Optional[str] = Field(None, description="관계 맥락")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 속성")


class RelationshipResponse(BaseModel):
    """엔티티 관계 응답"""
    relationship_id: int
    source_entity_id: int
    target_entity_id: int
    relationship_type: str
    strength: Optional[float]
    context: Optional[str]
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    mention_count: Optional[int]
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


class EntityMentionCreate(BaseModel):
    """엔티티 언급 생성 요청"""
    entity_id: int = Field(..., description="엔티티 ID")
    session_id: str = Field(..., description="세션 ID")
    turn_number: int = Field(..., description="턴 번호")
    mention_text: Optional[str] = Field(None, description="언급된 텍스트")
    context_window: Optional[str] = Field(None, description="주변 맥락")
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="감정 점수")


class EntityMentionResponse(BaseModel):
    """엔티티 언급 응답"""
    mention_id: int
    entity_id: int
    session_id: str
    turn_number: int
    mention_text: Optional[str]
    context_window: Optional[str]
    sentiment_score: Optional[float]
    mentioned_at: Optional[datetime]

    class Config:
        from_attributes = True


class EntityGraphResponse(BaseModel):
    """엔티티 그래프 응답 (엔티티 + 관계)"""
    entity: EntityResponse
    relationships: List[RelationshipResponse]
    related_entities: List[EntityResponse]


class EntitySearchRequest(BaseModel):
    """엔티티 검색 요청"""
    query: Optional[str] = Field(None, description="검색 쿼리")
    entity_type: Optional[str] = Field(None, description="엔티티 타입 필터")
    limit: int = Field(10, ge=1, le=100, description="결과 개수")
    use_vector_search: bool = Field(False, description="벡터 검색 사용 여부")


class EntityListResponse(BaseModel):
    """엔티티 목록 응답"""
    entities: List[EntityResponse]
    total_count: int
