"""
Sessions Feature - UseCase
세션 목록 및 관리 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

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
        # TODO: SessionRepository, ChatRepository 생성 필요
        # self.repository = SessionRepository(db)
        # self.chat_repository = ChatRepository(db)

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

        # TODO: Repository로 세션 목록 조회
        # sessions = await self.repository.list_user_sessions(
        #     user_id=user_id,
        #     limit=limit,
        #     offset=offset,
        #     scenario_id=scenario_id
        # )

        # 각 세션에 대해 추가 정보 조회
        # for session in sessions:
        #     # 마지막 대화 조회
        #     last_dialogue = await self.chat_repository.get_last_dialogue(
        #         session["session_id"]
        #     )
        #     session["last_dialogue"] = last_dialogue.text if last_dialogue else ""

        # 임시 응답
        sessions = []

        logger.info("list_user_sessions", f"Retrieved {len(sessions)} sessions",
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

        # TODO: Repository로 세션 조회
        # session = await self.repository.get_session(session_id)
        # if not session:
        #     logger.warning("get_session_detail", "Session not found",
        #                   session_id=session_id)
        #     return None

        # 권한 체크
        # if session.user_id != user_id:
        #     logger.warning("get_session_detail", "Permission denied",
        #                   session_id=session_id, user_id=user_id)
        #     return None

        # 최근 대화 조회
        # dialogues = await self.chat_repository.get_recent_dialogues(
        #     session_id, limit=10
        # )

        # 임시 응답
        session_detail = {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": "mugen_train",
            "scenario_title": "무한열차",
            "current_stage": "intro",
            "turn_count": 0,
            "state": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "dialogues": []
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

        # TODO: Repository로 세션 조회
        # session = await self.repository.get_session(session_id)
        # if not session:
        #     logger.warning("delete_session", "Session not found",
        #                   session_id=session_id)
        #     return False

        # 권한 체크
        # if session.user_id != user_id:
        #     logger.warning("delete_session", "Permission denied",
        #                   session_id=session_id, user_id=user_id)
        #     return False

        async with self.db.begin():
            # TODO: Repository로 세션 및 대화 삭제
            # await self.chat_repository.delete_session_dialogues(session_id)
            # await self.repository.delete_session(session_id)

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

        # 세션 ID 생성
        import uuid
        session_id = str(uuid.uuid4())

        # 초기 상태
        initial_state = {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "turn_count": 0,
            "current_stage": "intro",
            "affinity": {},
            "created_at": datetime.utcnow().isoformat()
        }

        async with self.db.begin():
            # TODO: Repository로 세션 저장
            # await self.repository.save_session(
            #     session_id=session_id,
            #     user_id=user_id,
            #     scenario_id=scenario_id,
            #     state=initial_state
            # )

            logger.info("create_session", "Session created",
                       session_id=session_id)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "state": initial_state,
            "created_at": initial_state["created_at"]
        }
