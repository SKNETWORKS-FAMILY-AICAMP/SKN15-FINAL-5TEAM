"""
Admin Feature - UseCase
관리자 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.logging import get_usecase_logger
from .repository import AdminRepository

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
