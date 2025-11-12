"""
Chat Feature - UseCase
비즈니스 로직, 트랜잭션 경계
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from .repositories import (
    DialogueRepository,
    SessionRepository,
    AffinityRepository,
    ImageRepository,
    EntityRepository,
    MemoryRepository,
)
from .agent.parent import ParentAgent  # Legacy ParentAgent (not LangGraph)
from .services import AffinityService, MemoryService, MissionService, ScenarioService
from .services.extractors.conversation_summarizer import ConversationSummarizer
from .models import DialogueTurn
from .schemas import DialogueResult, ChatMessage
from app.core.logging import get_usecase_logger, print_layer_debug
from app.shared.exceptions import DailyLimitExceededException
from app.features.users.repository import UserRepository
from app.features.progression.repository import ProgressionRepository
from app.core.llm.client import LLMClient

# LangGraph imports (optional - only used if USE_LANGGRAPH=true)
try:
    from .agent.workflow import get_workflow
    from .agent.graph_state import GraphState
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

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
        self.dialogue_repository = DialogueRepository(db)
        self.session_repository = SessionRepository(db)
        self.affinity_repository = AffinityRepository(db)
        self.image_repository = ImageRepository(db)
        self.entity_repository = EntityRepository(db)
        self.memory_repository = MemoryRepository(db)
        self.user_repository = UserRepository(db)
        self.progression_repository = ProgressionRepository(db)
        self.parent = ParentAgent()
        self.affinity_service = AffinityService()
        self.memory_service = MemoryService()
        self.mission_service = MissionService()
        self.scenario_service = ScenarioService()

        # Conversation Summarizer (LLM 기반 요약)
        try:
            llm_client = LLMClient()
            self.summarizer = ConversationSummarizer(llm_client=llm_client)
            logger.info("__init__", "ConversationSummarizer initialized")
        except Exception as e:
            logger.warning("__init__", f"Failed to initialize ConversationSummarizer: {e}")
            self.summarizer = None

        # LangGraph 워크플로우 (feature flag)
        self.use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
        self.workflow = None

        if self.use_langgraph and LANGGRAPH_AVAILABLE:
            try:
                self.workflow = get_workflow()
                logger.info("__init__", "LangGraph workflow enabled")
            except Exception as e:
                logger.warning("__init__", f"Failed to initialize LangGraph workflow: {e}", exc=e)
                self.use_langgraph = False
        elif self.use_langgraph and not LANGGRAPH_AVAILABLE:
            logger.warning("__init__", "USE_LANGGRAPH=true but LangGraph not available")
            self.use_langgraph = False

    def _convert_to_graph_state(
        self,
        session_state: Dict[str, Any],
        user_message: str,
        user_name: str
    ) -> GraphState:
        """
        session_state dict를 GraphState로 변환

        Args:
            session_state: 세션 상태
            user_message: 사용자 메시지
            user_name: 사용자 이름

        Returns:
            GraphState
        """
        graph_state = GraphState(
            # Session info
            session_id=session_state.get("session_id", ""),
            user_id=session_state.get("user_id", ""),
            scenario_id=session_state.get("scenario_id", ""),
            user_name=user_name,

            # User input
            user_input=user_message,

            # Scenario state
            current_stage=session_state.get("current_stage"),
            stage_tag=session_state.get("current_stage"),
            turn_count=session_state.get("turn_count", 0),
            stage_turn=session_state.get("stage_turn", 0),

            # Scenario data (optional - will be loaded by agents)
            scenario=session_state.get("scenario"),

            # Agent communication
            agent_inputs={},
            agent_responses=[],

            # Workflow control
            next_node=None,

            # Context
            children_ctx=None,
            temp_data={},

            # Game state
            game=session_state.get("game", {}),
            scene=session_state.get("scene", {}),

            # Output
            output={},

            # Summary and memory
            conversation_summary=session_state.get("conversation_summary"),
            summary_turn_count=session_state.get("summary_turn_count", 0),

            # Affinity
            affinity_scores=session_state.get("affinity_scores", {}),

            # Ending
            final_ending=session_state.get("final_ending"),
            is_active=session_state.get("is_active", True)
        )

        return graph_state

    def _convert_from_graph_state(
        self,
        graph_state: GraphState,
        original_state: Dict[str, Any]
    ) -> DialogueResult:
        """
        GraphState를 DialogueResult로 변환

        Args:
            graph_state: LangGraph 워크플로우 결과
            original_state: 원본 세션 상태 (병합용)

        Returns:
            DialogueResult
        """
        # Dialogues 변환 (Dict → ChatMessage)
        dialogues_raw = graph_state.get("output", {}).get("dialogues", [])
        dialogues = [
            ChatMessage(
                speaker=d.get("speaker", "narr"),
                text=d.get("text", ""),
                emotion=d.get("emotion", "neutral")
            )
            for d in dialogues_raw
        ]

        # Updated state 병합
        updated_state = original_state.copy()

        # affinity_delta를 사용해서 affinity_scores 계산
        affinity_delta = graph_state.get("output", {}).get("affinity_delta", {})
        current_affinity = updated_state.get("affinity_scores", {})

        # delta 적용
        for char, delta in affinity_delta.items():
            current_affinity[char] = current_affinity.get(char, 0) + delta

        updated_state.update({
            "current_stage": graph_state.get("current_stage") or graph_state.get("stage_tag"),
            "turn_count": graph_state.get("turn_count", 0),
            "stage_turn": graph_state.get("stage_turn", 0),
            "conversation_summary": graph_state.get("conversation_summary"),
            "summary_turn_count": graph_state.get("summary_turn_count", 0),
            "affinity_scores": current_affinity,  # 계산된 친밀도 사용
            "final_ending": graph_state.get("final_ending"),
            "is_active": graph_state.get("is_active", True),
            "game": graph_state.get("game", {}),
            "scene": graph_state.get("scene", {}),
        })

        # DialogueResult 생성
        result = DialogueResult(
            dialogues=dialogues,
            next_stage=graph_state.get("output", {}).get("next_stage"),
            stage_complete=graph_state.get("output", {}).get("stage_complete", False),
            updated_state=updated_state,
            affinity_delta=graph_state.get("output", {}).get("affinity_delta"),
            affinity_scores=updated_state.get("affinity_scores", {})  # 현재 친밀도 포함
        )

        return result

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
            existing_session = await self.session_repository.get_session(session_id)

            if existing_session:
                # 기존 세션 상태 로드
                logger.info("create_dialogue", "Loading existing session",
                           session_id=session_id,
                           current_stage=existing_session["state"].get("current_stage"),
                           turn_count=existing_session["state"].get("turn_count"))
                session_state = existing_session["state"]
                # 세션 메타 정보 업데이트 (scenario_id 포함)
                session_state["session_id"] = session_id
                session_state["scenario_id"] = scenario_id  # scenario_id 명시적 보존
                session_state["user_id"] = user_id
                session_state["user_name"] = user_name or session_state.get("user_name", "여행자")

                # 기존 세션이라도 DB에서 최신 친밀도를 다시 로드 (sessions 테이블에 저장되지 않으므로)
                if user_id:
                    try:
                        user_affinities = await self.affinity_repository.get_all_user_affinities(user_id)
                        affinity_scores = {}
                        for affinity in user_affinities:
                            affinity_scores[affinity.character_name] = affinity.total_affinity_score
                        session_state["affinity_scores"] = affinity_scores
                        logger.info("create_dialogue", f"Loaded {len(affinity_scores)} affinity scores from DB for existing session",
                                   user_id=user_id, scores=affinity_scores)
                    except Exception as e:
                        logger.error("create_dialogue", f"Failed to load affinity scores for existing session: {e}",
                                    user_id=user_id, exc_info=True)
                        # 에러 시에도 빈 dict로 초기화 (기존 로직 유지)
                        if "affinity_scores" not in session_state:
                            session_state["affinity_scores"] = {}
            else:
                # 신규 세션 생성
                logger.info("create_dialogue", "Creating new session", session_id=session_id)
                # Get first stage from scenario
                first_stage = self.scenario_service.get_first_stage_tag(scenario_id)

                # 사용자의 기존 친밀도를 DB에서 불러오기
                initial_affinity_scores = {}
                if user_id:
                    try:
                        user_affinities = await self.affinity_repository.get_all_user_affinities(user_id)
                        for affinity in user_affinities:
                            initial_affinity_scores[affinity.character_name] = affinity.total_affinity_score
                        logger.info("create_dialogue", f"Loaded {len(initial_affinity_scores)} affinity scores from DB",
                                   user_id=user_id, scores=initial_affinity_scores)
                    except Exception as e:
                        logger.error("create_dialogue", f"Failed to load affinity scores: {e}",
                                    user_id=user_id, exc_info=True)

                session_state = {
                    "session_id": session_id,
                    "scenario_id": scenario_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "turn_count": 0,
                    "current_stage": first_stage,
                    "affinity_scores": initial_affinity_scores,
                }

            # ============================================================
            # 2. 정책: 일일 대화 제한 체크
            # ============================================================
            today_count = await self.dialogue_repository.count_today(user_id)
            logger.debug("create_dialogue", f"Today's dialogue count: {today_count}", user_id=user_id, count=today_count)

            if today_count >= MAX_DAILY_CHATS:
                logger.warning("create_dialogue", "Daily limit exceeded", user_id=user_id, count=today_count, limit=MAX_DAILY_CHATS)
                raise DailyLimitExceededException(MAX_DAILY_CHATS)

            # ============================================================
            # 2. Agent 파이프라인 실행 (LangGraph 또는 Legacy)
            # ============================================================
            if self.use_langgraph and self.workflow:
                # LangGraph 워크플로우 사용
                logger.info("create_dialogue", "Calling LangGraph workflow", user_message=user_message[:50])
                print_layer_debug("USECASE", "Chat", "create_dialogue", "→ Calling LangGraph Workflow")

                try:
                    # GraphState로 변환
                    graph_state = self._convert_to_graph_state(
                        session_state=session_state,
                        user_message=user_message,
                        user_name=user_name
                    )

                    # 워크플로우 실행 (thread_id 필수)
                    config = {"configurable": {"thread_id": session_id}}
                    result_state = await self.workflow.ainvoke(graph_state, config)

                    # DialogueResult로 변환
                    logger.info("create_dialogue", "Graph state output", output=result_state.get("output"))
                    dialogue_result = self._convert_from_graph_state(
                        graph_state=result_state,
                        original_state=session_state
                    )

                    logger.info("create_dialogue", "LangGraph workflow completed",
                               dialogues_count=len(dialogue_result.dialogues))
                except Exception as e:
                    logger.exception("create_dialogue", "LangGraph workflow failed", exc=e)
                    raise
            else:
                # Legacy Parent Agent 사용
                logger.info("create_dialogue", "Calling legacy parent agent", user_message=user_message[:50])
                print_layer_debug("USECASE", "Chat", "create_dialogue", "→ Calling Legacy Parent Agent")

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
                    turn_number=turn_count,
                    speaker=dialogue.speaker,
                    content=dialogue.text,
                    emotion=dialogue.emotion or "neutral",
                    emotion_intensity=dialogue.emotion_intensity if hasattr(dialogue, 'emotion_intensity') else None,
                    stage_tag=session_state.get("current_stage"),
                    order_index=idx,
                    created_at=datetime.utcnow()
                )
                dialogue_models.append(model)

            logger.info("create_dialogue", f"Saving {len(dialogue_models)} dialogues to DB")
            await self.dialogue_repository.save_dialogues_batch(dialogue_models)

            # ============================================================
            # 4. 대화 요약 생성 및 Memory 저장
            # ============================================================
            if self.summarizer and user_id:
                try:
                    # 최근 대화 조회
                    recent_dialogues = await self.dialogue_repository.get_recent_dialogues(session_id, limit=50)

                    # 대화 히스토리 구성
                    message_history = []
                    for dlg in recent_dialogues:
                        message_history.append({
                            "turn": dlg.turn_number,
                            "user_input": "",  # 사용자 입력은 별도 저장 필요
                            "agent_responses": [{
                                "speaker": dlg.speaker,
                                "text": dlg.content
                            }]
                        })

                    # 요약 업데이트 체크
                    summary_result = await self.summarizer.update_summary(
                        state=dialogue_result.updated_state,
                        message_history=message_history
                    )

                    # 새 요약이 생성되었으면 저장
                    if summary_result["summary"] != dialogue_result.updated_state.get("conversation_summary"):
                        dialogue_result.updated_state["conversation_summary"] = summary_result["summary"]
                        dialogue_result.updated_state["summary_turn_count"] = summary_result["summary_turn_count"]

                        # 임베딩 생성
                        embedding = await self.summarizer.generate_embedding(summary_result["summary"])

                        # Memory로 저장
                        if embedding:
                            await self.memory_repository.create_memory(
                                user_id=user_id,
                                content=summary_result["summary"],
                                memory_type="episodic",
                                embedding=embedding,
                                scenario_id=scenario_id,
                                importance_score=0.8  # 요약은 높은 중요도
                            )
                            logger.info("create_dialogue", "Summary saved to memories",
                                       session_id=session_id, summary_length=len(summary_result["summary"]))

                except Exception as e:
                    logger.error("create_dialogue", f"Summary generation failed: {e}", exc=e)

            # ============================================================
            # 5. 세션 상태 저장
            # ============================================================
            logger.info("create_dialogue", "Saving session state")
            await self.session_repository.save_session(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                state=dialogue_result.updated_state
            )

            # ============================================================
            # 5.5 친밀도를 user_character_affinity 테이블에 저장
            # ============================================================
            if user_id and dialogue_result.affinity_scores:
                try:
                    from uuid import UUID
                    for character_name, score in dialogue_result.affinity_scores.items():
                        # 세션별 친밀도 변화 기록
                        await self.affinity_repository.save_affinity_record(
                            session_id=session_id,
                            turn_number=turn_count,
                            character_name=character_name,
                            affinity_score=score,
                            change_amount=None  # 변화량은 나중에 계산 가능
                        )

                        # 사용자별 글로벌 친밀도 업데이트
                        # 기존 점수 조회
                        existing_affinity = await self.affinity_repository.get_user_character_affinity(
                            user_id=user_id,
                            character_name=character_name
                        )

                        if existing_affinity:
                            # 차이만큼 업데이트 (delta 계산)
                            delta = score - existing_affinity.total_affinity_score
                            if delta != 0:
                                await self.affinity_repository.upsert_user_character_affinity(
                                    user_id=user_id,
                                    character_name=character_name,
                                    score_delta=delta
                                )
                        else:
                            # 새로 생성 (현재 점수를 delta로 설정)
                            await self.affinity_repository.upsert_user_character_affinity(
                                user_id=user_id,
                                character_name=character_name,
                                score_delta=score
                            )

                    logger.info("create_dialogue", "Affinity scores saved to DB",
                               user_id=user_id, characters=list(dialogue_result.affinity_scores.keys()))
                except Exception as e:
                    logger.error("create_dialogue", f"Failed to save affinity scores: {e}",
                                user_id=user_id, exc_info=True)

            # ============================================================
            # 6. 사용자 진행 (Progression) 업데이트
            # ============================================================
            if user_id:
                try:
                    from uuid import UUID

                    # 1. 사용자 입력 저장
                    await self.progression_repository.save_user_input(
                        session_id=UUID(session_id),
                        turn_number=turn_count,
                        user_input=user_message
                    )

                    # 2. 메시지 카운트 증가
                    await self.progression_repository.increment_user_stat(
                        user_id=UUID(user_id),
                        stat_name="total_messages",
                        increment_by=1
                    )

                    # 3. 시나리오 진행도 업데이트
                    scenario_progress = await self.progression_repository.get_scenario_progress(
                        UUID(user_id), scenario_id
                    )
                    if scenario_progress:
                        await self.progression_repository.update_scenario_progress(
                            user_id=UUID(user_id),
                            scenario_id=scenario_id,
                            progress_data={
                                "total_messages": scenario_progress.total_messages + 1,
                                "last_session_id": session_id,
                                "has_started": True
                            }
                        )
                    else:
                        # 새 시나리오 시작
                        await self.progression_repository.update_scenario_progress(
                            user_id=UUID(user_id),
                            scenario_id=scenario_id,
                            progress_data={
                                "has_started": True,
                                "total_messages": 1,
                                "last_session_id": session_id
                            }
                        )

                    # 4. XP 지급 (메시지당 5 XP)
                    xp_result = await self.progression_repository.award_experience(
                        user_id=UUID(user_id),
                        xp_amount=5,
                        xp_type="message",
                        description=f"Message in {scenario_id}",
                        metadata={"message_length": len(user_message)}
                    )

                    logger.info("create_dialogue", "Progression updated",
                               user_id=user_id,
                               xp_awarded=5,
                               level_before=xp_result.get("level_before"),
                               level_after=xp_result.get("level_after"),
                               did_level_up=xp_result.get("did_level_up"))

                except Exception as e:
                    logger.error("create_dialogue", f"Progression update failed: {e}", exc=e)

            # ============================================================
            # 7. 결과 반환
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
        dialogue_models = await self.dialogue_repository.get_recent_dialogues(session_id, limit)

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
        existing_session = await self.session_repository.get_session(session_id)

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
            count = await self.dialogue_repository.delete_session_dialogues(session_id)

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
