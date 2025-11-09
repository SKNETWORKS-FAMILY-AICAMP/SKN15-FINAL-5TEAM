"""
Memory Service - 통합 메모리 관리 서비스

Entity, Relationship, Memory Extraction을 통합 관리합니다.

Features:
- 엔티티 추출 (EntityExtractor 래핑)
- 관계 추출 (RelationshipExtractor 래핑)
- 장기 기억 추출 (MemoryExtractor 래핑)
- 통합 메모리 처리 파이프라인
"""
from typing import List, Dict, Any, Optional

from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient

from .extractors import (
    EntityExtractor,
    Entity,
    RelationshipExtractor,
    EntityRelationship,
    MemoryExtractor,
)

settings = get_settings()
logger = get_parent_logger("MemoryService")


class MemoryService:
    """
    통합 메모리 관리 서비스 (Layer 3 - Service)

    EntityExtractor, RelationshipExtractor, MemoryExtractor를
    통합하여 편리한 API를 제공합니다.

    Example:
        service = MemoryService(llm_client=llm)

        # 엔티티 추출
        entities = await service.extract_entities(
            text="탄지로와 네즈코가 함께 싸웠다",
            context={"scenario_id": "mugen_train"}
        )

        # 관계 추출
        relationships = await service.extract_relationships(
            text="탄지로와 네즈코가 함께 싸웠다",
            entities=entities
        )

        # 장기 기억 추출
        memories = await service.extract_memories(
            conversation_summary="탄지로는 네즈코를 매우 아낀다..."
        )
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            enable_llm: LLM 사용 여부
        """
        self.llm_client = llm_client or LLMClient()

        # Extractors 초기화
        self.entity_extractor = EntityExtractor(
            llm_client=self.llm_client,
            enable_llm=enable_llm
        )
        self.relationship_extractor = RelationshipExtractor(
            llm_client=self.llm_client,
            enable_llm=enable_llm
        )
        self.memory_extractor = MemoryExtractor(
            llm_client=self.llm_client
        )

        logger.info("__init__", "MemoryService initialized",
                   enable_llm=enable_llm)

    async def extract_entities(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """
        텍스트에서 엔티티 추출

        Args:
            text: 입력 텍스트
            context: 추가 컨텍스트 (scenario_id 등)

        Returns:
            Entity 리스트
        """
        logger.debug("extract_entities", "Extracting entities", text_len=len(text))

        entities = await self.entity_extractor.extract_entities(text, context)

        logger.info("extract_entities", "Entities extracted",
                   count=len(entities))
        return entities

    async def extract_relationships(
        self,
        text: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None
    ) -> List[EntityRelationship]:
        """
        텍스트에서 엔티티 간 관계 추출

        Args:
            text: 입력 텍스트
            entities: 엔티티 리스트 (None이면 자동 추출)
            session_id: 세션 ID (추적용)

        Returns:
            EntityRelationship 리스트
        """
        logger.debug("extract_relationships", "Extracting relationships",
                    text_len=len(text),
                    entities_provided=entities is not None)

        # 엔티티가 없으면 먼저 추출
        if entities is None:
            entity_objects = await self.entity_extractor.extract_entities(text)
            entities = [
                {
                    "entity_id": e.entity_id,
                    "entity_type": e.entity_type,
                    "name": e.name
                }
                for e in entity_objects
            ]

        relationships = await self.relationship_extractor.extract_relationships(
            text,
            entities,
            session_id
        )

        logger.info("extract_relationships", "Relationships extracted",
                   count=len(relationships))
        return relationships

    async def extract_memories(
        self,
        conversation_summary: str
    ) -> List[Dict[str, Any]]:
        """
        대화 요약에서 장기 기억 추출

        Args:
            conversation_summary: 대화 요약 텍스트

        Returns:
            Memory 리스트 (dict 형태)
        """
        logger.debug("extract_memories", "Extracting memories",
                    summary_len=len(conversation_summary))

        memories = await self.memory_extractor.extract_memories(conversation_summary)

        logger.info("extract_memories", "Memories extracted",
                   count=len(memories))
        return memories

    async def process_conversation_turn(
        self,
        user_input: str,
        assistant_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        대화 한 턴에서 모든 메모리 정보 추출 (통합 파이프라인)

        Args:
            user_input: 사용자 입력
            assistant_response: 어시스턴트 응답
            context: 추가 컨텍스트

        Returns:
            {
                "entities": List[Entity],
                "relationships": List[EntityRelationship],
                "combined_text": str
            }
        """
        # 텍스트 결합
        combined_text = f"사용자: {user_input}\n어시스턴트: {assistant_response}"

        logger.debug("process_conversation_turn", "Processing conversation turn",
                    user_input_len=len(user_input),
                    response_len=len(assistant_response))

        # 엔티티 추출
        entities = await self.extract_entities(combined_text, context)

        # 관계 추출
        entity_dicts = [
            {
                "entity_id": e.entity_id,
                "entity_type": e.entity_type,
                "name": e.name
            }
            for e in entities
        ]
        relationships = await self.extract_relationships(
            combined_text,
            entity_dicts,
            context.get("session_id") if context else None
        )

        logger.info("process_conversation_turn", "Conversation turn processed",
                   entities=len(entities),
                   relationships=len(relationships))

        return {
            "entities": entities,
            "relationships": relationships,
            "combined_text": combined_text
        }


__all__ = ["MemoryService"]
