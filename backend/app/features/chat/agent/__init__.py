"""
Chat Feature - Agent Layer (LangGraph)

Architecture:
- graph_state.py: TypedDict 상태 정의
- workflow.py: StateGraph 워크플로우
- nodes/: 에이전트 (상태 변환)
- guards/: 검증 및 라우팅
- handlers/: 스테이지별 대화 생성
"""

from .graph_state import GraphState, AgentDecision
from .workflow import ChatWorkflow, get_workflow

from .parent import ParentAgent
from .nodes.dialogue import DialogueAgent
from .nodes.router import RouterAgent
from .children import ChildrenAgent

from .guards.guardrail import GuardrailAgent
from .guards.should_route import should_route, check_safety

from .stage_handlers import (
    SceneStageHandler,
    MissionStageHandler,
    RouterStageHandler,
    FreeIntentStageHandler,
    OpenNarrativeStageHandler,
)

__all__ = [
    # State
    "GraphState",
    "AgentDecision",
    # Workflow
    "ChatWorkflow",
    "get_workflow",
    # Nodes
    "ParentAgent",
    "DialogueAgent",
    "RouterAgent",
    "ChildrenAgent",
    # Guards
    "GuardrailAgent",
    "should_route",
    "check_safety",
    # Stage Handlers
    "SceneStageHandler",
    "MissionStageHandler",
    "RouterStageHandler",
    "FreeIntentStageHandler",
    "OpenNarrativeStageHandler",
]
