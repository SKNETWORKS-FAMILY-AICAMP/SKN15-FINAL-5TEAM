"""Core 패키지 - 시스템의 심장 (상태와 워크플로우)"""

from .graph_state import GraphState, AgentState, create_initial_graph_state

__all__ = [
    'GraphState',
    'AgentState',  # 하위 호환성
    'create_initial_graph_state'
]
