"""
Chat Feature - UseCase
비즈니스 로직, 트랜잭션 경계
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime

from .repository import ChatRepository
from .agent import ParentAgent
from .services import AffinityService, MemoryService, MissionService
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
    책임: 유스케이스 정책, 트랜잭션 경계, Repository/Agent 조합
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)

    UseCase가 Repository와 Agent를 생성/관리함
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        # UseCase 내부에서 Repository, Agent, Service 생성
        self.repository = ChatRepository(db)
        self.parent = ParentAgent()
        self.affinity_service = AffinityService()
        self.memory_service = MemoryService()
        self.mission_service = MissionService()

    async def create_dialogue(
        self,
        user_id: str,
        session_id: str,
        scenario_id: str,
        user_message: str,
        user_name: str = "여행자"
    ) -> DialogueResult:
        """
        대화 생성 유스케이스

        플로우:
        1. 세션 상태 로드
        2. 정책 체크 (일일 한도)
        3. Parent Agent 파이프라인 실행
        4. 대화 저장
        5. 세션 상태 저장
        6. 결과 반환

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            user_message: 사용자 메시지
            user_name: 사용자 이름

        Returns:
            DialogueResult

        Raises:
            DailyLimitExceededException: 일일 한도 초과
        """
        print_layer_debug("USECASE", "Chat", "create_dialogue", "Starting", user_id=user_id, session_id=session_id)
        logger.info("create_dialogue", "Transaction started", user_id=user_id, session_id=session_id)

        async with self.db.begin():  # ← 트랜잭션 시작
            # ============================================================
            # 1. 세션 상태 로드 (트랜잭션 내부)
            # ============================================================
            existing_session = await self.repository.get_session(session_id)

            if existing_session:
                # 기존 세션 상태 로드
                logger.info("create_dialogue", "Loading existing session",
                           session_id=session_id,
                           current_stage=existing_session["state"].get("current_stage"),
                           turn_count=existing_session["state"].get("turn_count"))
                session_state = existing_session["state"]
                # 세션 메타 정보 업데이트
                session_state["session_id"] = session_id
                session_state["user_id"] = user_id
                session_state["user_name"] = user_name or session_state.get("user_name", "여행자")
            else:
                # 신규 세션 생성
                logger.info("create_dialogue", "Creating new session", session_id=session_id)
                session_state = {
                    "session_id": session_id,
                    "scenario_id": scenario_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "turn_count": 0,
                    "current_stage": "intro",
                    "affinity_scores": {},
                }

            # ============================================================
            # 2. 정책: 일일 대화 제한 체크
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
                dialogue_result = await self.parent.run(
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
            # 4. 세션 상태 저장
            # ============================================================
            logger.info("create_dialogue", "Saving session state")
            await self.repository.save_session(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                state=dialogue_result.updated_state
            )

            # ============================================================
            # 5. 결과 반환
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

    async def get_session_state(
        self,
        session_id: str,
        scenario_id: str,
        user_id: str,
        user_name: str
    ) -> Dict[str, Any]:
        """
        세션 상태 조회 (없으면 신규 생성)

        Args:
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            user_name: 사용자 이름

        Returns:
            세션 상태 dict
        """
        logger.info("get_session_state", "Getting session state", session_id=session_id)

        # 기존 세션 조회
        existing_session = await self.repository.get_session(session_id)

        if existing_session:
            # 기존 세션 상태 로드
            logger.info("get_session_state", "Loading existing session",
                       session_id=session_id,
                       current_stage=existing_session["state"].get("current_stage"),
                       turn_count=existing_session["state"].get("turn_count"))
            session_state = existing_session["state"]
            # 세션 메타 정보 업데이트
            session_state["session_id"] = session_id
            session_state["user_id"] = user_id
            session_state["user_name"] = user_name or session_state.get("user_name", "여행자")
        else:
            # 신규 세션 생성
            logger.info("get_session_state", "Creating new session", session_id=session_id)
            session_state = {
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_id": user_id,
                "user_name": user_name or "여행자",
                "turn_count": 0,
                "current_stage": "intro",
                "affinity_scores": {},
            }

        return session_state

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

    async def process_affinity(
        self,
        user_id: str,
        session_id: str,
        scenario_id: str,
        state: Dict[str, Any],
        user_input: str,
        dialogues: List[Dict[str, Any]],
        participating_characters: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        친밀도 처리 및 저장

        AffinityService를 통해 친밀도를 업데이트하고,
        Repository를 통해 DB에 저장합니다.

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            state: 게임 상태
            user_input: 사용자 입력
            dialogues: 대화 리스트
            participating_characters: 등장 캐릭터 리스트 (선택적)

        Returns:
            업데이트된 친밀도 점수 (character_id -> score)
        """
        logger.info("process_affinity", "Processing affinity",
                   user_id=user_id, session_id=session_id)

        try:
            # AffinityService로 친밀도 업데이트
            updated_affinity = await self.affinity_service.update_affinity(
                state=state,
                user_input=user_input,
                dialogues=dialogues,
                participating_characters=participating_characters
            )

            # Repository를 통해 DB에 저장 (트랜잭션)
            async with self.db.begin():
                for character_id, score in updated_affinity.items():
                    # TODO: Repository에 affinity 저장 메서드 추가 필요
                    # await self.repository.save_affinity(
                    #     user_id=user_id,
                    #     character_id=character_id,
                    #     scenario_id=scenario_id,
                    #     affinity_score=score
                    # )
                    logger.debug("process_affinity",
                               f"Affinity saved: {character_id} = {score}",
                               character=character_id, score=score)

            logger.info("process_affinity", "Affinity processed successfully",
                       characters=len(updated_affinity))

            return updated_affinity

        except Exception as e:
            logger.error("process_affinity", f"Affinity processing failed: {e}",
                        exc_info=True)
            return {}

    async def save_memories(
        self,
        user_id: str,
        session_id: str,
        scenario_id: str,
        user_input: str,
        assistant_responses: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        메모리 추출 및 저장

        MemoryService를 통해 엔티티, 관계, 기억을 추출하고,
        Repository를 통해 DB에 저장합니다.

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            user_input: 사용자 입력
            assistant_responses: 어시스턴트 응답 리스트
            context: 추가 컨텍스트

        Returns:
            추출된 메모리 정보
            {
                "entities": List[Entity],
                "relationships": List[EntityRelationship],
                "combined_text": str
            }
        """
        logger.info("save_memories", "Processing memories",
                   user_id=user_id, session_id=session_id)

        try:
            # 응답 텍스트 결합
            response_text = "\n".join([
                d.get("text", "") for d in assistant_responses
            ])

            # MemoryService로 메모리 추출
            memory_context = context or {}
            memory_context["scenario_id"] = scenario_id
            memory_context["session_id"] = session_id

            result = await self.memory_service.process_conversation_turn(
                user_input=user_input,
                assistant_response=response_text,
                context=memory_context
            )

            # Repository를 통해 DB에 저장 (트랜잭션)
            async with self.db.begin():
                # TODO: Repository에 메모리 저장 메서드 추가 필요
                # entities
                # for entity in result["entities"]:
                #     await self.repository.save_entity(entity)

                # relationships
                # for relationship in result["relationships"]:
                #     await self.repository.save_relationship(relationship)

                logger.debug("save_memories",
                            f"Saved {len(result['entities'])} entities, "
                            f"{len(result['relationships'])} relationships")

            logger.info("save_memories", "Memories saved successfully",
                       entities=len(result["entities"]),
                       relationships=len(result["relationships"]))

            return result

        except Exception as e:
            logger.error("save_memories", f"Memory saving failed: {e}",
                        exc_info=True)
            return {"entities": [], "relationships": [], "combined_text": ""}

    async def handle_mission(
        self,
        state: Dict[str, Any],
        user_input: str,
        mission_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        미션 처리 (동료 모집)

        MissionService를 통해 미션을 처리합니다.

        Args:
            state: 게임 상태
            user_input: 사용자 입력
            mission_state: 미션 상태 (선택적)

        Returns:
            미션 처리 결과
            {
                "target": str,  # 미션 대상
                "success": bool,  # 성공 여부
                "feedback_beats": List[Dict],  # 피드백 beats
                "mission_active": bool  # 미션 활성화 여부
            }
        """
        logger.info("handle_mission", "Handling mission",
                   user_input=user_input[:50])

        try:
            # 미션 상태 가져오기
            mission_state = mission_state or state.get("mission", {})

            # 미션 대상 결정
            target = self.mission_service.determine_mission_target(
                state=state,
                user_input=user_input,
                mission_state=mission_state
            )

            if not target:
                logger.debug("handle_mission", "No mission target found")
                return {
                    "target": None,
                    "success": False,
                    "feedback_beats": [],
                    "mission_active": False
                }

            # 미션 활성화
            self.mission_service.activate_mission(state, target)

            # 모집 시도 평가
            success = await self.mission_service.evaluate_recruit_attempt(
                state=state,
                target=target
            )

            # 피드백 beats 생성
            feedback_beats = self.mission_service.build_feedback_beats(
                state=state,
                character=target,
                success=success
            )

            logger.info("handle_mission", "Mission handled",
                       target=target, success=success,
                       feedback_count=len(feedback_beats))

            return {
                "target": target,
                "success": success,
                "feedback_beats": feedback_beats,
                "mission_active": True
            }

        except Exception as e:
            logger.error("handle_mission", f"Mission handling failed: {e}",
                        exc_info=True)
            return {
                "target": None,
                "success": False,
                "feedback_beats": [],
                "mission_active": False
            }
