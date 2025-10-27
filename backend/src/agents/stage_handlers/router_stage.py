from __future__ import annotations

from typing import Any, Dict

from src.utils.logger import log
from src.tools.scene_tools import get_next_stage_tag
from src.config.constants import INTRO_STAGE_TAGS
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
        stage_tag = stage.get("tag") or stage.get("id") or "router"

        outcome_routes = stage.get("next_by_outcome") or stage.get("outcome_routes") or {}
        if outcome_routes:
            outcome_key_raw = state.get("_outcome")
            outcome_key = str(outcome_key_raw or "").upper()
            next_stage = (
                outcome_routes.get(outcome_key)
                or outcome_routes.get(outcome_key.lower())
                or stage.get("default_next")
                or default_route
            )
            if not next_stage and outcome_routes:
                # pick first route as fallback
                next_stage = next(iter(outcome_routes.values()), None)

            ctx = {
                "stage_tag": stage_tag,
                "stage_type": "router",
                "beats": [],
                "router": {
                    "mode": "outcome",
                    "outcome": outcome_key,
                    "fallback": next_stage,
                },
                "speaker_pool": stage.get("speaker_pool", []),
            }

            log(
                "router_stage",
                "Outcome routing resolved",
                outcome=outcome_key or "UNKNOWN",
                next_stage=next_stage,
            )
            return StageResult(children_ctx=ctx, stage_complete=True, next_stage=next_stage)

        next_stage = intent_mapping.get(intent)
        if not next_stage:
            next_stage = default_route

        # 일부 기본 intent에 대한 fallback 반응
        intro_stage_aliases = {tag.upper() for tag in INTRO_STAGE_TAGS}
        if intent == "on_topic_generic" and stage_tag.upper() in (intro_stage_aliases | {"ROUTE_CHOICE"}):
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
