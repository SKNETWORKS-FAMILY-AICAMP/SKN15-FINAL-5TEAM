"""
Sessions Feature - UseCase
세션 목록 및 관리 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .repository import SessionRepository
from .models import Session
from app.features.chat.repositories import DialogueRepository
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("Session")


class SessionUseCase:
    """
    [Layer 2] UseCase
    책임: 세션 관리 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = SessionRepository(db)
        self.dialogue_repository = DialogueRepository(db)
        from app.features.progression.repository import ProgressionRepository
        self.progression_repository = ProgressionRepository(db)

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        scenario_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        사용자 세션 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 페이징 크기
            offset: 페이징 오프셋
            scenario_id: 시나리오 ID 필터 (선택적)

        Returns:
            세션 목록
            [
                {
                    "session_id": str,
                    "scenario_id": str,
                    "scenario_title": str,
                    "current_stage": str,
                    "turn_count": int,
                    "last_dialogue": str,
                    "created_at": str,
                    "updated_at": str
                },
                ...
            ]
        """
        logger.info("list_user_sessions", "Listing user sessions",
                   user_id=user_id, limit=limit)

        # Repository로 세션 목록 조회
        sessions_db = await self.repository.list_user_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            scenario_id=scenario_id,
            is_active=True
        )

        sessions = []
        for session_tuple in sessions_db:
            # 튜플 언패킹: (Session, title, thumbnail_url, last_speaker, last_content)
            session, scenario_title, scenario_thumbnail, last_speaker, last_content = session_tuple

            # last_dialogue는 하위 호환성을 위해 유지
            last_dialogue = last_content if last_content else ""

            sessions.append({
                "session_id": str(session.session_id),
                "scenario_id": session.scenario_id,
                "scenario_title": scenario_title if scenario_title else session.scenario_id,
                "scenario_thumbnail": scenario_thumbnail,
                "current_stage": session.current_stage or "intro",
                "turn_count": session.turn_count or 0,
                "last_message_speaker": last_speaker,
                "last_message_content": last_content,
                "last_dialogue": last_dialogue,  # 하위 호환성
                "created_at": session.created_at.isoformat() if session.created_at else "",
                "updated_at": session.updated_at.isoformat() if session.updated_at else ""
            })

        logger.info("list_user_sessions", f"Retrieved {len(sessions)} sessions with scenario info",
                   user_id=user_id)

        return sessions

    async def get_session_detail(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        세션 상세 조회

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID (권한 체크용)

        Returns:
            세션 상세 정보
            {
                "session_id": str,
                "user_id": str,
                "scenario_id": str,
                "scenario_title": str,
                "current_stage": str,
                "turn_count": int,
                "state": Dict,  # 전체 게임 상태
                "created_at": str,
                "updated_at": str,
                "dialogues": List[Dict]  # 최근 대화 (10개)
            }
        """
        logger.info("get_session_detail", "Getting session detail",
                   session_id=session_id, user_id=user_id)

        # Repository로 세션 조회
        session = await self.repository.get_session(session_id)
        if not session:
            logger.warning("get_session_detail", "Session not found",
                          session_id=session_id)
            return None

        # 권한 체크
        if str(session.user_id) != user_id:
            logger.warning("get_session_detail", "Permission denied",
                          session_id=session_id, user_id=user_id)
            return None

        # 최근 대화 조회
        dialogues_db = await self.dialogue_repository.get_recent_dialogues(
            session_id=session_id,
            limit=10
        )

        dialogues = [
            {
                "speaker": d.speaker,
                "text": d.text,
                "emotion": d.emotion,
                "created_at": d.created_at.isoformat() if d.created_at else ""
            }
            for d in dialogues_db
        ]

        session_detail = {
            "session_id": str(session.session_id),
            "user_id": str(session.user_id),
            "scenario_id": session.scenario_id,
            "scenario_title": session.scenario_id,  # TODO: scenarios 테이블 조인 필요
            "current_stage": session.current_stage or "intro",
            "turn_count": session.turn_count or 0,
            "state": {
                "current_stage": session.current_stage,
                "turn_count": session.turn_count,
                "stage_turn": session.stage_turn,
                "conversation_summary": session.conversation_summary
            },
            "created_at": session.created_at.isoformat() if session.created_at else "",
            "updated_at": session.updated_at.isoformat() if session.updated_at else "",
            "dialogues": dialogues
        }

        logger.info("get_session_detail", "Session detail retrieved",
                   session_id=session_id)

        return session_detail

    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID (권한 체크용)

        Returns:
            삭제 성공 여부
        """
        logger.warning("delete_session", "Deleting session",
                      session_id=session_id, user_id=user_id)

        # Repository로 세션 조회
        session = await self.repository.get_session(session_id)
        if not session:
            logger.warning("delete_session", "Session not found",
                          session_id=session_id)
            return False

        # 권한 체크
        if str(session.user_id) != user_id:
            logger.warning("delete_session", "Permission denied",
                          session_id=session_id, user_id=user_id)
            return False

        async with self.db.begin():
            # Repository로 세션 삭제 (CASCADE로 대화도 함께 삭제됨)
            await self.repository.delete_session(session_id)

            logger.warning("delete_session", "Session deleted",
                          session_id=session_id)

        return True

    async def create_session(
        self,
        user_id: str,
        scenario_id: str
    ) -> Dict[str, Any]:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            생성된 세션 정보
            {
                "session_id": str,
                "user_id": str,
                "scenario_id": str,
                "state": Dict,
                "created_at": str
            }
        """
        logger.info("create_session", "Creating session",
                   user_id=user_id, scenario_id=scenario_id)

        # 세션 객체 생성
        session_id = uuid.uuid4()
        new_session = Session(
            session_id=session_id,
            user_id=user_id,
            scenario_id=scenario_id,
            current_stage="intro",
            turn_count=0,
            stage_turn=0,
            is_active=True
        )

        async with self.db.begin():
            # Repository로 세션 저장
            saved_session = await self.repository.save_session(new_session)

            logger.info("create_session", "Session created",
                       session_id=str(session_id))

        return {
            "session_id": str(saved_session.session_id),
            "user_id": str(saved_session.user_id),
            "scenario_id": saved_session.scenario_id,
            "state": {
                "current_stage": saved_session.current_stage,
                "turn_count": saved_session.turn_count,
                "stage_turn": saved_session.stage_turn
            },
            "created_at": saved_session.created_at.isoformat() if saved_session.created_at else ""
        }

    async def get_last_session(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자의 특정 시나리오 최근 세션 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            최근 세션 정보 또는 None
        """
        logger.info("get_last_session", "Getting last session",
                   user_id=user_id, scenario_id=scenario_id)

        session = await self.repository.get_last_session(user_id, scenario_id)

        if not session:
            logger.info("get_last_session", "No last session found")
            return None

        return {
            "session_id": str(session.session_id),
            "scenario_id": session.scenario_id,
            "current_stage": session.current_stage or "intro",
            "turn_count": session.turn_count or 0,
            "updated_at": session.updated_at.isoformat() if session.updated_at else ""
        }

    async def get_session_dialogues(
        self,
        session_id: str,
        user_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        세션의 대화 히스토리 조회

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID (권한 체크용)
            limit: 최대 대화 개수

        Returns:
            대화 목록
            [
                {
                    "id": int,
                    "speaker": str,
                    "content": str,
                    "emotion": str,
                    "turn_number": int,
                    "created_at": str
                },
                ...
            ]
        """
        logger.info("get_session_dialogues", "Getting session dialogues",
                   session_id=session_id, user_id=user_id, limit=limit)

        # 권한 체크
        session = await self.repository.get_session(session_id)
        if not session or str(session.user_id) != user_id:
            logger.warning("get_session_dialogues", "Permission denied or session not found",
                          session_id=session_id, user_id=user_id)
            return []

        # 1. NPC 대화 조회
        dialogues_db = await self.dialogue_repository.get_recent_dialogues(
            session_id=session_id,
            limit=limit * 2  # 유저 입력과 합쳐질 것을 고려하여 더 많이 조회
        )

        # 2. 유저 입력 조회
        user_inputs = await self.progression_repository.get_user_inputs(
            session_id=session_id,
            limit=limit * 2
        )

        # 3. 유저 이름 가져오기
        user_name = session.user_name if session else "User"

        # 4. 통합 메시지 리스트 생성
        all_messages = []

        # NPC 대화 추가
        for d in dialogues_db:
            all_messages.append({
                "id": d.id,
                "speaker": d.speaker,
                "content": d.content,
                "emotion": d.emotion or "neutral",
                "emotion_intensity": d.emotion_intensity,
                "turn_number": d.turn_number,
                "order_index": d.order_index or 0,
                "created_at": d.created_at.isoformat() if d.created_at else "",
                "timestamp": d.created_at,
                "order": d.turn_number * 1000 + (d.order_index or 0) + 1
            })

        # 유저 입력 추가
        for user_input in user_inputs:
            all_messages.append({
                "id": f"user_{user_input.id}",  # 유저 입력 ID는 문자열로 구분
                "speaker": user_name,
                "content": user_input.user_input,
                "emotion": "neutral",
                "emotion_intensity": 1.0,
                "turn_number": user_input.turn_number,
                "order_index": 0,
                "created_at": user_input.timestamp.isoformat() if user_input.timestamp else "",
                "timestamp": user_input.timestamp,
                "order": user_input.turn_number * 1000  # 유저 입력은 턴의 시작
            })

        # 5. 시간순 정렬 (오래된 것부터 → 최신이 맨 뒤)
        all_messages.sort(key=lambda x: x["order"])

        # 6. limit 적용
        all_messages = all_messages[-limit:] if len(all_messages) > limit else all_messages

        # 7. order 필드 제거 (프론트엔드에 불필요)
        for msg in all_messages:
            msg.pop("order", None)
            msg.pop("timestamp", None)

        logger.info("get_session_dialogues",
                   f"Retrieved {len(all_messages)} messages (NPC: {len(dialogues_db)}, User: {len(user_inputs)})",
                   session_id=session_id)

        return all_messages
