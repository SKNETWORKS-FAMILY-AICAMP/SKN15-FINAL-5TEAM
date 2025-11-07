"""
Core 패키지 - 4-layer 아키텍처의 Core Layer

인터페이스, 예외, 설정, 공통 모델 정의
"""

from .models.state.graph_state import GraphState, AgentState, create_initial_graph_state

__all__ = [
    'GraphState',
    'AgentState',  # 하위 호환성
    'create_initial_graph_state'
]
