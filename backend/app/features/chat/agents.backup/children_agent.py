"""
Children Agent - 대화 컨텍스트 구성 에이전트
"""
from typing import Dict, Any, List
from app.core.graph.graph_state import GraphState


class ChildrenAgent:
    """
    Children Agent

    역할:
    - Parent Agent로부터 받은 컨텍스트 확장
    - Dialogue Agent로 전달할 프롬프트 구성
    """

    def run(self, state: GraphState) -> GraphState:
        """
        Children Agent 실행

        Args:
            state: GraphState

        Returns:
            업데이트된 GraphState
        """
        # Agent responses 초기화 (새로운 대화 생성 준비)
        state["agent_responses"] = []

        # Children context 가져오기
        children_ctx = state.get("children_ctx", {})

        if not children_ctx:
            print("⚠️ No children_ctx found")
            state["next_node"] = "END"
            return state

        # Beats 확인
        beats = children_ctx.get("beats", [])
        stage_turn = state.get("stage_turn", 0)

        # 현재 턴의 beat 가져오기 (있다면)
        current_beat = None
        if beats and stage_turn < len(beats):
            current_beat = beats[stage_turn]

        # Dialogue Agent로 전달할 입력 구성
        dialogue_input = {
            "children_ctx": children_ctx,
            "current_beat": current_beat,
            "user_input": state.get("user_input", ""),
            "user_name": state.get("user_name", "사용자"),
            "speaker_pool": children_ctx.get("speaker_pool", []),
            "stage_type": children_ctx.get("stage_type", "scene"),
        }

        # agent_inputs에 저장
        if "agent_inputs" not in state:
            state["agent_inputs"] = {}
        state["agent_inputs"]["dialogue"] = dialogue_input

        # 다음 노드: Dialogue Agent
        state["next_node"] = "dialogue_agent"

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
