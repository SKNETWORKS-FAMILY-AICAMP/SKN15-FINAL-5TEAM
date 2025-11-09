"""
Chat Feature - Repository
DB 접근 레이어 (CRUD)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import json

from .models import (
    DialogueTurn,
    UserCharacterAffinity,
    AffinityRecord,
    Entity,
    EntityRelationship,
    EntityMention,
    UserMemory,
)
from app.core.logging import get_repository_logger

logger = get_repository_logger("Chat")


class ChatRepository:
    """
    [Layer 4] Repository
    책임: DB CRUD, 쿼리 최적화
    금지: 비즈니스 로직, 트랜잭션 관리 (UseCase가 담당)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_dialogue(self, dialogue: DialogueTurn) -> DialogueTurn:
        """
        대사 저장

        Args:
            dialogue: DialogueTurn 인스턴스

        Returns:
            저장된 DialogueTurn (id 포함)
        """
        logger.info("save_dialogue", "Saving dialogue", speaker=dialogue.speaker, session_id=dialogue.session_id)

        self.db.add(dialogue)
        await self.db.flush()  # ID 생성

        logger.info("save_dialogue", "Dialogue saved", dialogue_id=dialogue.id)
        return dialogue

    async def save_dialogues_batch(self, dialogues: List[DialogueTurn]) -> List[DialogueTurn]:
        """
        대사 배치 저장

        Args:
            dialogues: DialogueTurn 리스트

        Returns:
            저장된 DialogueTurn 리스트
        """
        logger.info("save_dialogues_batch", f"Saving {len(dialogues)} dialogues")

        self.db.add_all(dialogues)
        await self.db.flush()

        logger.info("save_dialogues_batch", f"Batch saved: {len(dialogues)} dialogues")
        return dialogues

    async def count_today(self, user_id: str) -> int:
        """
        오늘 사용자의 대화 횟수

        Args:
            user_id: 사용자 ID

        Returns:
            오늘 대화 횟수
        """
        logger.debug("count_today", "Counting today's dialogues", user_id=user_id)

        today_start = datetime.combine(date.today(), datetime.min.time())

        stmt = select(func.count(DialogueTurn.id)).where(
            and_(
                DialogueTurn.user_id == user_id,
                DialogueTurn.created_at >= today_start
            )
        )

        result = await self.db.execute(stmt)
        count = result.scalar_one()

        logger.debug("count_today", f"Today's count: {count}", user_id=user_id, count=count)
        return count

    async def get_recent_dialogues(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[DialogueTurn]:
        """
        세션의 최근 대화 조회

        Args:
            session_id: 세션 ID
            limit: 조회 개수

        Returns:
            최근 대화 리스트 (시간 역순)
        """
        logger.debug("get_recent_dialogues", "Fetching recent dialogues", session_id=session_id, limit=limit)

        stmt = (
            select(DialogueTurn)
            .where(DialogueTurn.session_id == session_id)
            .order_by(DialogueTurn.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        logger.debug("get_recent_dialogues", f"Fetched {len(dialogues)} dialogues", session_id=session_id)
        return list(dialogues)

    async def get_user_dialogue_history(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        days: int = 7,
        limit: int = 100
    ) -> List[DialogueTurn]:
        """
        사용자의 대화 히스토리 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (선택)
            days: 최근 N일
            limit: 최대 개수

        Returns:
            대화 히스토리
        """
        logger.debug("get_user_dialogue_history", "Fetching user history", user_id=user_id, scenario_id=scenario_id)

        since = datetime.utcnow() - timedelta(days=days)

        conditions = [
            DialogueTurn.user_id == user_id,
            DialogueTurn.created_at >= since
        ]

        if scenario_id:
            conditions.append(DialogueTurn.scenario_id == scenario_id)

        stmt = (
            select(DialogueTurn)
            .where(and_(*conditions))
            .order_by(DialogueTurn.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        logger.debug("get_user_dialogue_history", f"Fetched {len(dialogues)} dialogues", user_id=user_id)
        return list(dialogues)

    async def delete_session_dialogues(self, session_id: str) -> int:
        """
        세션의 모든 대화 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제된 대화 수
        """
        logger.warning("delete_session_dialogues", "Deleting session dialogues", session_id=session_id)

        stmt = select(DialogueTurn).where(DialogueTurn.session_id == session_id)
        result = await self.db.execute(stmt)
        dialogues = result.scalars().all()

        count = len(dialogues)
        for dialogue in dialogues:
            await self.db.delete(dialogue)

        await self.db.flush()

        logger.warning("delete_session_dialogues", f"Deleted {count} dialogues", session_id=session_id)
        return count

    # ============================================================
    # Session State Management (JSONB)
    # ============================================================

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 상태 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 상태 dict (없으면 None)
        """
        logger.debug("get_session", "Fetching session", session_id=session_id)

        stmt = text("""
            SELECT id, user_id, scenario_id, state, created_at, updated_at, last_interaction_at
            FROM chat_sessions
            WHERE id = :session_id AND is_active = TRUE
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        row = result.fetchone()

        if not row:
            logger.debug("get_session", "Session not found", session_id=session_id)
            return None

        session_data = {
            "session_id": row.id,
            "user_id": row.user_id,
            "scenario_id": row.scenario_id,
            "state": row.state if isinstance(row.state, dict) else json.loads(row.state),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "last_interaction_at": row.last_interaction_at,
        }

        logger.debug("get_session", "Session found", session_id=session_id)
        return session_data

    async def save_session(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        state: Dict[str, Any]
    ) -> None:
        """
        세션 상태 저장 (upsert)

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            state: 세션 상태 dict
        """
        logger.info("save_session", "Saving session", session_id=session_id)

        stmt = text("""
            INSERT INTO chat_sessions (id, user_id, scenario_id, state, created_at, updated_at, last_interaction_at)
            VALUES (:session_id, :user_id, :scenario_id, CAST(:state AS jsonb), NOW(), NOW(), NOW())
            ON CONFLICT (id)
            DO UPDATE SET
                state = CAST(:state AS jsonb),
                updated_at = NOW(),
                last_interaction_at = NOW()
        """)

        await self.db.execute(stmt, {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "state": json.dumps(state)
        })

        await self.db.flush()
        logger.info("save_session", "Session saved", session_id=session_id)

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (soft delete)

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_session", "Deleting session", session_id=session_id)

        stmt = text("""
            UPDATE chat_sessions
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :session_id
        """)

        result = await self.db.execute(stmt, {"session_id": session_id})
        await self.db.flush()

        deleted = result.rowcount > 0
        logger.warning("delete_session", f"Session deleted: {deleted}", session_id=session_id)
        return deleted

    # ============================================================
    # Affinity Management
    # ============================================================

    async def save_affinity_record(
        self,
        session_id: str,
        turn_number: int,
        character_name: str,
        affinity_score: int,
        change_amount: Optional[int] = None
    ) -> AffinityRecord:
        """
        세션별 친밀도 변화 기록 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            character_name: 캐릭터 이름
            affinity_score: 현재 친밀도 점수
            change_amount: 변화량

        Returns:
            저장된 AffinityRecord
        """
        logger.info("save_affinity_record", f"Saving affinity for {character_name}",
                   session_id=session_id, score=affinity_score)

        record = AffinityRecord(
            session_id=session_id,
            turn_number=turn_number,
            character_name=character_name,
            affinity_score=affinity_score,
            change_amount=change_amount
        )
        self.db.add(record)
        await self.db.flush()

        logger.info("save_affinity_record", f"Affinity record saved", record_id=record.id)
        return record

    async def get_latest_affinity(
        self,
        session_id: str,
        character_name: str
    ) -> Optional[AffinityRecord]:
        """
        세션의 최신 친밀도 기록 조회

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름

        Returns:
            최신 AffinityRecord (없으면 None)
        """
        logger.debug("get_latest_affinity", f"Fetching latest affinity for {character_name}",
                    session_id=session_id)

        stmt = (
            select(AffinityRecord)
            .where(
                and_(
                    AffinityRecord.session_id == session_id,
                    AffinityRecord.character_name == character_name
                )
            )
            .order_by(AffinityRecord.timestamp.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        logger.debug("get_latest_affinity", f"Latest affinity: {record.affinity_score if record else None}")
        return record

    async def upsert_user_character_affinity(
        self,
        user_id: str,
        character_name: str,
        score_delta: int
    ) -> UserCharacterAffinity:
        """
        사용자별 글로벌 친밀도 UPSERT

        Args:
            user_id: 사용자 ID
            character_name: 캐릭터 이름
            score_delta: 친밀도 변화량

        Returns:
            업데이트된 UserCharacterAffinity
        """
        logger.info("upsert_user_character_affinity", f"Updating global affinity for {character_name}",
                   user_id=user_id, delta=score_delta)

        # 기존 레코드 조회
        stmt = select(UserCharacterAffinity).where(
            and_(
                UserCharacterAffinity.user_id == user_id,
                UserCharacterAffinity.character_name == character_name
            )
        )
        result = await self.db.execute(stmt)
        affinity = result.scalar_one_or_none()

        if affinity:
            # 업데이트
            affinity.total_affinity_score = max(0, min(1000, affinity.total_affinity_score + score_delta))
            affinity.total_interactions += 1
            affinity.last_interaction_at = datetime.utcnow()
            affinity.updated_at = datetime.utcnow()
        else:
            # 생성
            affinity = UserCharacterAffinity(
                user_id=user_id,
                character_name=character_name,
                total_affinity_score=max(0, min(1000, score_delta)),
                affinity_level=1,
                total_interactions=1
            )
            self.db.add(affinity)

        await self.db.flush()
        logger.info("upsert_user_character_affinity", f"Global affinity updated",
                   user_id=user_id, new_score=affinity.total_affinity_score)
        return affinity

    async def get_user_character_affinity(
        self,
        user_id: str,
        character_name: str
    ) -> Optional[UserCharacterAffinity]:
        """
        사용자의 특정 캐릭터 친밀도 조회

        Args:
            user_id: 사용자 ID
            character_name: 캐릭터 이름

        Returns:
            UserCharacterAffinity (없으면 None)
        """
        logger.debug("get_user_character_affinity", f"Fetching affinity for {character_name}",
                    user_id=user_id)

        stmt = select(UserCharacterAffinity).where(
            and_(
                UserCharacterAffinity.user_id == user_id,
                UserCharacterAffinity.character_name == character_name
            )
        )

        result = await self.db.execute(stmt)
        affinity = result.scalar_one_or_none()

        logger.debug("get_user_character_affinity", f"Affinity found: {affinity is not None}")
        return affinity

    # ============================================================
    # Entity Management
    # ============================================================

    async def save_entity(self, entity_data: Dict[str, Any]) -> Entity:
        """
        엔티티 저장 (UPSERT)

        Args:
            entity_data: 엔티티 정보 dict

        Returns:
            저장된 Entity
        """
        logger.info("save_entity", f"Saving entity: {entity_data.get('entity_name')}")

        # 기존 엔티티 조회 (type + canonical_name 기준)
        canonical_name = entity_data.get('canonical_name', entity_data['entity_name'])
        stmt = select(Entity).where(
            and_(
                Entity.entity_type == entity_data['entity_type'],
                Entity.canonical_name == canonical_name
            )
        )
        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            # 업데이트
            entity.mention_count += 1
            entity.last_updated_at = datetime.utcnow()
            if entity_data.get('description'):
                entity.description = entity_data['description']
            if entity_data.get('properties'):
                entity.properties = entity_data['properties']
            if entity_data.get('embedding'):
                entity.embedding = entity_data['embedding']
        else:
            # 생성
            entity = Entity(**entity_data, canonical_name=canonical_name)
            self.db.add(entity)

        await self.db.flush()
        logger.info("save_entity", f"Entity saved", entity_id=entity.entity_id)
        return entity

    async def save_relationship(self, relationship_data: Dict[str, Any]) -> EntityRelationship:
        """
        엔티티 간 관계 저장 (UPSERT)

        Args:
            relationship_data: 관계 정보 dict

        Returns:
            저장된 EntityRelationship
        """
        logger.info("save_relationship", f"Saving relationship: {relationship_data['relationship_type']}")

        # 기존 관계 조회
        stmt = select(EntityRelationship).where(
            and_(
                EntityRelationship.source_entity_id == relationship_data['source_entity_id'],
                EntityRelationship.target_entity_id == relationship_data['target_entity_id'],
                EntityRelationship.relationship_type == relationship_data['relationship_type']
            )
        )
        result = await self.db.execute(stmt)
        relationship = result.scalar_one_or_none()

        if relationship:
            # 업데이트
            relationship.mention_count += 1
            relationship.last_seen_at = datetime.utcnow()
            if relationship_data.get('strength'):
                relationship.strength = relationship_data['strength']
            if relationship_data.get('context'):
                relationship.context = relationship_data['context']
        else:
            # 생성
            relationship = EntityRelationship(**relationship_data)
            self.db.add(relationship)

        await self.db.flush()
        logger.info("save_relationship", f"Relationship saved", relationship_id=relationship.relationship_id)
        return relationship

    async def save_entity_mention(self, mention_data: Dict[str, Any]) -> EntityMention:
        """
        엔티티 언급 기록 저장

        Args:
            mention_data: 언급 정보 dict

        Returns:
            저장된 EntityMention
        """
        logger.info("save_entity_mention", f"Saving entity mention")

        mention = EntityMention(**mention_data)
        self.db.add(mention)
        await self.db.flush()

        logger.info("save_entity_mention", f"Mention saved", mention_id=mention.mention_id)
        return mention

    # ============================================================
    # Memory Management
    # ============================================================

    async def save_memory(self, memory_data: Dict[str, Any]) -> UserMemory:
        """
        사용자 장기 기억 저장

        Args:
            memory_data: 기억 정보 dict

        Returns:
            저장된 UserMemory
        """
        logger.info("save_memory", f"Saving memory for user {memory_data['user_id']}")

        memory = UserMemory(**memory_data)
        self.db.add(memory)
        await self.db.flush()

        logger.info("save_memory", f"Memory saved", memory_id=memory.memory_id)
        return memory

    async def get_user_memories(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[UserMemory]:
        """
        사용자 기억 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (선택)
            memory_type: 기억 유형 (선택)
            limit: 최대 개수

        Returns:
            UserMemory 리스트
        """
        logger.debug("get_user_memories", f"Fetching memories for user {user_id}")

        conditions = [UserMemory.user_id == user_id]
        if scenario_id:
            conditions.append(UserMemory.scenario_id == scenario_id)
        if memory_type:
            conditions.append(UserMemory.memory_type == memory_type)

        stmt = (
            select(UserMemory)
            .where(and_(*conditions))
            .order_by(UserMemory.importance_score.desc(), UserMemory.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        logger.debug("get_user_memories", f"Fetched {len(memories)} memories")
        return list(memories)
