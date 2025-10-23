from __future__ import annotations

from typing import Any, Dict

from ..utils.logger import log
from ..scene_tools import get_next_stage_tag
from . import StageResult


class RouterStageHandler:
    """A lightweight handler that jumps to the next stage based on routing metadata."""

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        routing = state.get("routing_result") or {}
        intent = str(routing.get("intent") or routing.get("classification") or "").lower()

        # ✅ ParentAgent에서 fallback 판단에 쓰일 classification 기록
        state["classification"] = intent

        intent_mapping = stage.get("intent_mapping") or stage.get("routes") or {}
        default_route = (
            stage.get("default_next")
            or stage.get("default")
            or stage.get("next")
            or stage.get("next_stage")
            or get_next_stage_tag(stage)
        )
        next_stage = intent_mapping.get(intent)
        if not next_stage:
            next_stage = default_route

        stage_tag = stage.get("tag") or stage.get("id") or "router"

        # 일부 기본 intent에 대한 fallback 반응
        if intent == "on_topic_generic" and stage_tag in ("INTRO", "ROUTE_CHOICE"):
            next_stage = next_stage or default_route
            log("codex_fix", f"Intent fallback triggered: {intent}", stage=stage_tag)
            return StageResult(
                children_ctx={
                    "stage_tag": stage_tag,
                    "stage_type": "router",
                    "dialogues": [
                        {"speaker": "tanjiro", "text": "좋아요, 이어서 진행해요!"}
                    ],
                    "speaker_pool": ["tanjiro"],
                },
                stage_complete=True,
                next_stage=next_stage,
            )

        ctx = {
            "stage_tag": stage_tag,
            "stage_type": "router",
            "beats": [],
            "router": {
                "intent": intent,
                "routes": intent_mapping,
            },
        }

        if next_stage:
            log("router_stage", "Routing intent matched", intent=intent, next_stage=next_stage)
        else:
            log("router_stage", "Router stage could not resolve next stage", intent=intent)

        return StageResult(children_ctx=ctx, stage_complete=True, next_stage=next_stage)
