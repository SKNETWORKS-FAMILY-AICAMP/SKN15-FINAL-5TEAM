"""
Knowledge Graph Service
엔티티 추출, 관계 분석, 언급 추적 통합 서비스
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient
from app.features.chat.services.extractors.entity_extractor import EntityExtractor
from app.features.chat.services.extractors.relationship_extractor import RelationshipExtractor
from app.features.chat.repositories.entity_repository import EntityRepository
from app.features.chat.models.entity import Entity
from app.features.chat.models.entity_mention import EntityMention

logger = get_parent_logger("KnowledgeGraphService")


class KnowledgeGraphService:
    """
    지식 그래프 통합 서비스

    책임:
    - 대화에서 엔티티 자동 추출
    - 엔티티 간 관계 자동 분석
    - 엔티티 언급 추적 및 기록
    - 지식 그래프 업데이트
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True
    ):
        """
        Args:
            db: 데이터베이스 세션
            llm_client: LLM 클라이언트
            enable_llm: LLM 기반 추출 활성화
        """
        self.db = db
        self.llm_client = llm_client or LLMClient()
        self.enable_llm = enable_llm

        # Initialize extractors
        self.entity_extractor = EntityExtractor(
            llm_client=self.llm_client,
            enable_llm=enable_llm
        )
        self.relationship_extractor = RelationshipExtractor(
            llm_client=self.llm_client,
            enable_llm=enable_llm
        )

        # Initialize repository
        self.entity_repository = EntityRepository(db)

        logger.info("__init__", "KnowledgeGraphService initialized",
                   enable_llm=enable_llm)

    async def process_dialogue_turn(
        self,
        text: str,
        session_id: str,
        turn_number: int,
        speaker: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        대화 턴 처리: 엔티티 추출, 관계 분석, 언급 추적

        Args:
            text: 대화 텍스트
            session_id: 세션 ID
            turn_number: 턴 번호
            speaker: 화자
            context: 추가 컨텍스트 (scenario_id, user_id 등)

        Returns:
            {
                "entities_extracted": int,
                "entities_new": int,
                "relationships_extracted": int,
                "mentions_recorded": int
            }
        """
        logger.info("process_dialogue_turn", "Processing dialogue turn",
                   session_id=session_id, turn_number=turn_number, speaker=speaker)

        result = {
            "entities_extracted": 0,
            "entities_new": 0,
            "relationships_extracted": 0,
            "mentions_recorded": 0
        }

        try:
            # 1. Extract entities from text
            extracted_entities = await self.entity_extractor.extract_entities(
                text=text,
                context={
                    "session_id": session_id,
                    "turn_number": turn_number,
                    "speaker": speaker,
                    **(context or {})
                }
            )

            result["entities_extracted"] = len(extracted_entities)

            if not extracted_entities:
                logger.debug("process_dialogue_turn", "No entities extracted")
                return result

            # 2. Upsert entities to database
            entity_records = []
            for entity in extracted_entities:
                # Check if entity exists
                existing = await self.entity_repository.get_by_canonical_name(
                    entity_type=entity.entity_type,
                    canonical_name=entity.canonical_name or entity.entity_name
                )

                if existing:
                    # Update mention count
                    await self.entity_repository.increment_mention_count(existing.entity_id)
                    entity_records.append(existing)
                else:
                    # Create new entity
                    new_entity = await self.entity_repository.create_entity(
                        entity_type=entity.entity_type,
                        entity_name=entity.entity_name,
                        canonical_name=entity.canonical_name or entity.entity_name,
                        description=entity.description,
                        properties=entity.properties or {}
                    )
                    entity_records.append(new_entity)
                    result["entities_new"] += 1

            # 3. Record entity mentions
            for i, entity in enumerate(extracted_entities):
                entity_record = entity_records[i]

                await self.entity_repository.create_mention(
                    entity_id=entity_record.entity_id,
                    session_id=session_id,
                    turn_number=turn_number,
                    mention_text=entity.entity_name,
                    context_window=entity.context
                )
                result["mentions_recorded"] += 1

            # 4. Extract relationships
            if len(entity_records) >= 2:
                # Prepare entity data for relationship extraction
                entity_data = []
                for i, entity_record in enumerate(entity_records):
                    entity_data.append({
                        "entity_id": entity_record.entity_id,
                        "entity_name": entity_record.entity_name,
                        "canonical_name": entity_record.canonical_name,
                        "entity_type": entity_record.entity_type
                    })

                relationships = await self.relationship_extractor.extract_relationships(
                    text=text,
                    entities=entity_data,
                    session_id=session_id,
                    turn_number=turn_number
                )

                # Store relationships
                for rel in relationships:
                    await self.entity_repository.create_or_update_relationship(
                        source_entity_id=rel.source_entity_id,
                        target_entity_id=rel.target_entity_id,
                        relationship_type=rel.relationship_type,
                        strength=rel.strength,
                        properties=rel.properties or {}
                    )

                result["relationships_extracted"] = len(relationships)

            logger.info("process_dialogue_turn", "Dialogue turn processed successfully",
                       **result)

            return result

        except Exception as e:
            logger.error("process_dialogue_turn", f"Failed to process dialogue turn: {e}",
                        session_id=session_id, turn_number=turn_number)
            raise

    async def get_session_knowledge_graph(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        세션의 지식 그래프 조회

        Args:
            session_id: 세션 ID

        Returns:
            {
                "entities": List[Entity],
                "relationships": List[Relationship],
                "mentions": List[EntityMention]
            }
        """
        logger.info("get_session_knowledge_graph", "Fetching session knowledge graph",
                   session_id=session_id)

        try:
            # Get all mentions for this session
            mentions = await self.entity_repository.get_mentions_by_session(session_id)

            # Get unique entity IDs
            entity_ids = list(set(m.entity_id for m in mentions))

            # Get entities
            entities = []
            for entity_id in entity_ids:
                entity = await self.entity_repository.get_entity(entity_id)
                if entity:
                    entities.append(entity)

            # Get relationships between these entities
            relationships = await self.entity_repository.get_relationships_for_entities(entity_ids)

            return {
                "entities": entities,
                "relationships": relationships,
                "mentions": mentions,
                "stats": {
                    "total_entities": len(entities),
                    "total_relationships": len(relationships),
                    "total_mentions": len(mentions)
                }
            }

        except Exception as e:
            logger.error("get_session_knowledge_graph", f"Failed to fetch knowledge graph: {e}",
                        session_id=session_id)
            raise

    async def get_entity_context(
        self,
        entity_id: int,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        엔티티 컨텍스트 조회 (최근 언급, 관련 엔티티, 관계)

        Args:
            entity_id: 엔티티 ID
            limit: 조회할 최근 언급 수

        Returns:
            {
                "entity": Entity,
                "recent_mentions": List[EntityMention],
                "related_entities": List[Entity],
                "relationships": List[Relationship]
            }
        """
        logger.info("get_entity_context", "Fetching entity context",
                   entity_id=entity_id, limit=limit)

        try:
            # Get entity
            entity = await self.entity_repository.get_entity(entity_id)
            if not entity:
                return {"error": "Entity not found"}

            # Get recent mentions
            recent_mentions = await self.entity_repository.get_recent_mentions(
                entity_id=entity_id,
                limit=limit
            )

            # Get relationships
            relationships = await self.entity_repository.get_entity_relationships(entity_id)

            # Get related entities
            related_entity_ids = set()
            for rel in relationships:
                if rel.source_entity_id == entity_id:
                    related_entity_ids.add(rel.target_entity_id)
                else:
                    related_entity_ids.add(rel.source_entity_id)

            related_entities = []
            for rel_entity_id in related_entity_ids:
                rel_entity = await self.entity_repository.get_entity(rel_entity_id)
                if rel_entity:
                    related_entities.append(rel_entity)

            return {
                "entity": entity,
                "recent_mentions": recent_mentions,
                "related_entities": related_entities,
                "relationships": relationships,
                "stats": {
                    "mention_count": entity.mention_count,
                    "related_entities_count": len(related_entities),
                    "relationships_count": len(relationships)
                }
            }

        except Exception as e:
            logger.error("get_entity_context", f"Failed to fetch entity context: {e}",
                        entity_id=entity_id)
            raise
