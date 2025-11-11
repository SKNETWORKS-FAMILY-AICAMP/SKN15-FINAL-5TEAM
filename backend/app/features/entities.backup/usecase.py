"""
Entities Feature - UseCase
Graph RAG 엔티티 비즈니스 로직
Layer 3: UseCase (4-Layer Architecture)
"""
from typing import List, Optional, Dict, Any

from app.features.entities.repository import EntitiesRepository
from app.features.entities.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityWithEmbedding,
    RelationshipCreate,
    RelationshipResponse,
    EntityMentionCreate,
    EntityMentionResponse,
    EntityGraphResponse,
    EntityListResponse
)
from app.core.logging import get_usecase_logger
from app.core.errors import NotFoundException

logger = get_usecase_logger("Entities")


class EntitiesUseCase:
    """
    [Layer 3] UseCase
    책임: Graph RAG 엔티티 비즈니스 로직, 트랜잭션 관리
    금지: HTTP 요청/응답 직접 처리
    """

    def __init__(self, repository: EntitiesRepository):
        """
        UseCase 초기화

        Args:
            repository: EntitiesRepository 인스턴스
        """
        self.repository = repository

    # ============================================================
    # Entity Management
    # ============================================================

    async def create_entity(self, data: EntityCreate) -> EntityResponse:
        """
        엔티티 생성

        Args:
            data: 엔티티 생성 데이터

        Returns:
            EntityResponse
        """
        logger.info("create_entity", f"Creating entity: {data.entity_name}",
                   entity_type=data.entity_type)

        entity = await self.repository.create_entity(
            entity_type=data.entity_type,
            entity_name=data.entity_name,
            canonical_name=data.canonical_name,
            description=data.description,
            properties=data.properties,
            importance_score=data.importance_score or 0.5,
            community_id=data.community_id
        )

        return EntityResponse.model_validate(entity)

    async def get_entity(self, entity_id: int) -> EntityResponse:
        """
        엔티티 조회

        Args:
            entity_id: 엔티티 ID

        Returns:
            EntityResponse

        Raises:
            NotFoundException: 엔티티를 찾을 수 없음
        """
        entity = await self.repository.get_entity_by_id(entity_id)

        if not entity:
            raise NotFoundException(f"Entity not found: {entity_id}")

        return EntityResponse.model_validate(entity)

    async def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        use_vector_search: bool = False,
        query_embedding: Optional[List[float]] = None
    ) -> EntityListResponse:
        """
        엔티티 검색

        Args:
            query: 검색 쿼리
            entity_type: 엔티티 타입 필터
            limit: 결과 개수
            offset: 오프셋
            use_vector_search: 벡터 검색 사용 여부
            query_embedding: 쿼리 임베딩 (벡터 검색시 필요)

        Returns:
            EntityListResponse
        """
        if use_vector_search and query_embedding:
            # 벡터 검색
            entities_with_similarity = await self.repository.search_entities_by_vector(
                query_embedding=query_embedding,
                entity_type=entity_type,
                limit=limit
            )
            entities = [
                EntityWithEmbedding(
                    **EntityResponse.model_validate(entity).model_dump(),
                    similarity=similarity
                )
                for entity, similarity in entities_with_similarity
            ]
            total_count = len(entities)
        else:
            # 텍스트 검색
            entity_list, total_count = await self.repository.search_entities(
                query=query,
                entity_type=entity_type,
                limit=limit,
                offset=offset
            )
            entities = [EntityResponse.model_validate(e) for e in entity_list]

        return EntityListResponse(
            entities=entities,
            total_count=total_count
        )

    async def update_entity(
        self,
        entity_id: int,
        data: EntityUpdate
    ) -> EntityResponse:
        """
        엔티티 수정

        Args:
            entity_id: 엔티티 ID
            data: 수정 데이터

        Returns:
            EntityResponse

        Raises:
            NotFoundException: 엔티티를 찾을 수 없음
        """
        entity = await self.repository.update_entity(
            entity_id=entity_id,
            description=data.description,
            properties=data.properties,
            importance_score=data.importance_score,
            community_id=data.community_id
        )

        if not entity:
            raise NotFoundException(f"Entity not found: {entity_id}")

        logger.info("update_entity", f"Updated entity: {entity_id}")

        return EntityResponse.model_validate(entity)

    # ============================================================
    # Relationship Management
    # ============================================================

    async def create_relationship(
        self,
        data: RelationshipCreate
    ) -> RelationshipResponse:
        """
        엔티티 관계 생성

        Args:
            data: 관계 생성 데이터

        Returns:
            RelationshipResponse
        """
        logger.info("create_relationship", f"Creating relationship: {data.source_entity_id} -> {data.target_entity_id}",
                   relationship_type=data.relationship_type)

        # 엔티티 존재 확인
        source = await self.repository.get_entity_by_id(data.source_entity_id)
        target = await self.repository.get_entity_by_id(data.target_entity_id)

        if not source:
            raise NotFoundException(f"Source entity not found: {data.source_entity_id}")
        if not target:
            raise NotFoundException(f"Target entity not found: {data.target_entity_id}")

        relationship = await self.repository.create_relationship(
            source_entity_id=data.source_entity_id,
            target_entity_id=data.target_entity_id,
            relationship_type=data.relationship_type,
            strength=data.strength or 0.5,
            context=data.context,
            properties=data.properties
        )

        return RelationshipResponse.model_validate(relationship)

    async def get_entity_graph(
        self,
        entity_id: int,
        relationship_type: Optional[str] = None
    ) -> EntityGraphResponse:
        """
        엔티티 그래프 조회 (엔티티 + 관계 + 관련 엔티티)

        Args:
            entity_id: 엔티티 ID
            relationship_type: 관계 타입 필터

        Returns:
            EntityGraphResponse

        Raises:
            NotFoundException: 엔티티를 찾을 수 없음
        """
        # 엔티티 조회
        entity = await self.repository.get_entity_by_id(entity_id)
        if not entity:
            raise NotFoundException(f"Entity not found: {entity_id}")

        # 관계 조회
        relationships = await self.repository.get_entity_relationships(
            entity_id=entity_id,
            direction="both"
        )

        # 관련 엔티티 조회
        related_entities = await self.repository.get_related_entities(
            entity_id=entity_id,
            relationship_type=relationship_type,
            limit=10
        )

        return EntityGraphResponse(
            entity=EntityResponse.model_validate(entity),
            relationships=[RelationshipResponse.model_validate(r) for r in relationships],
            related_entities=[EntityResponse.model_validate(e) for e in related_entities]
        )

    # ============================================================
    # Mention Management
    # ============================================================

    async def create_mention(
        self,
        data: EntityMentionCreate
    ) -> EntityMentionResponse:
        """
        엔티티 언급 생성

        Args:
            data: 언급 생성 데이터

        Returns:
            EntityMentionResponse
        """
        logger.info("create_mention", f"Creating mention for entity {data.entity_id}",
                   session_id=data.session_id, turn=data.turn_number)

        # 엔티티 존재 확인
        entity = await self.repository.get_entity_by_id(data.entity_id)
        if not entity:
            raise NotFoundException(f"Entity not found: {data.entity_id}")

        mention = await self.repository.create_mention(
            entity_id=data.entity_id,
            session_id=data.session_id,
            turn_number=data.turn_number,
            mention_text=data.mention_text,
            context_window=data.context_window,
            sentiment_score=data.sentiment_score
        )

        return EntityMentionResponse.model_validate(mention)

    async def get_entity_mentions(
        self,
        entity_id: int,
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> List[EntityMentionResponse]:
        """
        엔티티 언급 조회

        Args:
            entity_id: 엔티티 ID
            session_id: 세션 ID 필터
            limit: 결과 개수

        Returns:
            EntityMentionResponse 리스트
        """
        mentions = await self.repository.get_entity_mentions(
            entity_id=entity_id,
            session_id=session_id,
            limit=limit
        )

        return [EntityMentionResponse.model_validate(m) for m in mentions]

    # ============================================================
    # Utility Methods
    # ============================================================

    async def get_or_create_entity(
        self,
        entity_type: str,
        entity_name: str,
        **kwargs
    ) -> EntityResponse:
        """
        엔티티 조회 또는 생성

        Args:
            entity_type: 엔티티 타입
            entity_name: 엔티티 이름
            **kwargs: 추가 생성 파라미터

        Returns:
            EntityResponse
        """
        # 기존 엔티티 조회
        entity = await self.repository.get_entity_by_name(
            entity_name=entity_name,
            entity_type=entity_type
        )

        if entity:
            return EntityResponse.model_validate(entity)

        # 새 엔티티 생성
        create_data = EntityCreate(
            entity_type=entity_type,
            entity_name=entity_name,
            canonical_name=kwargs.get("canonical_name"),
            description=kwargs.get("description"),
            properties=kwargs.get("properties"),
            importance_score=kwargs.get("importance_score", 0.5),
            community_id=kwargs.get("community_id")
        )

        return await self.create_entity(create_data)
