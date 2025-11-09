"""
Children Agent - 대화 생성 에이전트

Features:
- ParentAgent가 전달한 children_ctx 기반 대화 생성
- LLMService를 사용한 beat 기반 대화 생성
- 대화 품질 관리
"""
from typing import Dict, Any, List, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import LLMService, DialogueService

logger = get_parent_logger("ChildrenAgent")


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

        # 포맷팅
        formatted_dialogues = self.dialogue_service.format_dialogues(
            dialogues,
            state
        )

        # 결과 저장
        state["agent_responses"] = formatted_dialogues
        state["has_more_dialogues"] = False

        logger.info("run", "Dialogues generated",
                   count=len(formatted_dialogues))

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
        Beats 기반 대화 생성

        Args:
            ctx: children_ctx
            state: 게임 상태

        Returns:
            생성된 대화 리스트
        """
        beats = ctx.get("beats", [])
        speaker_pool = ctx.get("speaker_pool", [])
        scenario_id = ctx.get("scenario_id", "unknown")
        character_refs = ctx.get("character_refs", {})

        if not beats:
            logger.warning("_generate_dialogues", "No beats provided")
            return []

        dialogues = []

        for beat in beats:
            if isinstance(beat, dict):
                # Beat dict 형식
                goal = beat.get("goal", "")
                speaker_hint = beat.get("speaker_hint", speaker_pool)
                fx = beat.get("fx")

                if not goal:
                    continue

                # LLM을 통한 대화 생성
                dialogue = await self.llm_service.generate_beat_dialogue(
                    goal=goal,
                    speaker_pool=speaker_hint if isinstance(speaker_hint, list) else [speaker_hint],
                    state=state,
                    character_refs=character_refs
                )

                if dialogue:
                    if fx:
                        dialogue["fx"] = fx
                    dialogues.append(dialogue)

            elif isinstance(beat, str):
                # 단순 문자열 beat
                dialogues.append({
                    "speaker": "narr",
                    "text": beat,
                    "goal": beat
                })

        logger.debug("_generate_dialogues", f"Generated {len(dialogues)} dialogues from {len(beats)} beats")

        return dialogues


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
