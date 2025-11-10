"""
Admin Feature - Repository
관리자용 DB 조회 레이어
Layer 4: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.features.sessions.models import Session
from app.features.chat.models import DialogueTurn
from app.features.auth.models import User
from app.core.logging import get_repository_logger

logger = get_repository_logger("Admin")


class AdminRepository:
    """
    [Layer 4] Repository
    책임: 관리자용 DB CRUD, 복잡한 JOIN 쿼리
    금지: 비즈니스 로직, 트랜잭션 관리 (UseCase가 담당)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_dialogue_sessions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        모든 대화 세션 목록 조회 (관리자용)

        sessions 테이블을 users 테이블과 JOIN하여 조회

        Args:
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            세션 정보 리스트
            [
                {
                    "session_id": str,
                    "user_id": str,
                    "username": str,
                    "scenario_id": str,
                    "current_stage": str,
                    "turn_count": int,
                    "is_active": bool,
                    "created_at": datetime,
                    "updated_at": datetime
                },
                ...
            ]
        """
        logger.info("get_all_dialogue_sessions", f"Fetching sessions (limit={limit}, offset={offset})")

        # LEFT JOIN으로 user 정보 포함
        stmt = (
            select(
                Session.session_id,
                Session.user_id,
                User.username,
                Session.scenario_id,
                Session.current_stage,
                Session.turn_count,
                Session.is_active,
                Session.created_at,
                Session.updated_at
            )
            .outerjoin(User, Session.user_id == User.user_id)
            .order_by(desc(Session.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        sessions = []
        for row in rows:
            sessions.append({
                "session_id": str(row.session_id),
                "user_id": str(row.user_id) if row.user_id else None,
                "username": row.username if row.username else "Anonymous",
                "scenario_id": row.scenario_id,
                "current_stage": row.current_stage,
                "turn_count": row.turn_count,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at
            })

        logger.info("get_all_dialogue_sessions", f"Retrieved {len(sessions)} sessions")
        return sessions

    async def get_dialogue_turns_by_session_id(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        특정 세션의 모든 대화 턴 조회

        Args:
            session_id: 세션 ID

        Returns:
            대화 턴 리스트
            [
                {
                    "id": int,
                    "session_id": str,
                    "user_id": str,
                    "scenario_id": str,
                    "turn_count": int,
                    "speaker": str,
                    "text": str,
                    "emotion": str,
                    "stage_tag": str,
                    "affinity_delta": float,
                    "created_at": datetime
                },
                ...
            ]
        """
        logger.info("get_dialogue_turns_by_session_id", f"Fetching turns for session {session_id}")

        stmt = (
            select(DialogueTurn)
            .where(DialogueTurn.session_id == session_id)
            .order_by(DialogueTurn.turn_count.asc())
        )

        result = await self.db.execute(stmt)
        turns_orm = result.scalars().all()

        turns = []
        for turn in turns_orm:
            turns.append({
                "id": turn.id,
                "session_id": turn.session_id,
                "user_id": turn.user_id,
                "scenario_id": turn.scenario_id,
                "turn_count": turn.turn_count,
                "speaker": turn.speaker,
                "text": turn.text,
                "emotion": turn.emotion,
                "stage_tag": turn.stage_tag,
                "affinity_delta": turn.affinity_delta,
                "created_at": turn.created_at
            })

        logger.info("get_dialogue_turns_by_session_id", f"Retrieved {len(turns)} turns")
        return turns

    async def get_session_count(self) -> int:
        """
        전체 세션 개수 조회

        Returns:
            세션 개수
        """
        stmt = select(func.count(Session.session_id))
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count

    # ============================================================
    # User Management
    # ============================================================

    async def list_all_users(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        모든 사용자 목록 조회 (관리자용)

        Args:
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            사용자 ORM 객체 리스트
        """
        logger.info("list_all_users", f"Fetching users (limit={limit}, offset={offset})")

        stmt = (
            select(User)
            .order_by(desc(User.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        users = result.scalars().all()

        logger.info("list_all_users", f"Retrieved {len(users)} users")
        return list(users)

    async def get_user_details_by_id(
        self,
        user_id: str
    ) -> Optional[User]:
        """
        특정 사용자 상세 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 ORM 객체 또는 None
        """
        logger.info("get_user_details_by_id", f"Fetching user details: {user_id}")

        stmt = select(User).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            logger.info("get_user_details_by_id", f"User found: {user.username}")
        else:
            logger.warning("get_user_details_by_id", f"User not found: {user_id}")

        return user

    async def get_user_count(self) -> int:
        """
        전체 사용자 개수 조회

        Returns:
            사용자 개수
        """
        stmt = select(func.count(User.user_id))
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count
