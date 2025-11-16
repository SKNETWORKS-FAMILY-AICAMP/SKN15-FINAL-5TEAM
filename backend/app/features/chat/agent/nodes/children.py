"""
Children Agent Node - 대화 생성 (LangGraph 노드)

역할:
- 5단계: agent/children.py를 호출하여 실제 LLM 대화 생성
- children_ctx 기반으로 대화 생성
"""
from typing import Dict, Any
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger

logger = get_service_logger("ChildrenNode")


class ChildrenAgent:
    """Children Agent Node - 대화 생성 (5단계)"""

    def __init__(self):
        """초기화 - agent/children.py는 lazy 로드"""
        self._legacy_children = None

    @property
    def legacy_children(self):
        """Lazy initialization of ChildrenAgent"""
        if self._legacy_children is None:
            from ..children import ChildrenAgent as LegacyChildren
            self._legacy_children = LegacyChildren()
            logger.info("legacy_children", "ChildrenAgent lazily initialized")
        return self._legacy_children

    async def run(self, state: GraphState) -> GraphState:
        """
        Children Agent 실행 (5단계)

        children_ctx를 기반으로 agent/children.py를 호출하여 LLM 대화 생성
        """
        logger.info("run", "Children node started")

        # children_ctx 확인
        children_ctx = state.get("children_ctx", {})

        if not children_ctx:
            logger.warning("run", "No children_ctx found")
            state["agent_responses"] = []
            return state

        beats = children_ctx.get("beats", [])
        logger.info("run", "Generating dialogues", beats_count=len(beats))

        try:
            # Dict[str, Any]로 변환 (agent/children.py는 일반 dict 사용)
            dict_state = dict(state)
            dict_state["children_ctx"] = children_ctx

            # agent/children.py 호출 - 실제 LLM 대화 생성
            updated_state = await self.legacy_children.run(dict_state)

            # agent_responses 가져오기
            agent_responses = updated_state.get("agent_responses", [])

            logger.info("run", "Dialogues generated", count=len(agent_responses))

            # GraphState 업데이트
            state["agent_responses"] = agent_responses

            # 기타 업데이트된 상태 반영
            for key in ["has_more_dialogues"]:
                if key in updated_state:
                    state[key] = updated_state[key]

        except Exception as e:
            logger.error("run", f"Dialogue generation failed: {e}", exc_info=True)
            state["agent_responses"] = []
            state["error"] = f"Dialogue generation failed: {str(e)}"

        logger.info("run", "Children node completed")
        return state


# 싱글톤 인스턴스
_children_agent = None


def get_children_agent() -> ChildrenAgent:
    """Children Agent 싱글톤"""
    global _children_agent
    if _children_agent is None:
        _children_agent = ChildrenAgent()
    return _children_agent


def run_children_agent(state: GraphState) -> GraphState:
    """
    Children Agent 실행 함수

    Args:
        state: GraphState

    Returns:
        업데이트된 GraphState
    """
    agent = get_children_agent()
    return agent.run(state)
