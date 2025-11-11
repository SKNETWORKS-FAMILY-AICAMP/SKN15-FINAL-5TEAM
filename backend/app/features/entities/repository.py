"""
Entities Feature - Repository
Graph RAG 엔티티 데이터 접근
Layer 4: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.features.chat.models import Entity, EntityRelationship, EntityMention
from app.core.logging import get_repository_logger

logger = get_repository_logger("Entities")


class EntitiesRepository:
    """
    [Layer 4] Repository
    책임: Graph RAG 엔티티 CRUD, 관계 그래프 관리
    금지: 비즈니스 로직, HTTP 처리
    """

    def __init__(self, db: AsyncSession):
        """
        Repository 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    # ============================================================
    # Entity Management
    # ============================================================

    async def create_entity(
        self,
        entity_type: str,
        entity_name: str,
        canonical_name: Optional[str] = None,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        importance_score: float = 0.5,
        community_id: Optional[int] = None
    ) -> Entity:
        """
        엔티티 생성

        Args:
            entity_type: 엔티티 타입 (character, location, event, item, skill)
            entity_name: 엔티티 이름
            canonical_name: 정규화된 이름
            description: 엔티티 설명
            properties: 추가 속성
            embedding: 벡터 임베딩
            importance_score: 중요도 점수
            community_id: 커뮤니티 ID

        Returns:
            Entity
        """
        entity = Entity(
            entity_type=entity_type,
            entity_name=entity_name,
            canonical_name=canonical_name or entity_name,
            description=description,
            properties=properties or {},
            embedding=embedding,
            importance_score=importance_score,
            community_id=community_id,
            mention_count=0,
            first_seen_at=datetime.utcnow(),
            last_updated_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        self.db.add(entity)
        await self.db.flush()

        logger.info("create_entity", f"Created entity: {entity_name}",
                   entity_id=entity.entity_id, entity_type=entity_type)

        return entity

    async def get_entity_by_id(self, entity_id: int) -> Optional[Entity]:
        """
        ID로 엔티티 조회

        Args:
            entity_id: 엔티티 ID

        Returns:
            Entity 또는 None
        """
        result = await self.db.execute(
            select(Entity).where(Entity.entity_id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_entity_by_name(
        self,
        entity_name: str,
        entity_type: Optional[str] = None
    ) -> Optional[Entity]:
        """
        이름으로 엔티티 조회

        Args:
            entity_name: 엔티티 이름
            entity_type: 엔티티 타입 필터

        Returns:
            Entity 또는 None
        """
        query = select(Entity).where(Entity.canonical_name == entity_name)
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_entities(
        self,
        query: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[Entity], int]:
        """
        엔티티 검색 (텍스트 기반)

        Args:
            query: 검색 쿼리
            entity_type: 엔티티 타입 필터
            limit: 결과 개수
            offset: 오프셋

        Returns:
            (엔티티 리스트, 전체 개수)
        """
        conditions = []

        if query:
            conditions.append(
                or_(
                    Entity.entity_name.ilike(f"%{query}%"),
                    Entity.canonical_name.ilike(f"%{query}%"),
                    Entity.description.ilike(f"%{query}%")
                )
            )

        if entity_type:
            conditions.append(Entity.entity_type == entity_type)

        # 쿼리 구성
        stmt = select(Entity)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # 전체 개수 조회
        count_stmt = select(func.count(Entity.entity_id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar_one()

        # 페이징 및 정렬
        stmt = stmt.order_by(Entity.importance_score.desc(), Entity.mention_count.desc())
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        entities = result.scalars().all()

        logger.info("search_entities", f"Found {len(entities)}/{total_count} entities",
                   query=query, entity_type=entity_type)

        return list(entities), total_count

    async def search_entities_by_vector(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[Entity, float]]:
        """
        벡터 유사도 기반 엔티티 검색

        Args:
            query_embedding: 쿼리 임베딩 벡터
            entity_type: 엔티티 타입 필터
            limit: 결과 개수
            similarity_threshold: 유사도 임계값

        Returns:
            List[(Entity, similarity_score)]
        """
        # pgvector cosine similarity
        similarity_expr = 1 - Entity.embedding.cosine_distance(query_embedding)

        query = select(
            Entity,
            similarity_expr.label("similarity")
        ).where(
            Entity.embedding.isnot(None)
        )

        if entity_type:
            query = query.where(Entity.entity_type == entity_type)

        query = query.where(similarity_expr >= similarity_threshold)
        query = query.order_by(similarity_expr.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        entities_with_similarity = [(row[0], row[1]) for row in rows]

        logger.info("search_entities_by_vector", f"Found {len(entities_with_similarity)} similar entities",
                   entity_type=entity_type, threshold=similarity_threshold)

        return entities_with_similarity

    async def update_entity(
        self,
        entity_id: int,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        importance_score: Optional[float] = None,
        community_id: Optional[int] = None
    ) -> Optional[Entity]:
        """
        엔티티 수정

        Args:
            entity_id: 엔티티 ID
            description: 새 설명
            properties: 새 속성
            importance_score: 새 중요도 점수
            community_id: 새 커뮤니티 ID

        Returns:
            업데이트된 Entity 또는 None
        """
        entity = await self.get_entity_by_id(entity_id)
        if not entity:
            return None

        if description is not None:
            entity.description = description
        if properties is not None:
            entity.properties = properties
        if importance_score is not None:
            entity.importance_score = importance_score
        if community_id is not None:
            entity.community_id = community_id

        entity.last_updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info("update_entity", f"Updated entity: {entity_id}")

        return entity

    async def increment_mention_count(self, entity_id: int) -> None:
        """
        엔티티 언급 카운트 증가

        Args:
            entity_id: 엔티티 ID
        """
        stmt = update(Entity).where(
            Entity.entity_id == entity_id
        ).values(
            mention_count=Entity.mention_count + 1,
            last_updated_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ============================================================
    # Relationship Management
    # ============================================================

    async def create_relationship(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        strength: float = 0.5,
        context: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> EntityRelationship:
        """
        엔티티 관계 생성

        Args:
            source_entity_id: 소스 엔티티 ID
            target_entity_id: 타겟 엔티티 ID
            relationship_type: 관계 타입
            strength: 관계 강도
            context: 관계 맥락
            properties: 추가 속성

        Returns:
            EntityRelationship
        """
        relationship = EntityRelationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            strength=strength,
            context=context,
            properties=properties or {},
            mention_count=0,
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow()
        )
        self.db.add(relationship)
        await self.db.flush()

        logger.info("create_relationship", f"Created relationship: {source_entity_id} -> {target_entity_id}",
                   relationship_type=relationship_type)

        return relationship

    async def get_entity_relationships(
        self,
        entity_id: int,
        direction: str = "both"  # "outgoing", "incoming", "both"
    ) -> List[EntityRelationship]:
        """
        엔티티의 관계 조회

        Args:
            entity_id: 엔티티 ID
            direction: 관계 방향 (outgoing: 나가는, incoming: 들어오는, both: 양방향)

        Returns:
            EntityRelationship 리스트
        """
        conditions = []

        if direction == "outgoing":
            conditions.append(EntityRelationship.source_entity_id == entity_id)
        elif direction == "incoming":
            conditions.append(EntityRelationship.target_entity_id == entity_id)
        else:  # both
            conditions.append(
                or_(
                    EntityRelationship.source_entity_id == entity_id,
                    EntityRelationship.target_entity_id == entity_id
                )
            )

        query = select(EntityRelationship).where(or_(*conditions))
        query = query.order_by(EntityRelationship.strength.desc())

        result = await self.db.execute(query)
        relationships = result.scalars().all()

        logger.debug("get_entity_relationships", f"Found {len(relationships)} relationships",
                    entity_id=entity_id, direction=direction)

        return list(relationships)

    async def get_related_entities(
        self,
        entity_id: int,
        relationship_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Entity]:
        """
        관련 엔티티 조회

        Args:
            entity_id: 엔티티 ID
            relationship_type: 관계 타입 필터
            limit: 결과 개수

        Returns:
            Entity 리스트
        """
        # source_entity_id가 entity_id인 관계의 target 조회
        conditions_out = [EntityRelationship.source_entity_id == entity_id]
        if relationship_type:
            conditions_out.append(EntityRelationship.relationship_type == relationship_type)

        query_out = (
            select(Entity)
            .join(EntityRelationship, EntityRelationship.target_entity_id == Entity.entity_id)
            .where(and_(*conditions_out))
            .order_by(EntityRelationship.strength.desc())
            .limit(limit)
        )

        result_out = await self.db.execute(query_out)
        entities_out = result_out.scalars().all()

        # target_entity_id가 entity_id인 관계의 source 조회
        conditions_in = [EntityRelationship.target_entity_id == entity_id]
        if relationship_type:
            conditions_in.append(EntityRelationship.relationship_type == relationship_type)

        query_in = (
            select(Entity)
            .join(EntityRelationship, EntityRelationship.source_entity_id == Entity.entity_id)
            .where(and_(*conditions_in))
            .order_by(EntityRelationship.strength.desc())
            .limit(limit)
        )

        result_in = await self.db.execute(query_in)
        entities_in = result_in.scalars().all()

        # 중복 제거 및 병합
        all_entities = list(entities_out) + list(entities_in)
        seen = set()
        unique_entities = []
        for entity in all_entities:
            if entity.entity_id not in seen:
                seen.add(entity.entity_id)
                unique_entities.append(entity)

        logger.debug("get_related_entities", f"Found {len(unique_entities)} related entities",
                    entity_id=entity_id, relationship_type=relationship_type)

        return unique_entities[:limit]

    async def increment_relationship_mention(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str
    ) -> None:
        """
        관계 언급 카운트 증가

        Args:
            source_entity_id: 소스 엔티티 ID
            target_entity_id: 타겟 엔티티 ID
            relationship_type: 관계 타입
        """
        stmt = update(EntityRelationship).where(
            and_(
                EntityRelationship.source_entity_id == source_entity_id,
                EntityRelationship.target_entity_id == target_entity_id,
                EntityRelationship.relationship_type == relationship_type
            )
        ).values(
            mention_count=EntityRelationship.mention_count + 1,
            last_seen_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ============================================================
    # Mention Management
    # ============================================================

    async def create_mention(
        self,
        entity_id: int,
        session_id: str,
        turn_number: int,
        mention_text: Optional[str] = None,
        context_window: Optional[str] = None,
        sentiment_score: Optional[float] = None
    ) -> EntityMention:
        """
        엔티티 언급 생성

        Args:
            entity_id: 엔티티 ID
            session_id: 세션 ID
            turn_number: 턴 번호
            mention_text: 언급된 텍스트
            context_window: 주변 맥락
            sentiment_score: 감정 점수

        Returns:
            EntityMention
        """
        mention = EntityMention(
            entity_id=entity_id,
            session_id=session_id,
            turn_number=turn_number,
            mention_text=mention_text,
            context_window=context_window,
            sentiment_score=sentiment_score,
            mentioned_at=datetime.utcnow()
        )
        self.db.add(mention)
        await self.db.flush()

        # 엔티티 언급 카운트 증가
        await self.increment_mention_count(entity_id)

        logger.info("create_mention", f"Created mention for entity {entity_id}",
                   session_id=session_id, turn=turn_number)

        return mention

    async def get_entity_mentions(
        self,
        entity_id: int,
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> List[EntityMention]:
        """
        엔티티 언급 조회

        Args:
            entity_id: 엔티티 ID
            session_id: 세션 ID 필터
            limit: 결과 개수

        Returns:
            EntityMention 리스트
        """
        query = select(EntityMention).where(EntityMention.entity_id == entity_id)

        if session_id:
            query = query.where(EntityMention.session_id == session_id)

        query = query.order_by(EntityMention.mentioned_at.desc()).limit(limit)

        result = await self.db.execute(query)
        mentions = result.scalars().all()

        logger.debug("get_entity_mentions", f"Found {len(mentions)} mentions",
                    entity_id=entity_id, session_id=session_id)

        return list(mentions)
