"""
Chat Feature - UseCase
비즈니스 로직, 트랜잭션 경계
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import json
import re
from pathlib import Path
from functools import lru_cache

from .repositories import (
    DialogueRepository,
    SessionRepository,
    AffinityRepository,
    ImageRepository,
    EntityRepository,
    MemoryRepository,
)
# v2 Memory System Repositories
from .repositories.user_profile_repository import UserProfileRepository
from .repositories.stm_repository import STMRepository
from .repositories.scenario_buffer_repository import ScenarioBufferRepository
from .agent.parent import ParentAgent  # Legacy ParentAgent (not LangGraph)
from .services import AffinityService, MemoryService, MissionService, ScenarioService, MessageHistoryService
from .services.extractors.conversation_summarizer import ConversationSummarizer
from .services.extractors.memory_extractor import MemoryExtractor
# v2 Memory System Services
from .services.stm_manager import STMManager
from .services.scenario_buffer_manager import ScenarioBufferManager
from .services.extractors.hierarchical_summarizer import HierarchicalSummarizer
from .models import DialogueTurn
from .schemas import DialogueResult, ChatMessage
from app.core.logging import get_usecase_logger, print_layer_debug
from app.shared.exceptions import DailyLimitExceededException
from app.features.users.repository import UserRepository
from app.features.progression.repository import ProgressionRepository
from app.core.llm.client import LLMClient
from app.core.embeddings import EmbeddingsService
from app.features.images.local_mapping_loader import get_stage_image_identifier
# ----------------------------------------
# Background metadata helpers (keyword-based)
# ----------------------------------------

DEFAULT_FIRST_TURN_BACKGROUND = "무한열차.png"

SPEAKER_BASIC_IMAGES = {
    "tanjiro": "탄지로_기본.png",
    "rengoku": "렌고쿠_기본.png",
    "zenitsu": "젠이츠_기본.png",
    "inosuke": "이노스케_기본.png",
    "nezuko": "네즈코_기본.png",
    "giyu": "기유_기본.png",
    "shinobu": "시노부_기본.png",
}

@lru_cache(maxsize=8)
def _load_background_metadata(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    Load background metadata JSON (shared with frontend) for keyword matching.

    Looks for <scenario>_images.json under data/image_mappings (supports -/_ variants).
    """
    if not scenario_id:
        return None

    candidates = set([scenario_id, scenario_id.replace('-', '_'), scenario_id.replace('_', '-')])
    base_dirs = []
    current = Path(__file__).resolve()
    for parent in list(current.parents)[:5]:
        base_dirs.append(parent.parent / "data" / "image_mappings")
        base_dirs.append(parent / "data" / "image_mappings")

    for name in candidates:
        filename = f"{name}_images.json"
        for base in base_dirs:
            path = (base / filename).resolve()
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue
    return None


def _tokenize(text: str) -> List[str]:
    if not text:
        return []

    # 조사가 붙은 단어, 불용어를 제거해 매칭 정확도를 높임
    stop_words = {
        "그리고", "그러나", "하지만", "그래서", "또한", "혹은", "그러면", "그럼", "아니면",
        "이", "그", "저", "거", "것", "뭐", "어디", "누가", "누구", "왜", "어떻게",
        "정말", "진짜", "음", "어", "아", "야", "자", "좀", "만약", "만일"
    }

    def _normalize_token(tok: str) -> str:
        tok = tok.strip().lower()
        if not tok:
            return ""

        # 조사/격 조사 제거 (간단한 후행 패턴)
        tok = re.sub(
            r"(에서|으로부터|으로써|으로서|으로|에게서|에게|께서|께|한테서|한테|까지|부터|처럼|만큼|보다|와|과|랑|하고|은|는|이|가|을|를)$",
            "",
            tok
        )
        # 동사/형용사 어미 단순 스테밍
        tok = re.sub(r"(했다|하였다|한다|한|하는|하며|하던|하여|해서|해요|해)$", "하", tok)
        tok = re.sub(r"(였다|였다면|였던|였다가|였으나|였지만)$", "이", tok)

        return tok.strip("_-")

    raw_tokens = [tok for tok in re.split(r"[^0-9A-Za-z가-힣_]+", text.lower()) if tok]
    normalized = []
    for tok in raw_tokens:
        base = _normalize_token(tok)
        if not base or len(base) <= 1 or base in stop_words:
            continue
        normalized.append(base)

    return normalized


@lru_cache(maxsize=8)
def _get_image_description_embeddings(scenario_id: str) -> Dict[str, List[float]]:
    """
    Load image metadata and generate embeddings for their descriptions.
    The result is cached to avoid re-computation.
    """
    logger.info("_get_image_description_embeddings", f"Cache miss. Generating embeddings for {scenario_id}")
    meta = _load_background_metadata(scenario_id)
    if not meta or not (images := meta.get("images")):
        return {}

    # Prepare texts for batch embedding
    image_ids = []
    texts_to_embed = []
    for img in images:
        # Use a combination of name, description, and tags for richer context
        desc = img.get("description", "")
        name = img.get("name", "")
        tags = ", ".join(img.get("tags", []))
        combined_text = f"{name}: {desc} (Tags: {tags})"
        
        image_id = img.get("id") or img.get("fileName")
        if image_id and combined_text:
            image_ids.append(image_id)
            texts_to_embed.append(combined_text)

    if not texts_to_embed:
        return {}

    # Generate embeddings in a batch
    try:
        embeddings_service = EmbeddingsService()
        embeddings = embeddings_service.embed_batch(texts_to_embed)
        return dict(zip(image_ids, embeddings))
    except Exception as e:
        logger.error("_get_image_description_embeddings", f"Failed to generate embeddings: {e}")
        return {}


def _select_background_by_keywords(scenario_id: str, dialogues: List[ChatMessage]) -> Optional[tuple[str, int]]:
    """
    Lightweight keyword matcher. Returns (image_id, score) tuple.
    """
    meta = _load_background_metadata(scenario_id)
    if not meta:
        return None

    images = meta.get("images") or []
    if not images:
        return None

    # Collect dialogue tokens (text/content fields)
    combined_tokens: set[str] = set()
    for d in dialogues or []:
        payload = d.dict() if hasattr(d, "dict") else d
        for field in ("text", "content"):
            combined_tokens.update(_tokenize(str(payload.get(field, "") or "")))

    if not combined_tokens:
        return None

    best = None
    best_score = -1

    for bg in images:
        score = 0
        tags = bg.get("tags") or []
        name_tokens = _tokenize(bg.get("name", ""))
        desc_tokens = _tokenize(bg.get("description", ""))

        for tok in tags:
            if tok.lower() in combined_tokens:
                score += 3  # Tags are most important
        for tok in name_tokens + desc_tokens:
            if tok in combined_tokens:
                score += 1

        if score > best_score:
            best_score = score
            best = bg

    if not best or best_score <= 0:
        return None

    image_id = best.get("id") or best.get("fileName") or best.get("file_name")
    return image_id, best_score


def _fallback_image_by_top_speaker(dialogues: List[ChatMessage]) -> Optional[str]:
    """
    대화 중 가장 많이 말한 화자의 기본 이미지를 fallback으로 반환.
    User 메시지는 제외하고, speaker 문자열 포함 매칭도 허용.
    """
    if not dialogues:
        return None

    counts: Dict[str, int] = {}
    for d in dialogues:
        payload = d.dict() if hasattr(d, "dict") else d
        if payload.get("is_user"):
            continue
        speaker = str(payload.get("speaker") or "").lower()
        if not speaker:
            continue
        counts[speaker] = counts.get(speaker, 0) + 1

    if not counts:
        return None

    top_speaker = max(counts.items(), key=lambda kv: kv[1])[0]
    if top_speaker in SPEAKER_BASIC_IMAGES:
        return SPEAKER_BASIC_IMAGES[top_speaker]

    for key, value in SPEAKER_BASIC_IMAGES.items():
        if key in top_speaker:
            return value

    return None

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
        self.message_history_service = MessageHistoryService(
            dialogue_repository=self.dialogue_repository,
            progression_repository=self.progression_repository
        )

        # Conversation Summarizer (LLM 기반 요약)
        try:
            llm_client = LLMClient()
            self.summarizer = ConversationSummarizer(llm_client=llm_client)
            logger.info("__init__", "ConversationSummarizer initialized")
        except Exception as e:
            logger.warning("__init__", f"Failed to initialize ConversationSummarizer: {e}")
            self.summarizer = None

        # Memory Extractor (장기기억 추출)
        try:
            self.memory_extractor = MemoryExtractor(llm_client=llm_client if self.summarizer else None)
            logger.info("__init__", "MemoryExtractor initialized")
        except Exception as e:
            logger.warning("__init__", f"Failed to initialize MemoryExtractor: {e}")
            self.memory_extractor = None

        # Embeddings Service (벡터 임베딩 생성)
        try:
            self.embeddings_service = EmbeddingsService()
            logger.info("__init__", "EmbeddingsService initialized")
        except Exception as e:
            logger.warning("__init__", f"Failed to initialize EmbeddingsService: {e}")
            self.embeddings_service = None

        # v2 Memory System - Repositories
        self.user_profile_repository = UserProfileRepository(db)
        self.stm_repository = STMRepository(db)
        self.scenario_buffer_repository = ScenarioBufferRepository(db)
        logger.info("__init__", "v2 Memory Repositories initialized")

        # v2 Memory System - Services
        try:
            self.hierarchical_summarizer = HierarchicalSummarizer()
            self.stm_manager = STMManager(
                stm_repository=self.stm_repository,
                hierarchical_summarizer=self.hierarchical_summarizer
            )
            self.scenario_buffer_manager = ScenarioBufferManager(
                scenario_buffer_repository=self.scenario_buffer_repository
            )
            logger.info("__init__", "v2 Memory Services initialized (STMManager, ScenarioBufferManager, HierarchicalSummarizer)")
        except Exception as e:
            logger.warning("__init__", f"Failed to initialize v2 Memory Services: {e}", exc_info=True)
            self.stm_manager = None
            self.scenario_buffer_manager = None
            self.hierarchical_summarizer = None

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
        # ✅ 시나리오 데이터 로드 (RouterAgent보다 먼저 실행되므로 여기서 로드 필요)
        scenario_id = session_state.get("scenario_id", "")
        scenario_data = None
        if scenario_id:
            scenario_data = self.scenario_service.load_scenario(scenario_id)
            logger.info("_convert_to_graph_state", f"✅ Loaded scenario for state | scenario_id={scenario_id}")

        # TypedDict는 dict로 생성해야 함
        graph_state: GraphState = {
            # Session info
            "session_id": session_state.get("session_id", ""),
            "user_id": session_state.get("user_id", ""),
            "scenario_id": scenario_id,
            "user_name": user_name,

            # User input
            "user_input": user_message,

            # Scenario state
            "current_stage": session_state.get("current_stage", ""),
            "stage_type": "",  # 필수 필드
            "turn_count": session_state.get("turn_count", 0),
            "stage_turn": session_state.get("stage_turn", 0),

            # Scenario data
            "scenario": scenario_data,  # ✅ 미리 로드한 시나리오 데이터 사용
            "stage_config": None,

            # Messages
            "messages": [],
            "message_history": session_state.get("message_history", []),  # ✅ 최근 대화 히스토리

            # Context
            "conversation_summary": session_state.get("conversation_summary"),
            "user_memories": [],
            "character_affinity": {},

            # Entities
            "entities": [],
            "entity_mentions": [],

            # Routing
            "next_stage": None,
            "routing_reason": None,
            "stage_complete": False,

            # Mission
            "mission_progress": None,
            "mission_completed": False,
            # ✅ 미션 상태 (세션에서 로드)
            "mission": session_state.get("mission", {}),
            "temp_data": session_state.get("temp_data", {}),
            "recruit_attempts": session_state.get("recruit_attempts", {}),
            "allies_recruited": session_state.get("allies_recruited", []),
            "recruit_order": session_state.get("recruit_order", []),

            # AI response
            "ai_response": None,
            "speaker": None,
            "emotion": None,

            # Children Context & Agent Responses
            "children_ctx": None,
            "agent_responses": [],

            # Output
            "output": {},

            # Images
            "image_url": None,
            "thumbnail_url": None,

            # Guardrail
            "is_safe": True,
            "guardrail_warnings": [],

            # Fallback
            "is_off_topic": False,
            "off_topic_count": session_state.get("off_topic_count", 0),

            # Error
            "error": None,

            # Metadata
            "processing_time": 0.0,
            "agent_trace": [],
        }

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

        # current_stage 결정: stage_complete=True이면 next_stage 사용
        stage_complete = graph_state.get("output", {}).get("stage_complete", False)
        next_stage = graph_state.get("output", {}).get("next_stage")
        current_stage_for_session = next_stage if (stage_complete and next_stage) else (graph_state.get("current_stage") or graph_state.get("stage_tag"))

        logger.info("_convert_from_graph_state", "🔍 Converting from GraphState",
                   turn_count_from_graph=graph_state.get("turn_count"),
                   stage_turn_from_graph=graph_state.get("stage_turn"))

        updated_state.update({
            "current_stage": current_stage_for_session,
            "turn_count": graph_state.get("turn_count", 0),
            "stage_turn": graph_state.get("stage_turn", 0),
            "conversation_summary": graph_state.get("conversation_summary"),
            "summary_turn_count": graph_state.get("summary_turn_count", 0),
            "affinity_scores": current_affinity,  # 계산된 친밀도 사용
            "final_ending": graph_state.get("final_ending"),
            "is_active": graph_state.get("is_active", True),
            "game": graph_state.get("game", {}),
            "scene": graph_state.get("scene", {}),
            "off_topic_count": graph_state.get("off_topic_count", 0),  # Fallback count 저장
            # ✅ 미션 관련 상태 추가 (세션 간 유지 필요)
            "mission": graph_state.get("mission", {}),
            "temp_data": graph_state.get("temp_data", {}),
            "recruit_attempts": graph_state.get("recruit_attempts", {}),
            "allies_recruited": graph_state.get("allies_recruited", []),
            "recruit_order": graph_state.get("recruit_order", []),
        })

        logger.info("_convert_from_graph_state", "🔍 Updated state created",
                   turn_count=updated_state.get("turn_count"),
                   stage_turn=updated_state.get("stage_turn"))

        # DialogueResult 생성
        result = DialogueResult(
            dialogues=dialogues,
            next_stage=graph_state.get("output", {}).get("next_stage"),
            stage_complete=graph_state.get("output", {}).get("stage_complete", False),
            updated_state=updated_state,
            affinity_delta=graph_state.get("output", {}).get("affinity_delta"),
            affinity_scores=updated_state.get("affinity_scores", {}),  # 현재 친밀도 포함
            session_ended=graph_state.get("output", {}).get("session_ended", False)  # ✅ 세션 종료 플래그
        )

        return result

    async def _resolve_current_image(
        self,
        state: Dict[str, Any],
        scenario_id: str
    ) -> Optional[str]:
        """현재 스테이지에 맞는 이미지 식별자 조회"""
        scenario = state.get("scenario_id") or scenario_id
        stage_id = state.get("current_stage") or state.get("stage_tag")
        turn_count = state.get("turn_count", 0)

        if not scenario or not stage_id:
            return None

        try:
            image_data = await self.image_repository.get_best_image_for_stage(
                scenario_id=scenario,
                stage_id=stage_id,
                turn_count=turn_count
            )
        except Exception as e:
            logger.error(
                "_resolve_current_image",
                f"Failed to fetch image mapping: {e}",
                scenario=scenario,
                stage=stage_id
            )
            return None

        if not image_data:
            fallback = get_stage_image_identifier(scenario, stage_id)
            if fallback:
                return fallback
            return None

        metadata = image_data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        # 프론트엔드가 이해할 수 있는 고유 ID 우선 반환
        identifier_keys = [
            "background_id",
            "frontend_id",
            "frontend_name",
            "frontend_slug",
            "file_name",
            "fileName",
            "image_key",
            "image_id",
            "current_image",
            "image_index",
            "index",
            "frontend_index",
        ]
        for key in identifier_keys:
            value = metadata.get(key)
            if value not in (None, ""):
                return str(value)

        if image_data.get("image_key"):
            return image_data["image_key"]

        if metadata.get("file_name"):
            return metadata["file_name"]

        fallback = get_stage_image_identifier(scenario, stage_id)
        if fallback:
            return fallback

        return image_data.get("image_url")

    async def _load_or_create_session(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        user_name: str
    ) -> Dict[str, Any]:
        """세션 상태 로드 또는 생성"""
        existing_session = await self.session_repository.get_session(session_id)

        if existing_session:
            # 기존 세션 상태 로드
            logger.info("_load_or_create_session", "Loading existing session",
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
                    logger.info("_load_or_create_session", f"Loaded {len(affinity_scores)} affinity scores from DB for existing session",
                               user_id=user_id, scores=affinity_scores)
                except Exception as e:
                    logger.error("_load_or_create_session", f"Failed to load affinity scores for existing session: {e}",
                                user_id=user_id, exc_info=True)
                    # 에러 시에도 빈 dict로 초기화 (기존 로직 유지)
                    if "affinity_scores" not in session_state:
                        session_state["affinity_scores"] = {}
        else:
            # 신규 세션 생성
            logger.info("_load_or_create_session", "Creating new session", session_id=session_id)
            # Get first stage from scenario
            first_stage = self.scenario_service.get_first_stage_tag(scenario_id)

            # 사용자의 기존 친밀도를 DB에서 불러오기
            initial_affinity_scores = {}
            if user_id:
                try:
                    user_affinities = await self.affinity_repository.get_all_user_affinities(user_id)
                    for affinity in user_affinities:
                        initial_affinity_scores[affinity.character_name] = affinity.total_affinity_score
                    logger.info("_load_or_create_session", f"Loaded {len(initial_affinity_scores)} affinity scores from DB",
                               user_id=user_id, scores=initial_affinity_scores)
                except Exception as e:
                    logger.error("_load_or_create_session", f"Failed to load affinity scores: {e}",
                                user_id=user_id, exc_info=True)

            session_state = {
                "session_id": session_id,
                "scenario_id": scenario_id,
                "user_id": user_id,
                "user_name": user_name,
                "turn_count": 0,
                "stage_turn": 0,  # 초기화 추가
                "current_stage": first_stage,
                "affinity_scores": initial_affinity_scores,
            }

            # 신규 세션을 먼저 DB에 저장 (dialogue FK 위반 방지)
            logger.info("_load_or_create_session", "Saving new session to DB before dialogue insert")
            await self.session_repository.save_session(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                state=session_state
            )

        return session_state

    async def _load_memories(
        self,
        session_state: Dict[str, Any],
        user_id: str,
        scenario_id: str,
        session_id: str
    ) -> None:
        """메모리 로딩 - v2 (STM + LTM/Scenario Buffer + User Profile)"""
        from .middleware.mode_guard import ModeGuard

        is_freechat = ModeGuard.is_freechat(scenario_id)

        logger.info("_load_memories", "Loading memories (v2)",
                   user_id=user_id, scenario_id=scenario_id, session_id=session_id, is_freechat=is_freechat)

        # 1. User Profile 로딩 (항상)
        if hasattr(self, 'user_profile_repository') and self.user_profile_repository:
            try:
                profile_text = await self.user_profile_repository.get_profile_for_prompt(user_id)
                session_state["user_profile"] = profile_text
                logger.info("_load_memories", "Loaded user profile")
            except Exception as e:
                logger.warning("_load_memories", f"Failed to load user profile: {e}")
                session_state["user_profile"] = ""

        # 2. STM 로딩 (항상)
        if hasattr(self, 'stm_manager') and self.stm_manager:
            try:
                stm_text = await self.stm_manager.get_stm_for_prompt(user_id, scenario_id, session_id)
                if stm_text:
                    session_state["stm_summary"] = stm_text
                    logger.info("_load_memories", "Loaded STM")
            except Exception as e:
                logger.warning("_load_memories", f"Failed to load STM: {e}")

        # 3-A. LTM 로딩 (자유대화만) - 하이브리드 검색
        if is_freechat and user_id:
            try:
                if self.memory_repository and hasattr(self, 'embeddings_service') and self.embeddings_service:
                    # 사용자 입력 임베딩 생성
                    user_input = session_state.get("user_input", "")
                    if user_input:
                        try:
                            user_input_embedding = self.embeddings_service.embed(user_input)

                            # 유사도 검색
                            similar_memories = await self.memory_repository.search_similar_memories(
                                query_embedding=user_input_embedding,
                                user_id=user_id,
                                scenario_id="free-talk",
                                limit=10,
                                similarity_threshold=0.6
                            )

                            if similar_memories:
                                # 하이브리드 스코어링
                                for memory in similar_memories:
                                    memory["hybrid_score"] = (
                                        memory.get("similarity", 0) * 0.6 +
                                        memory.get("importance_score", memory.get("importance", 0.5)) * 0.4
                                    )

                                # 동적 개수 조정
                                recent_message_count = len(session_state.get("message_history", []))
                                if recent_message_count < 5:
                                    limit = 3
                                elif recent_message_count < 20:
                                    limit = 5
                                else:
                                    limit = 7

                                # 상위 N개 선택
                                top_memories = sorted(
                                    similar_memories,
                                    key=lambda m: m.get("hybrid_score", 0),
                                    reverse=True
                                )[:limit]

                                session_state["long_term_memories"] = top_memories
                                logger.info("_load_memories", f"Loaded {len(top_memories)} LTM (hybrid search)")
                        except Exception as embed_err:
                            logger.warning("_load_memories", f"Embedding search failed, fallback to importance: {embed_err}")
                            # Fallback: 중요도만 사용
                            memories = await self.memory_repository.get_user_memories(
                                user_id=user_id,
                                scenario_id="free-talk",
                                limit=20
                            )
                            if memories:
                                memories_sorted = sorted(
                                    memories,
                                    key=lambda m: (m.importance or 0, m.created_at or datetime.min),
                                    reverse=True
                                )
                                session_state["long_term_memories"] = [
                                    {
                                        "memory_id": m.id,
                                        "memory_key": m.memory_key,
                                        "content": m.memory_value,
                                        "type": m.memory_type,
                                        "importance": m.importance,
                                        "created_at": m.created_at.isoformat() if m.created_at else None
                                    }
                                    for m in memories_sorted[:5]
                                ]
                                logger.info("_load_memories", f"Loaded {len(memories_sorted[:5])} LTM (importance only)")
            except Exception as mem_err:
                logger.error("_load_memories", f"Failed to load LTM: {mem_err}")

        # 3-B. Scenario Buffer 로딩 (시나리오만)
        elif not is_freechat and user_id:
            if hasattr(self, 'scenario_buffer_manager') and self.scenario_buffer_manager:
                try:
                    buffer_text = await self.scenario_buffer_manager.get_buffer_for_prompt(user_id, scenario_id)
                    if buffer_text:
                        session_state["scenario_buffer"] = buffer_text
                        logger.info("_load_memories", "Loaded Scenario Buffer")
                except Exception as e:
                    logger.warning("_load_memories", f"Failed to load Scenario Buffer: {e}")

        logger.info("_load_long_term_memories", "DEBUG: Finished memory loading section")

    async def _check_and_return_prologue(
        self,
        session_state: Dict[str, Any],
        session_id: str,
        user_id: str,
        scenario_id: str
    ) -> Optional[DialogueResult]:
        """Prologue 체크 및 반환 (turn_count=0일 때만)"""
        if session_state["turn_count"] != 0:
            return None

        # DB에 이미 대화가 있는지 확인 (프롤로그가 이미 저장되었는지)
        existing_dialogues = await self.dialogue_repository.get_recent_dialogues(session_id, limit=1)

        # DB에 대화가 있으면 prologue 스킵
        if existing_dialogues:
            return None

        scenario = self.scenario_service.load_scenario(scenario_id)
        prologue_messages = scenario.get("prologue_messages") if scenario else None

        if not prologue_messages:
            return None

        logger.info("_check_and_return_prologue", "Returning hardcoded prologue messages",
                   scenario_id=scenario_id, count=len(prologue_messages))

        # 세션 상태 업데이트 (turn_count 증가, stage 유지)
        session_state["turn_count"] += 1

        # 세션 저장
        await self.session_repository.save_session(
            session_id=session_id,
            user_id=user_id,
            scenario_id=scenario_id,
            state=session_state
        )

        # prologue_messages를 DialogueTurn 모델로 변환
        dialogue_turns = []
        for idx, msg in enumerate(prologue_messages):
            dialogue_turn = DialogueTurn(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                turn_number=session_state["turn_count"],
                speaker=msg.get("speaker", "narr"),
                content=msg.get("text", ""),
                emotion=msg.get("emotion", "neutral"),
                order_index=idx
            )
            dialogue_turns.append(dialogue_turn)

        # 배치로 대화 저장 (prologue)
        saved_turns = await self.dialogue_repository.save_dialogues_batch(dialogue_turns)

        # DialogueResult 반환
        result = DialogueResult(
            session_id=session_id,
            scenario_id=scenario_id,
            current_stage=session_state["current_stage"],
            turn_count=session_state["turn_count"],
            dialogues=[
                ChatMessage(
                    speaker=turn.speaker,
                    text=turn.content,
                    emotion=turn.emotion
                ) for turn in saved_turns
            ],
            speaker_pool=[],
            next_stage=session_state["current_stage"],
            images=[]
        )

        # 1턴 프로로그는 항상 기본 컷 사용
        result.current_image = DEFAULT_FIRST_TURN_BACKGROUND
        logger.info("_check_and_return_prologue", "Prologue returned successfully",
                   session_id=session_id, turn_count=session_state["turn_count"])
        return result

    async def _save_dialogue_and_user_input(
        self,
        session_state: Dict[str, Any],
        dialogue_result: DialogueResult,
        session_id: str,
        user_id: str,
        scenario_id: str,
        user_message: str
    ) -> int:
        """대화 및 사용자 입력 저장"""
        turn_count = session_state.get("turn_count", 0) + 1

        # turn_count를 updated_state에 반영
        dialogue_result.updated_state["turn_count"] = turn_count

        # DialogueTurn 모델로 변환
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

        logger.info("_save_dialogue_and_user_input", f"Saving {len(dialogue_models)} dialogues to DB")
        await self.dialogue_repository.save_dialogues_batch(dialogue_models)

        # 사용자 입력 저장
        if user_message:
            from ..chat.models import UserInput

            user_input_model = UserInput(
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_count,
                user_input=user_message,
                timestamp=datetime.utcnow(),
                created_at=datetime.utcnow()
            )

            self.db.add(user_input_model)
            await self.db.flush()

            logger.debug("_save_dialogue_and_user_input", f"User input saved for turn {turn_count}")

        return turn_count

    async def _process_summary_and_memories(
        self,
        dialogue_result: DialogueResult,
        session_id: str,
        user_id: str,
        scenario_id: str = "free-talk",
        scenario_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """대화 요약 생성 및 장기기억 추출"""
        logger.info("_process_summary_and_memories",
                   f"Called with user_id={user_id}, summarizer={self.summarizer is not None}")

        if not self.summarizer or not user_id:
            logger.warning("_process_summary_and_memories",
                          f"Skipped: summarizer={self.summarizer is not None}, user_id={user_id}")
            return

        try:
            # MessageHistoryService로 통합 메시지 로드
            message_history_full = await self.message_history_service.load_full_message_history(
                session_id=session_id,
                limit=50
            )

            # Summarizer가 요구하는 포맷으로 변환
            turn_data = {}
            for msg in message_history_full:
                turn = msg["turn"]
                if turn not in turn_data:
                    turn_data[turn] = {"user_input": "", "agent_responses": []}

                if msg["speaker"] == "{{user}}":
                    turn_data[turn]["user_input"] = msg.get("text", "")
                else:
                    turn_data[turn]["agent_responses"].append({
                        "speaker": msg["speaker"],
                        "text": msg.get("text", "")
                    })

            message_history = [
                {"turn": turn, **data}
                for turn, data in sorted(turn_data.items())
            ]

            # 요약 업데이트 체크 (10개 메시지마다)
            summary_result = await self.summarizer.update_summary(
                state=dialogue_result.updated_state,
                message_history=message_history
            )

            # 새 요약이 생성되었으면 저장
            if summary_result["summary"] != dialogue_result.updated_state.get("conversation_summary"):
                dialogue_result.updated_state["conversation_summary"] = summary_result["summary"]
                dialogue_result.updated_state["last_summary_message_count"] = summary_result["last_summary_message_count"]
                logger.info("_process_summary_and_memories",
                           f"Summary updated: {summary_result['last_summary_message_count']} messages summarized")

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
                        scenario_config=scenario_config,
                        importance_score=0.8
                    )
                    logger.info("_process_summary_and_memories", "Summary saved to memories",
                               session_id=session_id, summary_length=len(summary_result["summary"]))

                # 장기기억 추출
                if self.memory_extractor and self.embeddings_service:
                    try:
                        logger.info("_process_summary_and_memories", "Extracting long-term memories from summary",
                                   session_id=session_id)

                        extracted_memories = await self.memory_extractor.extract_memories(
                            conversation_summary=summary_result["summary"]
                        )

                        logger.info("_process_summary_and_memories",
                                   f"Extracted {len(extracted_memories)} long-term memories",
                                   session_id=session_id)

                        # 추출된 메모리 저장
                        saved_memories = []
                        for memory in extracted_memories:
                            try:
                                memory_embedding = self.embeddings_service.embed(memory.memory_value)

                                await self.memory_repository.create_memory(
                                    user_id=user_id,
                                    content=memory.memory_value,
                                    memory_type=memory.memory_type,
                                    embedding=memory_embedding,
                                    scenario_id=scenario_id,
                                    scenario_config=scenario_config,
                                    importance_score=memory.importance
                                )

                                logger.debug("_process_summary_and_memories", f"Saved memory: {memory.memory_key}",
                                            type=memory.memory_type, importance=memory.importance)

                                saved_memories.append(memory)

                            except Exception as mem_err:
                                logger.error("_process_summary_and_memories",
                                           f"Failed to save individual memory: {mem_err}",
                                           memory_key=memory.memory_key, exc=mem_err)

                        logger.info("_process_summary_and_memories",
                                   f"Successfully saved {len(saved_memories)} long-term memories",
                                   session_id=session_id, user_id=user_id)

                        # 메모리 저장 이벤트 생성
                        if saved_memories:
                            from .schemas import MemoryEvent
                            character_name = dialogue_result.dialogues[-1].speaker if dialogue_result.dialogues else "AI"

                            for memory in saved_memories:
                                event = MemoryEvent(
                                    event_type="saved",
                                    character_name=character_name,
                                    memory_type=memory.memory_type,
                                    memory_content=memory.memory_value[:100],
                                    importance=memory.importance,
                                    count=None
                                )
                                dialogue_result.memory_events.append(event)

                    except Exception as extract_err:
                        logger.error("_process_summary_and_memories", f"Memory extraction failed: {extract_err}",
                                   session_id=session_id, exc=extract_err)

            # v2: STM 업데이트 (5턴마다 요약 트리거)
            if hasattr(self, 'stm_manager') and self.stm_manager:
                try:
                    scenario_id = dialogue_result.updated_state.get("scenario_id", "free-talk")

                    # STM 업데이트 전에 현재 chunk 개수 확인
                    stm_before = None
                    if hasattr(self, 'stm_repository') and self.stm_repository:
                        stm_before = await self.stm_repository.get_stm(user_id, scenario_id, session_id)

                    chunk_count_before = len(stm_before.chunk_summaries) if stm_before and stm_before.chunk_summaries else 0

                    await self.stm_manager.update_stm(
                        user_id=user_id,
                        scenario_id=scenario_id,
                        session_id=session_id,
                        new_turn_data={
                            "user_input": dialogue_result.updated_state.get("user_input", ""),
                            "agent_responses": [
                                {"speaker": d.speaker, "text": d.text}
                                for d in dialogue_result.dialogues
                            ]
                        },
                        message_history=message_history
                    )
                    logger.info("_process_summary_and_memories", "STM updated (v2)")

                    # v2: 새 chunk가 생성되었으면 LTM 추출 (free-talk 전용)
                    if scenario_id == "free-talk":
                        stm_after = await self.stm_repository.get_stm(user_id, scenario_id, session_id)
                        chunk_count_after = len(stm_after.chunk_summaries) if stm_after and stm_after.chunk_summaries else 0

                        # 새 chunk가 추가되었고, MemoryExtractor와 embeddings_service가 있으면 LTM 추출
                        if chunk_count_after > chunk_count_before and self.memory_extractor and self.embeddings_service:
                            try:
                                latest_chunk = stm_after.chunk_summaries[-1]
                                chunk_summary = latest_chunk.get("summary", "")

                                if chunk_summary and len(chunk_summary) > 50:
                                    logger.info("_process_summary_and_memories",
                                               f"Extracting LTM from new chunk (v2): {latest_chunk.get('turn_range')}",
                                               session_id=session_id)

                                    extracted_memories = await self.memory_extractor.extract_memories(
                                        conversation_summary=chunk_summary
                                    )

                                    logger.info("_process_summary_and_memories",
                                               f"Extracted {len(extracted_memories)} memories from chunk (v2)",
                                               session_id=session_id)

                                    # 추출된 메모리 저장
                                    saved_count = 0
                                    for memory in extracted_memories:
                                        try:
                                            memory_embedding = self.embeddings_service.embed(memory.memory_value)

                                            # Entity 이름을 entity_id로 변환
                                            entity_ids = []
                                            if memory.related_entities and self.entity_repository:
                                                for entity_name in memory.related_entities:
                                                    try:
                                                        # 먼저 기존 엔티티 검색
                                                        entity = await self.entity_repository.get_entity_by_name(entity_name)
                                                        if entity:
                                                            entity_ids.append(entity.entity_id)
                                                        else:
                                                            # 없으면 새로 생성 (character 타입으로 가정)
                                                            new_entity = await self.entity_repository.create_entity(
                                                                entity_type="character",
                                                                entity_name=entity_name,
                                                                canonical_name=entity_name.lower()
                                                            )
                                                            entity_ids.append(new_entity.entity_id)
                                                            logger.debug("_process_summary_and_memories",
                                                                        f"Created new entity: {entity_name}")
                                                    except Exception as entity_err:
                                                        logger.warning("_process_summary_and_memories",
                                                                      f"Failed to process entity {entity_name}: {entity_err}")

                                            await self.memory_repository.create_memory(
                                                user_id=user_id,
                                                content=memory.memory_value,
                                                memory_type=memory.memory_type,
                                                embedding=memory_embedding,
                                                scenario_id=scenario_id,
                                                scenario_config=scenario_config,
                                                importance_score=memory.importance,
                                                tags=memory.tags,
                                                confidence=memory.confidence,
                                                source_session_id=session_id,
                                                related_entity_ids=entity_ids  # 엔티티 ID 추가
                                            )

                                            saved_count += 1
                                            logger.debug("_process_summary_and_memories",
                                                        f"Saved LTM (v2): {memory.memory_key}",
                                                        type=memory.memory_type, importance=memory.importance,
                                                        tags=memory.tags, entities=len(entity_ids))

                                        except Exception as mem_err:
                                            logger.error("_process_summary_and_memories",
                                                       f"Failed to save memory (v2): {mem_err}",
                                                       memory_key=memory.memory_key, exc_info=True)

                                    logger.info("_process_summary_and_memories",
                                               f"Saved {saved_count}/{len(extracted_memories)} LTM (v2)",
                                               session_id=session_id)

                            except Exception as ltm_err:
                                logger.error("_process_summary_and_memories",
                                           f"LTM extraction from chunk failed (v2): {ltm_err}",
                                           exc_info=True)

                    # v2: Scenario Buffer 업데이트 (시나리오 모드 전용)
                    elif scenario_id != "free-talk":
                        if hasattr(self, 'scenario_buffer_manager') and self.scenario_buffer_manager:
                            try:
                                # STM chunk summary를 scenario buffer summary로 사용
                                stm_after = await self.stm_repository.get_stm(user_id, scenario_id, session_id)
                                if stm_after and stm_after.chunk_summaries:
                                    # 모든 chunk를 하나의 buffer summary로 통합
                                    buffer_summary = "\n\n".join([
                                        f"[{chunk.get('turn_range')}턴] {chunk.get('summary')}"
                                        for chunk in stm_after.chunk_summaries
                                    ])

                                    # Progress data 추출 (현재 stage, turn count 등)
                                    progress_data = {
                                        "current_stage": dialogue_result.updated_state.get("current_stage"),
                                        "stage_turn": dialogue_result.updated_state.get("stage_turn", 0),
                                        "total_turns": len(message_history)
                                    }

                                    await self.scenario_buffer_manager.update_buffer(
                                        user_id=user_id,
                                        scenario_id=scenario_id,
                                        buffer_summary=buffer_summary,
                                        progress_data=progress_data
                                    )
                                    logger.info("_process_summary_and_memories",
                                               f"Scenario Buffer updated for {scenario_id}")
                            except Exception as buffer_err:
                                logger.error("_process_summary_and_memories",
                                           f"Scenario Buffer update failed: {buffer_err}",
                                           exc_info=True)

                except Exception as stm_err:
                    logger.error("_process_summary_and_memories", f"STM update failed: {stm_err}", exc_info=True)

        except Exception as e:
            logger.error("_process_summary_and_memories", f"Summary generation failed: {e}", exc=e)

    async def _save_affinity_scores(
        self,
        dialogue_result: DialogueResult,
        session_id: str,
        user_id: str,
        turn_count: int
    ) -> None:
        """친밀도 점수를 DB에 저장"""
        if not user_id or not dialogue_result.affinity_scores:
            return

        try:
            for character_name, score in dialogue_result.affinity_scores.items():
                # 세션별 친밀도 변화 기록
                await self.affinity_repository.save_affinity_record(
                    session_id=session_id,
                    turn_number=turn_count,
                    character_name=character_name,
                    affinity_score=score,
                    change_amount=None
                )

                # 사용자별 글로벌 친밀도 업데이트
                existing_affinity = await self.affinity_repository.get_user_character_affinity(
                    user_id=user_id,
                    character_name=character_name
                )

                if existing_affinity:
                    delta = score - existing_affinity.total_affinity_score
                    if delta != 0:
                        await self.affinity_repository.upsert_user_character_affinity(
                            user_id=user_id,
                            character_name=character_name,
                            score_delta=delta
                        )
                else:
                    await self.affinity_repository.upsert_user_character_affinity(
                        user_id=user_id,
                        character_name=character_name,
                        score_delta=score
                    )

            logger.info("_save_affinity_scores", "Affinity scores saved to DB",
                       user_id=user_id, characters=list(dialogue_result.affinity_scores.keys()))
        except Exception as e:
            logger.error("_save_affinity_scores", f"Failed to save affinity scores: {e}",
                        user_id=user_id, exc_info=True)

    async def _update_user_progression(
        self,
        session_id: str,
        user_id: str,
        scenario_id: str,
        user_message: str,
        turn_count: int
    ) -> None:
        """사용자 진행도 업데이트"""
        if not user_id:
            return

        try:
            from uuid import UUID

            # 1. 사용자 입력 저장 (✅ 중복 제거: _save_dialogue_and_user_input에서 이미 저장됨)
            # await self.progression_repository.save_user_input(
            #     session_id=UUID(session_id),
            #     turn_number=turn_count,
            #     user_input=user_message
            # )

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
                await self.progression_repository.update_scenario_progress(
                    user_id=UUID(user_id),
                    scenario_id=scenario_id,
                    progress_data={
                        "has_started": True,
                        "total_messages": 1,
                        "last_session_id": session_id
                    }
                )

            # 4. XP 지급
            xp_result = await self.progression_repository.award_experience(
                user_id=UUID(user_id),
                xp_amount=5,
                xp_type="message",
                description=f"Message in {scenario_id}",
                metadata={"message_length": len(user_message)}
            )

            logger.info("_update_user_progression", "Progression updated",
                       user_id=user_id,
                       xp_awarded=5,
                       level_before=xp_result.get("level_before"),
                       level_after=xp_result.get("level_after"),
                       did_level_up=xp_result.get("did_level_up"))

        except Exception as e:
            logger.error("_update_user_progression", f"Progression update failed: {e}", exc=e)

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
            session_state = await self._load_or_create_session(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                user_name=user_name
            )

            # ============================================================
            # 1.5 메모리 로딩 (v2: STM + LTM/Scenario Buffer + User Profile)
            # ============================================================
            await self._load_memories(
                session_state=session_state,
                user_id=user_id,
                scenario_id=scenario_id,
                session_id=session_id
            )

            # ============================================================
            # 2. 정책: 일일 대화 제한 체크 (비활성화)
            # ============================================================
            # today_count = await self.dialogue_repository.count_today(user_id)
            # logger.debug("create_dialogue", f"Today's dialogue count: {today_count}", user_id=user_id, count=today_count)

            # if today_count >= MAX_DAILY_CHATS:
            #     logger.warning("create_dialogue", "Daily limit exceeded", user_id=user_id, count=today_count, limit=MAX_DAILY_CHATS)
            #     raise DailyLimitExceededException(MAX_DAILY_CHATS)

            # ============================================================
            # 2.5 Prologue 체크: turn_count가 0이고 DB에 대화가 없으면 프롤로그 반환
            # ============================================================
            prologue_result = await self._check_and_return_prologue(
                session_state=session_state,
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id
            )
            if prologue_result:
                return prologue_result

            # ============================================================
            # 3. message_history 로드 (LangGraph/Legacy 공통)
            # ============================================================
            # ✅ MessageHistoryService를 사용하여 message_history 로드
            message_history = await self.message_history_service.load_full_message_history(
                session_id=session_id,
                limit=50
            )

            # message_history를 session_state에 추가
            session_state["message_history"] = message_history
            logger.info("create_dialogue",
                       f"Loaded {len(message_history)} messages for context",
                       session_id=session_id)

            # ============================================================
            # 4. Agent 파이프라인 실행 (LangGraph 또는 Legacy)
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
                    # ✅ CRITICAL FIX: scenario 데이터를 session_state에 추가
                    scenario_data = self.scenario_service.load_scenario(scenario_id)
                    if scenario_data:
                        session_state["scenario_data"] = scenario_data
                        logger.info("create_dialogue",
                                   "Loaded scenario data for context",
                                   scenario_id=scenario_id,
                                   stages_count=len(scenario_data.get("stages", [])))

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
            # 5. 현재 스테이지용 이미지 선택 (하이브리드 방식)
            # ============================================================
            predicted_turn = (session_state.get("turn_count", 0) or 0) + 1
            resolved_image = None

            if predicted_turn == 1:
                resolved_image = DEFAULT_FIRST_TURN_BACKGROUND
            else:
                # 1단계: 키워드 검색
                keyword_match = _select_background_by_keywords(
                    scenario_id,
                    dialogue_result.dialogues or []
                )

                if keyword_match and keyword_match[1] >= 9:
                    # 점수가 9점 이상이면 키워드 매칭 결과 사용
                    resolved_image = keyword_match[0]
                    logger.info("create_dialogue", f"Image selected by keyword score >= 9: {resolved_image}")

                # 2단계: 스테이지 매핑 (키워드 미적용 시)
                if not resolved_image:
                    try:
                        resolved_image = await self._resolve_current_image(
                            state=dialogue_result.updated_state,
                            scenario_id=scenario_id
                        )
                        if resolved_image:
                            logger.info("create_dialogue", f"Image selected by stage mapping: {resolved_image}")
                    except Exception as e:
                        logger.error("create_dialogue", f"Stage mapping lookup failed: {e}")

                if not resolved_image:
                    # 3단계: 임베딩 검색
                    if keyword_match:
                        logger.info("create_dialogue", f"Keyword score {keyword_match[1]} < 9. Falling back to embedding search.")
                    else:
                        logger.info("create_dialogue", "No keyword match. Falling back to embedding search.")

                    if self.embeddings_service:
                        try:
                            # 비교 대상: 이전 턴의 전체 대화 (사용자 입력 + AI 응답)
                            dialogue_text = ""
                            previous_turn_number = session_state.get("turn_count", 0)

                            if previous_turn_number > 0:
                                # message_history는 이미 로드되어 있음
                                turn_messages = [
                                    msg.get("text", "")
                                    for msg in message_history
                                    if msg.get("turn") == previous_turn_number
                                ]
                                if turn_messages:
                                    dialogue_text = "\n".join(turn_messages)
                                    logger.info("create_dialogue", f"Using full context from turn {previous_turn_number} for embedding search.")

                            # Fallback to last dialogue if history is unavailable
                            if not dialogue_text and dialogue_result.dialogues:
                                last_dialogue = dialogue_result.dialogues[-1]
                                dialogue_text = last_dialogue.text
                                logger.info("create_dialogue", "Fell back to last dialogue text for embedding search.")

                            if dialogue_text:
                                # 대화 내용 임베딩
                                query_embedding = self.embeddings_service.embed(dialogue_text)
                                
                                # 이미지 설명 임베딩 (캐시됨)
                                candidate_embeddings = _get_image_description_embeddings(scenario_id)

                                if query_embedding and candidate_embeddings:
                                    # 가장 유사한 이미지 찾기
                                    similar_images = self.embeddings_service.find_most_similar(
                                        query_embedding,
                                        candidate_embeddings,
                                        top_k=1
                                    )
                                    if similar_images:
                                        resolved_image = similar_images[0][0]
                                        logger.info("create_dialogue", f"Image selected by embedding search: {resolved_image} (Score: {similar_images[0][1]:.2f})")
                        except Exception as e:
                            logger.error("create_dialogue", f"Embedding search for image failed: {e}")

                # 최종 폴백: 동적 선택 실패 시, 가장 많이 말한 화자의 기본 이미지 사용
                if not resolved_image:
                    speaker_fallback = _fallback_image_by_top_speaker(dialogue_result.dialogues or [])
                    if speaker_fallback:
                        resolved_image = speaker_fallback
                        logger.info("create_dialogue", f"Image selected by speaker fallback: {resolved_image}")

            dialogue_result.current_image = resolved_image

            # ============================================================
            # 6. 대화 및 사용자 입력 저장
            # ============================================================
            turn_count = await self._save_dialogue_and_user_input(
                session_state=session_state,
                dialogue_result=dialogue_result,
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                user_message=user_message
            )

            # ============================================================
            # 7. 대화 요약 생성 및 Memory 저장
            # ============================================================
            # scenario 데이터 가져오기 (LangGraph/Legacy 모두 사용)
            scenario_data = session_state.get("scenario_data")
            if not scenario_data:
                scenario_data = self.scenario_service.load_scenario(scenario_id)

            await self._process_summary_and_memories(
                dialogue_result=dialogue_result,
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                scenario_config=scenario_data
            )

            # ============================================================
            # 8. 세션 상태 저장
            # ============================================================
            try:
                logger.info("create_dialogue", "🔍 Before saving session to DB",
                           turn_count=dialogue_result.updated_state.get("turn_count"),
                           stage_turn=dialogue_result.updated_state.get("stage_turn"))

                await self.session_repository.save_session(
                    session_id=session_id,
                    user_id=user_id,
                    scenario_id=scenario_id,
                    state=dialogue_result.updated_state
                )

                logger.info("create_dialogue", "🔍 Session saved to DB")

                # ✅ 엔딩 스테이지 도달 시 final_ending 저장
                if dialogue_result.session_ended:
                    current_stage = dialogue_result.updated_state.get("current_stage")
                    if current_stage and current_stage.startswith("END_"):
                        await self.session_repository.update_session_state(
                            session_id=session_id,
                            final_ending=current_stage,
                            is_active=False  # 세션 종료
                        )
                        logger.info("create_dialogue", f"🏁 Final ending saved: {current_stage}", session_id=session_id)

            except Exception as session_save_err:
                logger.warning("create_dialogue", f"Session save failed (memories already saved): {session_save_err}",
                             session_id=session_id)

            # ============================================================
            # 9. 친밀도 저장
            # ============================================================
            await self._save_affinity_scores(
                dialogue_result=dialogue_result,
                session_id=session_id,
                user_id=user_id,
                turn_count=turn_count
            )

            # ============================================================
            # 10. Progression 업데이트
            # ============================================================
            await self._update_user_progression(
                session_id=session_id,
                user_id=user_id,
                scenario_id=scenario_id,
                user_message=user_message,
                turn_count=turn_count
            )

            # ============================================================
            # 11. 결과 반환
            # ============================================================
            logger.info("create_dialogue", "Transaction committed", dialogues_saved=len(dialogue_result.dialogues))
            print_layer_debug("USECASE", "Chat", "create_dialogue", "✅ Completed", dialogues=len(dialogue_result.dialogues))

            return dialogue_result

    async def get_recent_dialogues(
        self,
        session_id: str,
        limit: int = 500
    ) -> list[ChatMessage]:
        """최근 대화 조회 (유저 입력 + NPC 대화 통합) - API 응답용"""
        logger.info("get_recent_dialogues", "Fetching recent dialogues", session_id=session_id, limit=limit)

        # MessageHistoryService로 통합 메시지 로드
        message_history = await self.message_history_service.load_full_message_history(
            session_id=session_id,
            limit=limit
        )

        # 최근 N개만 선택
        recent = message_history[-limit:] if len(message_history) > limit else message_history

        # 유저 이름 가져오기
        session = await self.session_repository.get_session(session_id)
        user_name = session.user_name if session else "User"

        # ChatMessage DTO로 변환 + {{user}} 치환
        messages = []
        for idx, msg in enumerate(recent):
            # ✅ {{user}} placeholder로 유저 메시지 판별
            is_user_message = msg["speaker"] == "{{user}}"

            speaker = msg["speaker"].replace("{{user}}", user_name)
            text = msg.get("text", "")
            if text:
                text = text.replace("{{user}}", user_name).replace("{user}", user_name)

            # 🔍 디버깅: 처음 5개 메시지 로그
            if idx < 5:
                logger.info("get_recent_dialogues",
                           f"[{idx}] original_speaker={msg['speaker']}, is_user={is_user_message}, "
                           f"final_speaker={speaker}, text={text[:30]}")

            messages.append(ChatMessage(
                speaker=speaker,
                text=text,
                is_user=is_user_message,  # ✅ 명시적으로 is_user 설정
                emotion=msg.get("emotion", "neutral"),
                timestamp=None  # message_history에는 timestamp 없음
            ))

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

    async def finalize_session(
        self,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        세션 종료 처리: 남은 대화 요약 및 메모리 추출

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID

        Returns:
            종료 결과 dict
        """
        logger.info("finalize_session", f"Finalizing session {session_id}", user_id=user_id)

        try:
            # 1. 세션 상태 조회
            session_data = await self.session_repository.get_session(session_id)
            if not session_data:
                logger.warning("finalize_session", f"Session not found: {session_id}")
                return {
                    "success": False,
                    "error": "Session not found",
                    "memories_created": 0
                }

            session_state = session_data["state"]
            scenario_id = session_data["scenario_id"]

            # 2. 최근 대화 조회
            recent_dialogues = await self.dialogue_repository.get_recent_dialogues(session_id, limit=50)

            if not recent_dialogues:
                logger.info("finalize_session", "No dialogues to process", session_id=session_id)
                # 세션을 비활성화
                await self.session_repository.delete_session(session_id)
                return {
                    "success": True,
                    "memories_created": 0,
                    "message": "No dialogues to process"
                }

            # 3. 사용자 입력 조회
            from ..chat.models import UserInput
            from sqlalchemy import select

            user_inputs_query = select(UserInput).where(
                UserInput.session_id == session_id
            ).order_by(UserInput.turn_number)

            user_inputs_result = await self.db.execute(user_inputs_query)
            user_inputs_list = list(user_inputs_result.scalars().all())

            # turn_number → user_input 매핑
            user_inputs_map = {
                ui.turn_number: ui.user_input
                for ui in user_inputs_list
            }

            # 4. 대화 히스토리 구성 (turn별로 그룹화)
            turn_dialogues = {}
            for dlg in recent_dialogues:
                if dlg.turn_number not in turn_dialogues:
                    turn_dialogues[dlg.turn_number] = []
                turn_dialogues[dlg.turn_number].append({
                    "speaker": dlg.speaker,
                    "text": dlg.content
                })

            # message_history 구성
            message_history = []
            for turn_num in sorted(turn_dialogues.keys()):
                message_history.append({
                    "turn": turn_num,
                    "user_input": user_inputs_map.get(turn_num, ""),
                    "agent_responses": turn_dialogues[turn_num]
                })

            # 5. 강제 요약 생성 (summarizer가 있는 경우)
            memories_created = 0
            if self.summarizer and message_history:
                try:
                    logger.info("finalize_session", "Generating final summary", session_id=session_id)

                    # 시나리오 컨텍스트
                    scenario_context = f"시나리오: {scenario_id}"

                    # 요약 생성
                    summary_text = await self.summarizer.generate_summary(
                        conversations=message_history,
                        existing_summary=session_state.get("conversation_summary", ""),
                        scenario_context=scenario_context
                    )

                    logger.info("finalize_session", f"Final summary generated ({len(summary_text)} chars)",
                               session_id=session_id)

                    # 6. 장기기억 추출 (요약에서)
                    if self.memory_extractor and self.embeddings_service and summary_text:
                        try:
                            logger.info("finalize_session", "Extracting final memories", session_id=session_id)

                            # 메모리 추출
                            extracted_memories = await self.memory_extractor.extract_memories(
                                conversation_summary=summary_text
                            )

                            logger.info("finalize_session", f"Extracted {len(extracted_memories)} memories",
                                       session_id=session_id)

                            # 메모리 저장
                            for memory in extracted_memories:
                                try:
                                    # 임베딩 생성
                                    memory_embedding = self.embeddings_service.embed(memory.memory_value)

                                    # scenario config 로드
                                    scenario_config = self.scenario_service.load_scenario(scenario_id)

                                    # 메모리 저장
                                    await self.memory_repository.create_memory(
                                        user_id=user_id,
                                        content=memory.memory_value,
                                        memory_type=memory.memory_type,
                                        embedding=memory_embedding,
                                        scenario_id=scenario_id,
                                        scenario_config=scenario_config,
                                        importance_score=memory.importance
                                    )
                                    memories_created += 1
                                except Exception as mem_err:
                                    logger.error("finalize_session", f"Failed to save memory: {mem_err}",
                                               session_id=session_id)

                            logger.info("finalize_session", f"Saved {memories_created} memories",
                                       session_id=session_id)

                        except Exception as extract_err:
                            logger.error("finalize_session", f"Memory extraction failed: {extract_err}",
                                       session_id=session_id)

                except Exception as summary_err:
                    logger.error("finalize_session", f"Summary generation failed: {summary_err}",
                               session_id=session_id)

            # 7. 세션 비활성화
            await self.session_repository.delete_session(session_id)
            logger.info("finalize_session", "Session finalized successfully",
                       session_id=session_id, memories_created=memories_created)

            return {
                "success": True,
                "memories_created": memories_created,
                "message": "Session finalized successfully"
            }

        except Exception as e:
            logger.error("finalize_session", f"Session finalization failed: {e}",
                        session_id=session_id, exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "memories_created": 0
            }
