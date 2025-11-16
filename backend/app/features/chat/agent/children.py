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
from app.features.chat.services import LLMService, DialogueService, ScenarioService

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
        dialogue_service: Optional[DialogueService] = None,
        scenario_service: Optional[ScenarioService] = None
    ):
        """
        Args:
            llm_service: LLMService 인스턴스
            dialogue_service: DialogueService 인스턴스
            scenario_service: ScenarioService 인스턴스
        """
        self.llm_service = llm_service or LLMService()
        self.dialogue_service = dialogue_service or DialogueService()
        self.scenario_service = scenario_service or ScenarioService()

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

    def _get_world_context(self, state: Dict[str, Any]) -> str:
        """
        State에서 world_id를 추출하고 world_context 로드

        Args:
            state: 게임 상태

        Returns:
            World context 문자열
        """
        scenario_data = state.get("scenario_data") or state.get("scenario") or {}
        world_id = scenario_data.get("world_id")

        if not world_id:
            logger.warning("_get_world_context", "No world_id found in scenario_data")
            return ""

        world_context = self.scenario_service.get_world_context(world_id)
        logger.info("_get_world_context", f"Loaded world_context for {world_id}: {len(world_context)} chars")

        return world_context

    async def _generate_dialogues(
        self,
        ctx: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Beats 기반 대화 생성 (prompts.yaml 사용)
        """
        beats = ctx.get("beats", [])
        speaker_pool = ctx.get("speaker_pool", [])
        scenario_id = ctx.get("scenario_id", "unknown")

        if not beats:
            logger.warning("_generate_dialogues", "No beats provided")
            return []

        # 컨텍스트 정보 준비
        recent_dialogues = ctx.get("recent_dialogues", [])
        long_term_memories = ctx.get("long_term_memories", [])
        conversation_summary = state.get("conversation_summary", "")  # ✅ 대화 요약 추가
        user_input = state.get("user_input", "")
        current_turn = state.get("turn_count", 0)
        user_name = state.get("user_name", "츠구코")

        logger.info("_generate_dialogues", f"Post-processing will replace '{user_name}' with '{{user}}'")
        logger.info("_generate_dialogues", f"🔍 DEBUG: recent_dialogues count = {len(recent_dialogues)}")
        logger.info("_generate_dialogues", f"🔍 DEBUG: long_term_memories count = {len(long_term_memories)}")
        if recent_dialogues:
            logger.info("_generate_dialogues", f"🔍 DEBUG: First dialogue = {recent_dialogues[0]}")
            logger.info("_generate_dialogues", f"🔍 DEBUG: Last dialogue = {recent_dialogues[-1]}")

        # Beat goal 정리 ({{user}} → user_name 치환)
        beat_descriptions = []
        for beat in beats:
            if isinstance(beat, dict):
                desc = beat.get("goal") or beat.get("description") or beat.get("text") or str(beat)
                # ✅ {{user}} 치환 (프롬프트용)
                desc = desc.replace("{{user}}", user_name)
                beat_descriptions.append(desc)
            elif isinstance(beat, str):
                # ✅ {{user}} 치환 (프롬프트용)
                desc = beat.replace("{{user}}", user_name)
                beat_descriptions.append(desc)
        beats_description = "\n".join(beat_descriptions) if beat_descriptions else "일반 대화"

        # ✅ World context 로드
        world_context = self._get_world_context(state)

        logger.info("_generate_dialogues", f"Generating dialogues for {len(beats)} beats",
                    speaker_pool=speaker_pool, turn=current_turn,
                    world_context_length=len(world_context))

        try:
            # 대화 생성 프롬프트 (단일 모드)
            prompt = prompt_service.get_dialogue_generation_prompt(
                beats_description=beats_description,
                speaker_pool=speaker_pool,
                user_input=user_input,
                recent_dialogues=recent_dialogues,
                conversation_summary=conversation_summary,  # ✅ 대화 요약 추가
                world_context=world_context,
                user_name=user_name  # ✅ user_name 전달 (프롬프트에서 {{user}} 치환용)
            )

            # 🔍 DEBUG: 프롬프트에 중괄호 패턴이 있는지 확인
            if "{" in prompt and "}" in prompt:
                logger.warning("_generate_dialogues",
                              f"⚠️ Prompt contains braces! Checking for patterns...")
                import re
                brace_patterns = re.findall(r'\{[^}]+\}', prompt)
                if brace_patterns:
                    logger.warning("_generate_dialogues",
                                  f"⚠️ Found brace patterns in prompt: {brace_patterns[:5]}")

            # 🔍 DEBUG: 프롬프트 일부 출력
            logger.info("_generate_dialogues",
                       f"🔍 Prompt preview (first 500 chars): {prompt}")
            logger.info("_generate_dialogues",
                       f"🔍 Prompt preview (last 500 chars): {prompt}")

            dialogues_messages = await self.llm_service.generate_with_prompt(
                prompt=prompt,
                temperature=0.8,
                max_tokens=800
            )

            logger.info("_generate_dialogues",
                        f"LLM returned {len(dialogues_messages) if dialogues_messages else 0} messages")

        except Exception as e:
            logger.error("_generate_dialogues", f"LLM call failed: {e}", exc_info=True)
            return []

        if not dialogues_messages:
            logger.warning("_generate_dialogues", "LLM returned empty list")
            return []

        # Post-processing 동일
        dialogue_dicts = []
        for i, msg in enumerate(dialogues_messages):
            try:
                if hasattr(msg, 'speaker'):
                    dialogue_dict = {
                        "speaker": msg.speaker,
                        "text": msg.text,
                        "emotion": getattr(msg, 'emotion', 'neutral')
                    }
                elif isinstance(msg, dict):
                    dialogue_dict = {
                        "speaker": msg.get("speaker", "narr"),
                        "text": msg.get("text", ""),
                        "emotion": msg.get("emotion", "neutral")
                    }
                else:
                    logger.warning("_generate_dialogues",
                                   f"Unexpected message type at index {i}: {type(msg)}, value: {msg}")
                    continue

                # ✅ 따옴표 안의 대사만 추출 (speaker가 narr이 아닌 경우에만)
                if dialogue_dict["speaker"] != "narr":
                    import re
                    original_text_before_clean = dialogue_dict["text"]
                    # "대사"라고 ~다 패턴에서 대사만 추출
                    match = re.search(r'"([^"]+)"', dialogue_dict["text"])
                    if not match:
                        # 작은따옴표 시도
                        match = re.search(r"'([^']+)'", dialogue_dict["text"])

                    if match:
                        extracted_text = match.group(1)
                        if extracted_text != original_text_before_clean:
                            dialogue_dict["text"] = extracted_text
                            logger.info("_generate_dialogues",
                                        f"🧹 Extracted dialogue from quotes | {original_text_before_clean} → {extracted_text}")

                # ✅ 역치환: 사용자 이름 → {{user}} 플레이스홀더로 변환 (DB 저장용)
                if user_name in dialogue_dict["text"]:
                    original_text = dialogue_dict["text"]
                    dialogue_dict["text"] = dialogue_dict["text"].replace(user_name, "{{user}}")
                    logger.info("_generate_dialogues",
                                f"✏️ Replaced '{user_name}' → '{{{{user}}}}' | {original_text} → {dialogue_dict['text']}")

                if dialogue_dict["speaker"] == user_name:
                    logger.warning("_generate_dialogues",
                                   f"LLM generated player dialogue (speaker={user_name}), skipping")
                    continue

                dialogue_dicts.append(dialogue_dict)

            except Exception as e:
                logger.error("_generate_dialogues", f"Error converting message {i}: {e}", exc_info=True)
                continue

        logger.info("_generate_dialogues",
                    f"Generated {len(dialogue_dicts)} dialogues from {len(beats)} beats")

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
