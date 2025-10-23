from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class StageResult:
    children_ctx: Dict[str, Any]
    stage_complete: bool = False
    next_stage: Optional[str] = None
    fallback_payload: Optional[Dict[str, Any]] = None


from .mission_stage import MissionHandler
from .scene_stage import SceneHandler
from .free_intent_stage import FreeIntentHandler
from .router_stage import RouterStageHandler

__all__ = [
    "StageResult",
    "MissionHandler",
    "SceneHandler",
    "FreeIntentHandler",
    "RouterStageHandler",
]
