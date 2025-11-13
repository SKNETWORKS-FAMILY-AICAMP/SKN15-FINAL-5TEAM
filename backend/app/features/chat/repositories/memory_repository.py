"""
Memories Feature - Repository
pgvector를 사용한 의미적 검색 지원
Layer 3: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.user_memory import UserMemory
from app.core.logging import get_repository_logger

logger = get_repository_logger("Memories")


class MemoryRepository:
    """
    [Layer 3] Repository
    책임: 데이터베이스 CRUD, pgvector 유사도 검색
    금지: 비즈니스 로직, HTTP 처리
    """

    def __init__(self, db: AsyncSession):
        """
        Repository 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def create_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        embedding: Optional[List[float]] = None,
        scenario_id: Optional[str] = None,
        importance_score: Optional[float] = None
    ) -> UserMemory:
        """
        기억 생성

        Args:
            user_id: 사용자 ID
            content: 기억 내용 (memory_value로 저장됨)
            memory_type: 기억 유형 (fact, event, relationship, preference)
            embedding: 임베딩 벡터 (1536차원)
            scenario_id: 시나리오 ID (source_session_id로 저장)
            importance_score: 중요도 점수 (0.0 ~ 1.0, importance로 저장)

        Returns:
            생성된 UserMemory
        """
        # memory_key 생성 (memory_type, 타임스탬프, UUID 기반 - 고유성 보장)
        import uuid
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]  # UUID 앞 8자리
        memory_key = f"{memory_type}_{timestamp}_{unique_id}"

        memory = UserMemory(
            user_id=user_id,
            memory_key=memory_key,
            memory_value=content,  # content -> memory_value
            memory_type=memory_type,
            embedding=embedding,
            source_session_id=scenario_id,  # scenario_id를 source_session_id로 매핑
            importance=importance_score or 0.5,  # importance_score -> importance
            access_count=0,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.db.add(memory)
        await self.db.flush()

        logger.info("create_memory", f"Memory created: {memory.id}",
                   user_id=user_id, type=memory_type, key=memory_key)

        return memory

    async def get_memory(self, memory_id: int) -> Optional[UserMemory]:
        """
        기억 조회

        Args:
            memory_id: 기억 ID

        Returns:
            UserMemory 또는 None
        """
        result = await self.db.execute(
            select(UserMemory).where(UserMemory.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def search_similar_memories(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        임베딩 기반 유사 기억 검색 (pgvector cosine similarity)

        Args:
            query_embedding: 검색 임베딩 벡터
            user_id: 사용자 ID 필터
            scenario_id: 시나리오 ID 필터
            memory_type: 기억 유형 필터
            limit: 결과 개수
            similarity_threshold: 유사도 임계값

        Returns:
            유사 기억 리스트 (유사도 포함)
        """
        # pgvector의 cosine similarity 사용
        # 1 - (embedding <=> query) = cosine similarity
        similarity_expr = 1 - UserMemory.embedding.cosine_distance(query_embedding)

        # 쿼리 구성
        query = select(
            UserMemory,
            similarity_expr.label("similarity")
        ).where(
            UserMemory.embedding.isnot(None)
        )

        # 필터 추가
        if user_id:
            query = query.where(UserMemory.user_id == user_id)
        if scenario_id:
            query = query.where(UserMemory.scenario_id == scenario_id)
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)

        # 유사도 임계값 및 정렬
        query = query.where(similarity_expr >= similarity_threshold)
        query = query.order_by(similarity_expr.desc())
        query = query.limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        # 결과 변환
        memories = []
        for row in rows:
            memory = row[0]
            similarity = row[1]

            memories.append({
                "memory_id": memory.id,  # id 필드 사용
                "content": memory.memory_value,  # memory_value 필드 사용
                "memory_key": memory.memory_key,
                "memory_type": memory.memory_type,
                "importance_score": memory.importance,  # importance 필드 사용
                "similarity": float(similarity),
                "created_at": memory.created_at.isoformat() if memory.created_at else None
            })

        logger.info("search_similar_memories", f"Found {len(memories)} similar memories",
                   user_id=user_id, threshold=similarity_threshold)

        return memories

    async def get_user_memories(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 100
    ) -> List[UserMemory]:
        """
        사용자의 기억 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID 필터 (source_session_id로 매핑됨)
            memory_type: 기억 유형 필터
            limit: 결과 개수

        Returns:
            UserMemory 리스트
        """
        query = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.is_active == True  # 활성화된 메모리만 조회
        )

        if scenario_id:
            query = query.where(UserMemory.source_session_id == scenario_id)  # scenario_id -> source_session_id
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)

        query = query.order_by(UserMemory.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        memories = result.scalars().all()

        logger.info("get_user_memories", f"Retrieved {len(memories)} memories",
                   user_id=user_id, scenario_id=scenario_id)

        return list(memories)

    async def update_access_stats(self, memory_id: int):
        """
        기억 액세스 통계 업데이트

        Args:
            memory_id: 기억 ID
        """
        memory = await self.get_memory(memory_id)
        if memory:
            memory.access_count = (memory.access_count or 0) + 1
            memory.last_accessed_at = datetime.utcnow()
            await self.db.flush()

            logger.debug("update_access_stats", f"Access count updated: {memory.access_count}",
                        memory_id=memory_id)

    async def delete_memory(self, memory_id: int) -> bool:
        """
        기억 삭제

        Args:
            memory_id: 기억 ID

        Returns:
            삭제 성공 여부
        """
        memory = await self.get_memory(memory_id)
        if not memory:
            logger.warning("delete_memory", f"Memory not found: {memory_id}")
            return False

        await self.db.delete(memory)
        await self.db.flush()

        logger.info("delete_memory", f"Memory deleted: {memory_id}")
        return True
