"""
Chat Feature - Agent Layer
에이전트 파이프라인 (Parent, Guardrail, Router, Children, Dialogue, Stages)

Architecture:
- ParentAgent: 스테이지 라우팅 및 파이프라인 조율
- ChildrenAgent: 대화 생성
- DialogueAgent: 대화 검증 및 수정
- StageHandlers: 스테이지별 처리 (Mission, Scene, Router, FreeIntent, OpenNarrative)
"""

from .parent import ParentAgent, get_parent_agent, run_parent_agent
from .children import ChildrenAgent, get_children_agent, run_children_agent
from .dialogue import DialogueAgent

from .stage_handlers import (
    StageResult,
    MissionStageHandler,
    SceneStageHandler,
    RouterStageHandler,
    FreeIntentStageHandler,
    OpenNarrativeStageHandler,
)

__all__ = [
    # Parent Agent
    "ParentAgent",
    "get_parent_agent",
    "run_parent_agent",
    # Children Agent
    "ChildrenAgent",
    "get_children_agent",
    "run_children_agent",
    # Dialogue Agent
    "DialogueAgent",
    # Stage Handlers
    "StageResult",
    "MissionStageHandler",
    "SceneStageHandler",
    "RouterStageHandler",
    "FreeIntentStageHandler",
    "OpenNarrativeStageHandler",
]
