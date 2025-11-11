"""
Admin Feature - UseCase
관리자 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.logging import get_usecase_logger
from .repository import AdminRepository
from app.features.chat.repositories.entity_repository import EntityRepository

logger = get_usecase_logger("Admin")


class AdminUseCase:
    """
    [Layer 2] UseCase
    책임: 관리자 기능 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = AdminRepository(db)
        self.entity_repository = EntityRepository(db)

    async def list_dialogue_sessions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        모든 대화 세션 목록 조회

        Args:
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            {
                "sessions": List[Dict],
                "total": int
            }
        """
        logger.info("list_dialogue_sessions", f"Listing sessions (limit={limit}, offset={offset})")

        # Repository로 세션 목록 조회
        sessions = await self.repository.get_all_dialogue_sessions(
            limit=limit,
            offset=offset
        )

        # 전체 개수 조회 (페이징 정보용)
        total = await self.repository.get_session_count()

        logger.info("list_dialogue_sessions", f"Retrieved {len(sessions)} sessions (total={total})")

        return {
            "sessions": sessions,
            "total": total
        }

    async def get_dialogue_session_detail(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        특정 세션의 대화 내역 상세 조회

        Args:
            session_id: 세션 ID

        Returns:
            {
                "session_id": str,
                "turns": List[Dict],
                "total": int
            }
        """
        logger.info("get_dialogue_session_detail", f"Getting session detail: {session_id}")

        # Repository로 대화 턴 조회
        turns = await self.repository.get_dialogue_turns_by_session_id(session_id)

        logger.info("get_dialogue_session_detail", f"Retrieved {len(turns)} turns")

        return {
            "session_id": session_id,
            "turns": turns,
            "total": len(turns)
        }

    # ============================================================
    # User Management
    # ============================================================

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        모든 사용자 목록 조회

        Args:
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            {
                "users": List[User ORM],
                "total": int
            }
        """
        logger.info("list_users", f"Listing users (limit={limit}, offset={offset})")

        # Repository로 사용자 목록 조회
        users = await self.repository.list_all_users(
            limit=limit,
            offset=offset
        )

        # 전체 개수 조회 (페이징 정보용)
        total = await self.repository.get_user_count()

        logger.info("list_users", f"Retrieved {len(users)} users (total={total})")

        return {
            "users": users,
            "total": total
        }

    async def get_user_details(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        특정 사용자 상세 조회

        Args:
            user_id: 사용자 ID

        Returns:
            User ORM 객체 또는 None

        Raises:
            ValueError: 사용자를 찾을 수 없는 경우
        """
        logger.info("get_user_details", f"Getting user details: {user_id}")

        # Repository로 사용자 조회
        user = await self.repository.get_user_details_by_id(user_id)

        if not user:
            logger.warning("get_user_details", f"User not found: {user_id}")
            raise ValueError(f"User not found: {user_id}")

        logger.info("get_user_details", f"User retrieved: {user.username}")

        return user

    # ============================================================
    # Graph RAG Entity Management
    # ============================================================

    async def list_entities(
        self,
        query: str = None,
        entity_type: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        모든 엔티티 목록 조회 (관리자용)

        Args:
            query: 검색 쿼리 (엔티티 이름/설명 필터)
            entity_type: 엔티티 타입 필터
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            {
                "entities": List[Entity ORM],
                "total": int
            }
        """
        logger.info("list_entities", f"Listing entities (limit={limit}, offset={offset})",
                   query=query, entity_type=entity_type)

        # EntityRepository로 엔티티 검색
        entities, total = await self.entity_repository.search_entities(
            query=query,
            entity_type=entity_type,
            limit=limit,
            offset=offset
        )

        logger.info("list_entities", f"Retrieved {len(entities)} entities (total={total})")

        return {
            "entities": entities,
            "total": total
        }

    async def get_entity_relationships(
        self,
        entity_id: int,
        direction: str = "both"
    ) -> Dict[str, Any]:
        """
        특정 엔티티의 관계 조회

        Args:
            entity_id: 엔티티 ID
            direction: 관계 방향 (outgoing, incoming, both)

        Returns:
            {
                "entity_id": int,
                "relationships": List[EntityRelationship ORM],
                "total": int
            }

        Raises:
            ValueError: 엔티티를 찾을 수 없는 경우
        """
        logger.info("get_entity_relationships", f"Getting relationships for entity: {entity_id}",
                   direction=direction)

        # 엔티티 존재 여부 확인
        entity = await self.entity_repository.get_entity_by_id(entity_id)
        if not entity:
            logger.warning("get_entity_relationships", f"Entity not found: {entity_id}")
            raise ValueError(f"Entity not found: {entity_id}")

        # EntityRepository로 관계 조회
        relationships = await self.entity_repository.get_entity_relationships(
            entity_id=entity_id,
            direction=direction
        )

        logger.info("get_entity_relationships", f"Retrieved {len(relationships)} relationships")

        return {
            "entity_id": entity_id,
            "relationships": relationships,
            "total": len(relationships)
        }
