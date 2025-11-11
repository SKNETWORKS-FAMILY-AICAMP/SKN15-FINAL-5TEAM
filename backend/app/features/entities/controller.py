"""
Entities Feature - Controller
Graph RAG 엔티티 API 엔드포인트
Layer 2: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from app.features.entities.usecase import EntitiesUseCase
from app.features.entities.repository import EntitiesRepository
from app.features.entities.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    RelationshipCreate,
    RelationshipResponse,
    EntityMentionCreate,
    EntityMentionResponse,
    EntityGraphResponse
)
from app.core.db.session import get_db
from app.core.logging import get_controller_logger
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/entities", tags=["entities"])
logger = get_controller_logger("Entities")


def get_usecase(db: AsyncSession = Depends(get_db)) -> EntitiesUseCase:
    """EntitiesUseCase 의존성 주입"""
    repository = EntitiesRepository(db)
    return EntitiesUseCase(repository)


# ============================================================
# Entity Endpoints
# ============================================================

@router.post("", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    data: EntityCreate,
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 생성

    Args:
        data: 엔티티 생성 데이터
        usecase: EntitiesUseCase

    Returns:
        EntityResponse
    """
    logger.info("create_entity", f"POST /api/entities - {data.entity_name}")
    return await usecase.create_entity(data)


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: int,
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 조회

    Args:
        entity_id: 엔티티 ID
        usecase: EntitiesUseCase

    Returns:
        EntityResponse
    """
    logger.info("get_entity", f"GET /api/entities/{entity_id}")
    return await usecase.get_entity(entity_id)


@router.get("", response_model=EntityListResponse)
async def search_entities(
    query: Optional[str] = Query(None, description="검색 쿼리"),
    entity_type: Optional[str] = Query(None, description="엔티티 타입 (character, location, event, item, skill)"),
    limit: int = Query(10, ge=1, le=100, description="결과 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 검색

    Args:
        query: 검색 쿼리
        entity_type: 엔티티 타입 필터
        limit: 결과 개수
        offset: 오프셋
        usecase: EntitiesUseCase

    Returns:
        EntityListResponse
    """
    logger.info("search_entities", f"GET /api/entities - query={query}")
    return await usecase.search_entities(
        query=query,
        entity_type=entity_type,
        limit=limit,
        offset=offset
    )


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: int,
    data: EntityUpdate,
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 수정

    Args:
        entity_id: 엔티티 ID
        data: 수정 데이터
        usecase: EntitiesUseCase

    Returns:
        EntityResponse
    """
    logger.info("update_entity", f"PUT /api/entities/{entity_id}")
    return await usecase.update_entity(entity_id, data)


# ============================================================
# Relationship Endpoints
# ============================================================

@router.post("/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    data: RelationshipCreate,
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 관계 생성

    Args:
        data: 관계 생성 데이터
        usecase: EntitiesUseCase

    Returns:
        RelationshipResponse
    """
    logger.info("create_relationship", f"POST /api/entities/relationships")
    return await usecase.create_relationship(data)


@router.get("/{entity_id}/graph", response_model=EntityGraphResponse)
async def get_entity_graph(
    entity_id: int,
    relationship_type: Optional[str] = Query(None, description="관계 타입 필터"),
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 그래프 조회 (엔티티 + 관계 + 관련 엔티티)

    Args:
        entity_id: 엔티티 ID
        relationship_type: 관계 타입 필터
        usecase: EntitiesUseCase

    Returns:
        EntityGraphResponse
    """
    logger.info("get_entity_graph", f"GET /api/entities/{entity_id}/graph")
    return await usecase.get_entity_graph(entity_id, relationship_type)


# ============================================================
# Mention Endpoints
# ============================================================

@router.post("/mentions", response_model=EntityMentionResponse, status_code=status.HTTP_201_CREATED)
async def create_mention(
    data: EntityMentionCreate,
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 언급 생성

    Args:
        data: 언급 생성 데이터
        usecase: EntitiesUseCase

    Returns:
        EntityMentionResponse
    """
    logger.info("create_mention", f"POST /api/entities/mentions - entity_id={data.entity_id}")
    return await usecase.create_mention(data)


@router.get("/{entity_id}/mentions", response_model=list[EntityMentionResponse])
async def get_entity_mentions(
    entity_id: int,
    session_id: Optional[str] = Query(None, description="세션 ID 필터"),
    limit: int = Query(50, ge=1, le=100, description="결과 개수"),
    usecase: EntitiesUseCase = Depends(get_usecase)
):
    """
    엔티티 언급 조회

    Args:
        entity_id: 엔티티 ID
        session_id: 세션 ID 필터
        limit: 결과 개수
        usecase: EntitiesUseCase

    Returns:
        EntityMentionResponse 리스트
    """
    logger.info("get_entity_mentions", f"GET /api/entities/{entity_id}/mentions")
    return await usecase.get_entity_mentions(entity_id, session_id, limit)
