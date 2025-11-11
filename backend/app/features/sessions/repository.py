"""
Sessions Feature - Repository
세션 DB 접근 레이어 (CRUD)
Layer 4: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, literal
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from .models import Session
from app.features.scenarios.models import Scenarios
from app.features.chat.models import DialogueTurn
from app.core.logging import get_repository_logger

logger = get_repository_logger("Session")


class SessionRepository:
    """
    [Layer 4] Repository
    책임: Session 테이블 CRUD, 쿼리 최적화
    금지: 비즈니스 로직, 트랜잭션 관리 (UseCase가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        Repository 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            Session 객체 또는 None
        """
        logger.debug("get_session", "Fetching session", session_id=session_id)

        stmt = select(Session).where(Session.session_id == uuid.UUID(session_id))
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            logger.debug("get_session", "Session found", session_id=session_id)
        else:
            logger.debug("get_session", "Session not found", session_id=session_id)

        return session

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        scenario_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Tuple[Session, Optional[str], Optional[str], Optional[str], Optional[str]]]:
        """
        사용자 세션 목록 조회 (시나리오 정보 및 마지막 대화 포함)

        Args:
            user_id: 사용자 ID
            limit: 페이징 크기
            offset: 페이징 오프셋
            scenario_id: 시나리오 ID 필터 (선택적)
            is_active: 활성 상태 필터 (선택적)

        Returns:
            (Session, title, thumbnail_url, last_speaker, last_content) 튜플 리스트 (최신순)
        """
        logger.debug("list_user_sessions", "Listing sessions with scenario info", user_id=user_id, limit=limit)

        conditions = [Session.user_id == user_id]

        if scenario_id:
            conditions.append(Session.scenario_id == scenario_id)

        if is_active is not None:
            conditions.append(Session.is_active == is_active)

        # 마지막 대화를 가져오는 서브쿼리 (speaker != 'user')
        last_dialogue_subq = (
            select(
                DialogueTurn.session_id,
                DialogueTurn.speaker,
                DialogueTurn.text
            )
            .where(
                and_(
                    DialogueTurn.session_id == Session.session_id.cast(String),
                    DialogueTurn.speaker != 'user'
                )
            )
            .order_by(desc(DialogueTurn.turn_count), desc(DialogueTurn.id))
            .limit(1)
            .correlate(Session)
            .lateral("last_dialogue")
        )

        stmt = (
            select(
                Session,
                Scenarios.title,
                Scenarios.thumbnail_url,
                last_dialogue_subq.c.speaker,
                last_dialogue_subq.c.text
            )
            .outerjoin(Scenarios, Session.scenario_id == Scenarios.scenario_id)
            .outerjoin(last_dialogue_subq, literal(True))
            .where(and_(*conditions))
            .order_by(desc(Session.updated_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        sessions = result.all()

        logger.debug("list_user_sessions", f"Found {len(sessions)} sessions with details", user_id=user_id)
        return sessions

    async def get_last_session(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[Session]:
        """
        사용자의 특정 시나리오 최근 세션 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            가장 최근 세션 또는 None
        """
        logger.debug("get_last_session", "Fetching last session",
                    user_id=user_id, scenario_id=scenario_id)

        stmt = (
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.scenario_id == scenario_id,
                    Session.is_active == True
                )
            )
            .order_by(desc(Session.updated_at))
            .limit(1)
        )

        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            logger.debug("get_last_session", "Last session found", session_id=str(session.session_id))
        else:
            logger.debug("get_last_session", "No last session found")

        return session

    async def save_session(self, session: Session) -> Session:
        """
        세션 저장 (새로 생성 또는 업데이트)

        Args:
            session: Session 인스턴스

        Returns:
            저장된 Session
        """
        logger.info("save_session", "Saving session", session_id=str(session.session_id))

        self.db.add(session)
        await self.db.flush()

        logger.info("save_session", "Session saved", session_id=str(session.session_id))
        return session

    async def update_session_state(
        self,
        session_id: str,
        current_stage: Optional[str] = None,
        turn_count: Optional[int] = None,
        stage_turn: Optional[int] = None,
        conversation_summary: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """
        세션 상태 업데이트

        Args:
            session_id: 세션 ID
            current_stage: 현재 스테이지
            turn_count: 총 턴 수
            stage_turn: 스테이지 턴 수
            conversation_summary: 대화 요약
            is_active: 활성 상태

        Returns:
            업데이트 성공 여부
        """
        logger.info("update_session_state", "Updating session", session_id=session_id)

        session = await self.get_session(session_id)
        if not session:
            logger.warning("update_session_state", "Session not found", session_id=session_id)
            return False

        if current_stage is not None:
            session.current_stage = current_stage

        if turn_count is not None:
            session.turn_count = turn_count

        if stage_turn is not None:
            session.stage_turn = stage_turn

        if conversation_summary is not None:
            session.conversation_summary = conversation_summary
            session.summary_updated_at = datetime.utcnow()
            session.summary_turn_count = turn_count or session.turn_count

        if is_active is not None:
            session.is_active = is_active

        session.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info("update_session_state", "Session updated", session_id=session_id)
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_session", "Deleting session", session_id=session_id)

        session = await self.get_session(session_id)
        if not session:
            logger.warning("delete_session", "Session not found", session_id=session_id)
            return False

        await self.db.delete(session)
        await self.db.flush()

        logger.warning("delete_session", "Session deleted", session_id=session_id)
        return True

    async def count_user_sessions(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        사용자 세션 개수 카운트

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID 필터 (선택적)
            is_active: 활성 상태 필터 (선택적)

        Returns:
            세션 개수
        """
        logger.debug("count_user_sessions", "Counting sessions", user_id=user_id)

        conditions = [Session.user_id == user_id]

        if scenario_id:
            conditions.append(Session.scenario_id == scenario_id)

        if is_active is not None:
            conditions.append(Session.is_active == is_active)

        stmt = select(func.count(Session.session_id)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        count = result.scalar_one()

        logger.debug("count_user_sessions", f"Count: {count}", user_id=user_id, count=count)
        return count

    async def deactivate_session(self, session_id: str) -> bool:
        """
        세션 비활성화

        Args:
            session_id: 세션 ID

        Returns:
            비활성화 성공 여부
        """
        logger.info("deactivate_session", "Deactivating session", session_id=session_id)

        return await self.update_session_state(session_id, is_active=False)
