"""
Chat Feature - UseCase
비즈니스 로직, 트랜잭션 경계
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime

from .repository import ChatRepository
from .models import DialogueTurn
from .schemas import DialogueResult, ChatMessage
from app.core.logging import get_usecase_logger, print_layer_debug
from app.shared.exceptions import DailyLimitExceededException

logger = get_usecase_logger("Chat")

# 일일 대화 제한
MAX_DAILY_CHATS = 1000


class ChatUseCase:
    """
    [Layer 2] UseCase
    책임: 유스케이스 정책, 트랜잭션 경계, 여러 Repository/Agent 조합
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(
        self,
        db: AsyncSession,
        repository: ChatRepository,
        parent  # parent agent (순환 참조 방지를 위해 타입 힌트 생략)
    ):
        self.db = db
        self.repository = repository
        self.parent = parent

    async def create_dialogue(
        self,
        user_id: str,
        session_id: str,
        scenario_id: str,
        user_message: str,
        session_state: Dict[str, Any]
    ) -> DialogueResult:
        """
        대화 생성 유스케이스

        플로우:
        1. 정책 체크 (일일 한도)
        2. Parent Agent 파이프라인 실행
        3. 대화 저장
        4. 결과 반환

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            user_message: 사용자 메시지
            session_state: 세션 상태

        Returns:
            DialogueResult

        Raises:
            DailyLimitExceededException: 일일 한도 초과
        """
        print_layer_debug("USECASE", "Chat", "create_dialogue", "Starting", user_id=user_id, session_id=session_id)
        logger.info("create_dialogue", "Transaction started", user_id=user_id, session_id=session_id)

        async with self.db.begin():  # ← 트랜잭션 시작
            # ============================================================
            # 1. 정책: 일일 대화 제한 체크
            # ============================================================
            today_count = await self.repository.count_today(user_id)
            logger.debug("create_dialogue", f"Today's dialogue count: {today_count}", user_id=user_id, count=today_count)

            if today_count >= MAX_DAILY_CHATS:
                logger.warning("create_dialogue", "Daily limit exceeded", user_id=user_id, count=today_count, limit=MAX_DAILY_CHATS)
                raise DailyLimitExceededException(MAX_DAILY_CHATS)

            # ============================================================
            # 2. Parent Agent 파이프라인 실행
            # ============================================================
            logger.info("create_dialogue", "Calling parent agent", user_message=user_message[:50])
            print_layer_debug("USECASE", "Chat", "create_dialogue", "→ Calling Parent Agent")

            try:
                dialogue_result = await self.parent.execute(
                    user_message=user_message,
                    session_state=session_state,
                    scenario_id=scenario_id
                )
                logger.info("create_dialogue", "Parent agent completed", dialogues_count=len(dialogue_result.dialogues))
            except Exception as e:
                logger.exception("create_dialogue", "Parent agent failed", exc=e)
                raise

            # ============================================================
            # 3. 대화 저장
            # ============================================================
            turn_count = session_state.get("turn_count", 0) + 1

            dialogue_models = []
            for idx, dialogue in enumerate(dialogue_result.dialogues):
                model = DialogueTurn(
                    session_id=session_id,
                    user_id=user_id,
                    scenario_id=scenario_id,
                    turn_count=turn_count,
                    speaker=dialogue.speaker,
                    text=dialogue.text,  # ✅ text 필드 사용
                    emotion=dialogue.emotion or "neutral",
                    stage_tag=session_state.get("current_stage"),
                    created_at=datetime.utcnow()
                )
                dialogue_models.append(model)

            logger.info("create_dialogue", f"Saving {len(dialogue_models)} dialogues to DB")
            await self.repository.save_dialogues_batch(dialogue_models)

            # ============================================================
            # 4. 결과 반환
            # ============================================================
            logger.info("create_dialogue", "Transaction committed", dialogues_saved=len(dialogue_models))
            print_layer_debug("USECASE", "Chat", "create_dialogue", "✅ Completed", dialogues=len(dialogue_models))

            return dialogue_result

    async def get_recent_dialogues(
        self,
        session_id: str,
        limit: int = 10
    ) -> list[ChatMessage]:
        """
        최근 대화 조회

        Args:
            session_id: 세션 ID
            limit: 조회 개수

        Returns:
            ChatMessage 리스트
        """
        logger.info("get_recent_dialogues", "Fetching recent dialogues", session_id=session_id, limit=limit)

        # Repository 호출
        dialogue_models = await self.repository.get_recent_dialogues(session_id, limit)

        # ORM → DTO 변환
        messages = [
            ChatMessage(
                speaker=d.speaker,
                text=d.text,  # ✅ text 필드
                emotion=d.emotion,
                timestamp=d.created_at.isoformat() if d.created_at else None
            )
            for d in dialogue_models
        ]

        logger.info("get_recent_dialogues", f"Fetched {len(messages)} messages", session_id=session_id)
        return messages

    async def delete_session(self, session_id: str) -> int:
        """
        세션 삭제 (대화 포함)

        Args:
            session_id: 세션 ID

        Returns:
            삭제된 대화 수
        """
        logger.warning("delete_session", "Deleting session", session_id=session_id)

        async with self.db.begin():
            count = await self.repository.delete_session_dialogues(session_id)

        logger.warning("delete_session", f"Session deleted: {count} dialogues", session_id=session_id)
        return count
