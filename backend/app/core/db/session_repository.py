"""
Session Repository (Hybrid)
Redis (Hot) + PostgreSQL (Cold) 하이브리드 세션 저장소
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import redis.asyncio as redis
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

from .models import Session
from app.core.logging import get_repository_logger

logger = get_repository_logger("SessionRepository")


class SessionRepository:
    """
    [Layer 4] Hybrid Session Repository

    전략:
    - Hot Storage (Redis): 최근 1시간 이내 활성 세션
    - Cold Storage (PostgreSQL): 모든 세션 영구 저장
    - TTL: Redis 1시간 후 자동 삭제
    """

    # Redis TTL (1시간)
    REDIS_TTL = 3600

    # Redis 키 프리픽스
    REDIS_PREFIX = "session:"

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    def _get_redis_key(self, session_id: str) -> str:
        """Redis 키 생성"""
        return f"{self.REDIS_PREFIX}{session_id}"

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회 (Hybrid)

        1. Redis 조회 (Hot)
        2. Redis 미스 시 PostgreSQL 조회 (Cold)
        3. PostgreSQL에서 찾으면 Redis에 캐싱

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 dict (없으면 None)
        """
        logger.debug("get_session", f"Fetching session {session_id}")

        # 1. Redis 조회 (Hot)
        redis_key = self._get_redis_key(session_id)
        cached = await self.redis.get(redis_key)

        if cached:
            logger.debug("get_session", f"Cache HIT - Redis", session_id=session_id)
            session_data = json.loads(cached)
            # TTL 갱신
            await self.redis.expire(redis_key, self.REDIS_TTL)
            return session_data

        logger.debug("get_session", f"Cache MISS - Checking PostgreSQL", session_id=session_id)

        # 2. PostgreSQL 조회 (Cold)
        stmt = select(Session).where(
            and_(
                Session.session_id == session_id,
                Session.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            logger.debug("get_session", f"Session not found", session_id=session_id)
            return None

        # 3. Dict 변환 및 Redis 캐싱
        session_data = {
            "session_id": str(session_obj.session_id),
            "scenario_id": session_obj.scenario_id,
            "user_name": session_obj.user_name,
            "user_id": str(session_obj.user_id) if session_obj.user_id else None,
            "current_stage": session_obj.current_stage,
            "turn_count": session_obj.turn_count,
            "stage_turn": session_obj.stage_turn,
            "final_ending": session_obj.final_ending,
            "is_active": session_obj.is_active,
            "conversation_summary": session_obj.conversation_summary,
            "summary_updated_at": session_obj.summary_updated_at.isoformat() if session_obj.summary_updated_at else None,
            "summary_turn_count": session_obj.summary_turn_count,
            "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
            "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else None,
        }

        # Redis에 캐싱
        await self.redis.setex(
            redis_key,
            self.REDIS_TTL,
            json.dumps(session_data, ensure_ascii=False)
        )
        logger.debug("get_session", f"Cached to Redis", session_id=session_id)

        return session_data

    async def save_session(
        self,
        session_id: str,
        session_data: Dict[str, Any]
    ) -> Session:
        """
        세션 저장 (Hybrid UPSERT)

        1. PostgreSQL에 UPSERT
        2. Redis에 캐싱

        Args:
            session_id: 세션 ID
            session_data: 세션 데이터

        Returns:
            저장된 Session 객체
        """
        logger.info("save_session", f"Saving session {session_id}")

        # 1. PostgreSQL UPSERT
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if session_obj:
            # 업데이트
            for key, value in session_data.items():
                if hasattr(session_obj, key):
                    setattr(session_obj, key, value)
            session_obj.updated_at = datetime.utcnow()
        else:
            # 생성
            session_obj = Session(
                session_id=session_id,
                **session_data
            )
            self.db.add(session_obj)

        await self.db.flush()
        logger.info("save_session", f"Saved to PostgreSQL", session_id=session_id)

        # 2. Redis 캐싱
        redis_key = self._get_redis_key(session_id)
        cache_data = {
            "session_id": str(session_obj.session_id),
            "scenario_id": session_obj.scenario_id,
            "user_name": session_obj.user_name,
            "user_id": str(session_obj.user_id) if session_obj.user_id else None,
            "current_stage": session_obj.current_stage,
            "turn_count": session_obj.turn_count,
            "stage_turn": session_obj.stage_turn,
            "final_ending": session_obj.final_ending,
            "is_active": session_obj.is_active,
            "conversation_summary": session_obj.conversation_summary,
            "summary_updated_at": session_obj.summary_updated_at.isoformat() if session_obj.summary_updated_at else None,
            "summary_turn_count": session_obj.summary_turn_count,
            "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
            "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else None,
        }

        await self.redis.setex(
            redis_key,
            self.REDIS_TTL,
            json.dumps(cache_data, ensure_ascii=False)
        )
        logger.info("save_session", f"Cached to Redis", session_id=session_id)

        return session_obj

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Session]:
        """
        세션 부분 업데이트

        Args:
            session_id: 세션 ID
            updates: 업데이트할 필드들

        Returns:
            업데이트된 Session (없으면 None)
        """
        logger.info("update_session", f"Updating session {session_id}", fields=list(updates.keys()))

        # PostgreSQL 업데이트
        stmt = select(Session).where(Session.session_id == session_id)
        result = await self.db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            logger.warning("update_session", f"Session not found", session_id=session_id)
            return None

        for key, value in updates.items():
            if hasattr(session_obj, key):
                setattr(session_obj, key, value)
        session_obj.updated_at = datetime.utcnow()

        await self.db.flush()

        # Redis 캐시 무효화 (다음 조회 시 재생성)
        redis_key = self._get_redis_key(session_id)
        await self.redis.delete(redis_key)
        logger.info("update_session", f"Updated and invalidated cache", session_id=session_id)

        return session_obj

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제 (소프트 삭제)

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_session", f"Deleting session {session_id}")

        # PostgreSQL 소프트 삭제
        stmt = (
            update(Session)
            .where(Session.session_id == session_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        await self.db.flush()

        # Redis 캐시 삭제
        redis_key = self._get_redis_key(session_id)
        await self.redis.delete(redis_key)

        success = result.rowcount > 0
        logger.warning("delete_session", f"Deleted: {success}", session_id=session_id)
        return success

    async def get_user_recent_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> list[Session]:
        """
        사용자의 최근 세션 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            Session 리스트
        """
        logger.debug("get_user_recent_sessions", f"Fetching recent sessions", user_id=user_id)

        stmt = (
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True
                )
            )
            .order_by(Session.updated_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        sessions = result.scalars().all()

        logger.debug("get_user_recent_sessions", f"Found {len(sessions)} sessions")
        return list(sessions)

    async def get_active_session_count(self, user_id: str) -> int:
        """
        사용자의 활성 세션 개수

        Args:
            user_id: 사용자 ID

        Returns:
            활성 세션 개수
        """
        from sqlalchemy import func

        stmt = select(func.count(Session.session_id)).where(
            and_(
                Session.user_id == user_id,
                Session.is_active == True
            )
        )

        result = await self.db.execute(stmt)
        count = result.scalar_one()

        return count

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        오래된 비활성 세션 정리

        Args:
            days: N일 이전 세션 삭제

        Returns:
            삭제된 세션 수
        """
        logger.info("cleanup_old_sessions", f"Cleaning up sessions older than {days} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            update(Session)
            .where(
                and_(
                    Session.is_active == False,
                    Session.updated_at < cutoff_date
                )
            )
            .values(is_active=False)
        )

        result = await self.db.execute(stmt)
        await self.db.flush()

        count = result.rowcount
        logger.info("cleanup_old_sessions", f"Cleaned up {count} sessions")
        return count
