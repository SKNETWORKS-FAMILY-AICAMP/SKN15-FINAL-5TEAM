"""
Children Agent - 대화 생성 에이전트

Features:
- ParentAgent가 전달한 children_ctx 기반 대화 생성
- LLMService를 사용한 beat 기반 대화 생성
- 대화 품질 관리
"""
from typing import Dict, Any, List, Optional

from app.core.logging import get_parent_logger
from app.core.llm.prompt_service import get_prompt_service
from app.features.chat.services import LLMService, DialogueService

logger = get_parent_logger("ChildrenAgent")
prompt_service = get_prompt_service()


class ChildrenAgent:
    """
    대화 생성 에이전트 (Layer 3 - Agent)

    ParentAgent가 구성한 children_ctx를 받아 실제 대화를 생성합니다.

    Features:
    - run(): children_ctx 기반 대화 생성
    - LLMService 활용
    - DialogueService를 통한 포맷팅

    Example:
        agent = ChildrenAgent(llm_service=llm)

        state = agent.run(state)
        dialogues = state.get("agent_responses", [])
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        dialogue_service: Optional[DialogueService] = None
    ):
        """
        Args:
            llm_service: LLMService 인스턴스
            dialogue_service: DialogueService 인스턴스
        """
        self.llm_service = llm_service or LLMService()
        self.dialogue_service = dialogue_service or DialogueService()

        logger.info("__init__", "ChildrenAgent initialized")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        대화 생성 메인 엔트리 포인트

        Args:
            state: 게임 상태 (children_ctx 포함)

        Returns:
            업데이트된 state (agent_responses 포함)
        """
        # children_ctx 추출
        ctx = self._extract_context(state)

        if not ctx:
            logger.warning("run", "No children_ctx found, returning empty response")
            state["agent_responses"] = []
            state["has_more_dialogues"] = False
            return state

        logger.debug("run", "Generating dialogues",
                    beats_count=len(ctx.get("beats", [])))

        # 대화 생성
        dialogues = await self._generate_dialogues(ctx, state)

        # 결과 저장 (렌더링은 나중에 Controller/UseCase에서 수행)
        state["agent_responses"] = dialogues
        state["has_more_dialogues"] = False

        logger.info("run", "Dialogues generated",
                   count=len(dialogues))

        return state

    def _extract_context(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """children_ctx 추출"""
        ctx = state.get("children_ctx")

        if not isinstance(ctx, dict):
            logger.warning("_extract_context", "children_ctx is not a dict")
            return None

        return ctx

    async def _generate_dialogues(
        self,
        ctx: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Beats 기반 대화 생성 (prompts.yaml 사용)

        Layer 3 (Agent): 비즈니스 로직만 처리, 프롬프트는 Layer 4 (PromptService)에서 가져옴

        Args:
            ctx: children_ctx
            state: 게임 상태

        Returns:
            생성된 대화 리스트
        """
        beats = ctx.get("beats", [])
        speaker_pool = ctx.get("speaker_pool", [])
        scenario_id = ctx.get("scenario_id", "unknown")

        if not beats:
            logger.warning("_generate_dialogues", "No beats provided")
            return []

        # 컨텍스트 정보 준비
        recent_dialogues = state.get("recent_dialogues", [])
        user_input = state.get("user_input", "")
        current_turn = state.get("turn_count", 0)
        user_name = state.get("user_name", "츠구코")

        logger.info("_generate_dialogues", f"Post-processing will replace '{user_name}' with '{{user}}'")

        # Beat 설명 결합
        beat_descriptions = []
        for beat in beats:
            if isinstance(beat, dict):
                desc = beat.get("goal") or beat.get("description") or beat.get("text") or str(beat)
                beat_descriptions.append(desc)
            elif isinstance(beat, str):
                beat_descriptions.append(beat)
        beats_description = "\n".join(beat_descriptions) if beat_descriptions else "일반 대화"

        logger.info("_generate_dialogues", f"Generating dialogues for {len(beats)} beats",
                    speaker_pool=speaker_pool, turn=current_turn)

        try:
            # Layer 4 (PromptService)에서 프롬프트 생성
            prompt = prompt_service.get_dialogue_generation_prompt(
                beats_description=beats_description,
                speaker_pool=speaker_pool,
                user_input=user_input,
                recent_dialogues=recent_dialogues,
                current_turn=current_turn,
                max_turns=len(beats) + 5,
                # 향후 추가할 컨텍스트
                tone_profile=None,
                atmosphere=None,
                scene_setting=None,
                previous_scene_summary=None,
                previous_emotion_tone=None,
                spatial_continuity=None,
                character_states=None,
                transition_hint=None
            )

            # Layer 4 (LLMService)로 대화 생성
            dialogues_messages = await self.llm_service.generate_with_prompt(
                prompt=prompt,
                temperature=0.8,
                max_tokens=2000
            )

            logger.info("_generate_dialogues", f"LLM returned {len(dialogues_messages) if dialogues_messages else 0} messages")

        except Exception as e:
            logger.error("_generate_dialogues", f"LLM call failed: {e}", exc_info=True)
            return []

        if not dialogues_messages:
            logger.warning("_generate_dialogues", "LLM returned empty list")
            return []

        # Post-processing: ChatMessage -> dict 변환 및 플레이어 이름 치환
        dialogue_dicts = []

        for i, msg in enumerate(dialogues_messages):
            try:
                # Handle ChatMessage object
                if hasattr(msg, 'speaker'):
                    dialogue_dict = {
                        "speaker": msg.speaker,
                        "text": msg.text,
                        "emotion": msg.emotion if hasattr(msg, 'emotion') else "neutral"
                    }
                # Handle dict
                elif isinstance(msg, dict):
                    dialogue_dict = {
                        "speaker": msg.get("speaker", "narr"),
                        "text": msg.get("text", ""),
                        "emotion": msg.get("emotion", "neutral")
                    }
                # Handle unexpected type
                else:
                    logger.warning("_generate_dialogues", f"Unexpected message type at index {i}: {type(msg)}, value: {msg}")
                    continue

                # Post-processing: Replace user name with {user} placeholder
                if user_name in dialogue_dict["text"]:
                    original_text = dialogue_dict["text"]
                    dialogue_dict["text"] = dialogue_dict["text"].replace(user_name, "{user}")
                    logger.info("_generate_dialogues", f"✏️ Replaced '{user_name}' → '{{user}}' | {original_text} → {dialogue_dict['text']}")

                # Skip if LLM generated player dialogue (플레이어 대사 생성 금지 실패 시)
                if dialogue_dict["speaker"] == user_name:
                    logger.warning("_generate_dialogues", f"LLM generated player dialogue (speaker={user_name}), skipping")
                    continue

                dialogue_dicts.append(dialogue_dict)

            except Exception as e:
                logger.error("_generate_dialogues", f"Error converting message {i}: {e}", exc_info=True)
                continue

        logger.info("_generate_dialogues", f"Generated {len(dialogue_dicts)} dialogues from {len(beats)} beats")

        return dialogue_dicts


# 싱글톤 인스턴스
_default_agent: Optional[ChildrenAgent] = None


def get_children_agent() -> ChildrenAgent:
    """ChildrenAgent 싱글톤"""
    global _default_agent
    if _default_agent is None:
        _default_agent = ChildrenAgent()
    return _default_agent


async def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ChildrenAgent 실행 헬퍼

    Args:
        state: 게임 상태

    Returns:
        업데이트된 state
    """
    agent = get_children_agent()
    return await agent.run(state)


__all__ = ["ChildrenAgent", "get_children_agent", "run_children_agent"]
