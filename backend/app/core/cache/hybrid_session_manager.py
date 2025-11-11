"""
HybridSessionManager - Repository + Cache 통합
현재 4-layer 아키텍처에 맞게 구성
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.sessions.repository import SessionRepository
from app.core.cache.cache_manager import CacheManager, get_cache_manager
from app.core.logging import get_repository_logger

logger = get_repository_logger("HybridSession")


class HybridSessionManager:
    """
    하이브리드 세션 관리자

    전략:
    - 읽기: Cache-first (Redis -> PostgreSQL fallback)
    - 쓰기: Write-through (Redis + PostgreSQL 동시)
    - TTL: Redis에만 적용
    """

    def __init__(
        self,
        db: AsyncSession,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Args:
            db: 데이터베이스 세션
            cache_manager: CacheManager 인스턴스 (None이면 생성)
        """
        self.repository = SessionRepository(db)
        self.cache = cache_manager or get_cache_manager()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회 (Cache-first)

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        # 1. 캐시에서 조회
        cached = self.cache.get_session(session_id)
        if cached:
            logger.debug("get_session", f"Cache HIT: {session_id}")
            return cached

        # 2. DB에서 조회
        session_model = await self.repository.get_session(session_id)
        if not session_model:
            logger.debug("get_session", f"Not found: {session_id}")
            return None

        # 3. Dict로 변환
        session_data = {
            "session_id": str(session_model.session_id),
            "user_id": str(session_model.user_id),
            "scenario_id": session_model.scenario_id,
            "current_stage": session_model.current_stage,
            "turn_count": session_model.turn_count,
            "stage_turn": session_model.stage_turn,
            "is_active": session_model.is_active,
            "conversation_summary": session_model.conversation_summary,
            "summary_turn_count": session_model.summary_turn_count,
        }

        # 4. 캐시에 저장 (warming)
        self.cache.set_session(session_id, session_data)

        logger.debug("get_session", f"DB HIT: {session_id}")
        return session_data

    async def save_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        세션 저장 (Write-through)

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터
            ttl: 캐시 TTL (None이면 기본값 사용)

        Returns:
            성공 여부
        """
        try:
            # 1. DB 업데이트
            await self.repository.update_session_state(
                session_id=session_id,
                current_stage=session_data.get("current_stage"),
                turn_count=session_data.get("turn_count"),
                stage_turn=session_data.get("stage_turn"),
                conversation_summary=session_data.get("conversation_summary"),
                is_active=session_data.get("is_active"),
            )

            # 2. 캐시 저장
            self.cache.set_session(session_id, session_data, ttl)

            logger.debug("save_session", f"Saved: {session_id}")
            return True

        except Exception as e:
            logger.error("save_session", f"Failed: {e}", exc=e)
            return False

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (soft delete)

        Args:
            session_id: 세션 ID

        Returns:
            성공 여부
        """
        try:
            # 1. DB: is_active = false
            await self.repository.deactivate_session(session_id)

            # 2. 캐시에서 제거
            self.cache.delete_session(session_id)

            logger.info("delete_session", f"Deleted: {session_id}")
            return True

        except Exception as e:
            logger.error("delete_session", f"Failed: {e}", exc=e)
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        return self.cache.get_stats()
