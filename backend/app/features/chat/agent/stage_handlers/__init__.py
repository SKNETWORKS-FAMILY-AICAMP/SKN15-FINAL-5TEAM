"""
Stage Handlers - 스테이지별 처리 핸들러

각 스테이지 타입에 맞는 핸들러를 제공합니다.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class StageResult:
    """
    스테이지 처리 결과

    Attributes:
        children_ctx: ChildrenAgent에 전달할 컨텍스트
        stage_complete: 스테이지 완료 여부
        next_stage: 다음 스테이지 태그 (완료 시)
        fallback_payload: Fallback 데이터 (선택)
        state_updates: state에 병합할 업데이트 (선택)
    """
    children_ctx: Dict[str, Any]
    stage_complete: bool = False
    next_stage: Optional[str] = None
    fallback_payload: Optional[Dict[str, Any]] = None
    state_updates: Optional[Dict[str, Any]] = None


from .mission_stage import MissionStageHandler
from .free_intent_stage import FreeIntentStageHandler
from .router_stage import RouterStageHandler
from .scene_stage import SceneStageHandler
from .open_narrative_stage import OpenNarrativeStageHandler


__all__ = [
    "StageResult",
    "MissionStageHandler",
    "FreeIntentStageHandler",
    "RouterStageHandler",
    "SceneStageHandler",
    "OpenNarrativeStageHandler",
]
