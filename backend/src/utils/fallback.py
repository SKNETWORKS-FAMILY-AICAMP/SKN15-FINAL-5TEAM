from __future__ import annotations

import time
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import log
from .fallback_llm import generate_stage_fallback

_FALLBACK_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "scenarios"
    / "fallback_mission.json"
)


@lru_cache(maxsize=1)
def _load_fallback_spec() -> Dict[str, Any]:
    if not _FALLBACK_FILE.exists():
        log("fallback", f"Fallback file missing at {_FALLBACK_FILE}, using default data")
        return {
            "mission": {
                "default": [
                    {
                        "speaker": "tanjiro",
                        "text": "시간이 없습니다! 선택을 명확히 말해주세요.",
                    }
                ]
            }
        }

    try:
        with _FALLBACK_FILE.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:  # pragma: no cover - defensive
        log("fallback", f"Failed to load fallback spec: {exc}")
        return {
            "mission": {
                "default": [
                    {
                        "speaker": "narr",
                        "text": "긴급 상황입니다. 다시 한번 결정을 내려주세요.",
                    }
                ]
            }
        }


def _select_entries(stage_type: str, stage_tag: str) -> List[Dict[str, Any]]:
    data = _load_fallback_spec()
    stage_bucket = data.get(stage_type.lower())
    if isinstance(stage_bucket, dict):
        if stage_tag in stage_bucket and isinstance(stage_bucket[stage_tag], list):
            return stage_bucket[stage_tag]
        if "default" in stage_bucket and isinstance(stage_bucket["default"], list):
            return stage_bucket["default"]
    generic = data.get("default")
    if isinstance(generic, list):
        return generic
    return [
        {"speaker": "narr", "text": "긴급 상황입니다. 다시 한번 결정을 내려주세요."}
    ]


def trigger_fallback(
    state: Dict[str, Any],
    stage: Dict[str, Any],
    *,
    reason: str = "automatic",
    override_stage_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a fallback payload for the given stage.

    Args:
        state: Shared story state (unused but kept for consistency).
        stage: Stage definition that triggered the fallback.
        reason: Short label describing why fallback executed.
        override_stage_tag: When provided the fallback will log using this tag.

    Returns:
        A payload containing fallback dialogues and metadata.
    """
    stage_tag = override_stage_tag or stage.get("tag") or stage.get("id") or "unknown"
    stage_type = stage.get("type", "scene")
    atmosphere = (stage.get("atmosphere") or "").lower()
    temp_data = state.get("temp_data") or {}
    auto_resume = temp_data.get("auto_resume_active")

    if atmosphere == "urgent":
        llm_dialogue = generate_stage_fallback(
            state,
            stage,
            state.get("user_input", ""),
        )
        if llm_dialogue:
            entry = {
                "speaker": llm_dialogue.get("speaker", "narr"),
                "text": llm_dialogue.get("text", ""),
            }
            speaker_pool = stage.get("speaker_pool") or [entry["speaker"]]
            if auto_resume:
                log(
                    "fallback",
                    f"Urgent fallback (auto-resume) for {stage_tag}",
                    reason="llm_fallback_auto",
                    speaker=entry["speaker"],
                )
                return {
                    "stage_tag": stage_tag,
                    "stage_type": stage_type,
                    "reason": "llm_fallback",
                    "dialogues": [entry],
                    "speaker_pool": speaker_pool,
                    "atmosphere": stage.get("atmosphere"),
                }
            log(
                "fallback",
                f"Urgent fallback via LLM for {stage_tag}",
                reason="llm_fallback",
                speaker=entry["speaker"],
            )
            state["system_blocked"] = True
            state["blocked_until"] = time.time() + 600
            temp = state.setdefault("temp_data", {})
            temp["force_story_resume"] = True
            temp.pop("skip_parent_after_dialogue", None)
            state["off_topic_count"] = 0
            return {
                "stage_tag": stage_tag,
                "stage_type": stage_type,
                "reason": "llm_fallback",
                "dialogues": [entry],
                "speaker_pool": speaker_pool,
                "atmosphere": stage.get("atmosphere"),
            }

    entries = _select_entries(stage_type, stage_tag)
    speaker_pool = stage.get("speaker_pool") or [item.get("speaker", "narr") for item in entries]

    log("fallback", f"Triggered fallback for {stage_tag}", reason=reason, entries=len(entries))

    return {
        "stage_tag": stage_tag,
        "stage_type": stage_type,
        "reason": reason,
        "dialogues": entries,
        "speaker_pool": speaker_pool,
        "atmosphere": stage.get("atmosphere"),
    }


__all__ = ["trigger_fallback"]
