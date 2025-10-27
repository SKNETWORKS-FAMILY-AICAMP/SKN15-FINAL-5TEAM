from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.utils.logger import log


def _scenario_search_paths(scenario_id: str) -> List[Path]:
    base = Path(__file__).resolve().parents[3] / "data" / "scenarios"
    candidates = [
        base / f"{scenario_id}.json",
        base / f"{scenario_id.lower()}.json",
        base / f"{scenario_id}.JSON",
    ]
    return candidates


@lru_cache(maxsize=8)
def _load_scenario_file(scenario_id: str) -> Optional[Dict[str, Any]]:
    for path in _scenario_search_paths(scenario_id):
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
    log("scenario", f"Scenario file for {scenario_id} not found")
    return None


def resolve_scenario(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scenario = state.get("scenario_data")
    if isinstance(scenario, dict):
        return scenario
    scenario_id = state.get("scenario_id") or state.get("scenario", {}).get("id")
    if not scenario_id:
        log("scenario", "Missing scenario_id in state")
        return None
    loaded = _load_scenario_file(str(scenario_id))
    if loaded is not None:
        state["scenario_data"] = loaded
    return loaded


def list_stages(scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    stages = scenario.get("stages") or []
    if isinstance(stages, dict):
        return [value for value in stages.values() if isinstance(value, dict)]
    if isinstance(stages, list):
        return [stage for stage in stages if isinstance(stage, dict)]
    return []


def get_stage(scenario: Dict[str, Any], stage_tag: str) -> Optional[Dict[str, Any]]:
    target = stage_tag.lower()
    for stage in list_stages(scenario):
        for key in ("tag", "id", "name"):
            value = stage.get(key)
            if isinstance(value, str) and value.lower() == target:
                return stage
    return None


def get_stage_type(stage: Dict[str, Any]) -> str:
    return str(stage.get("type", "scene")).lower()


def get_stage_atmosphere(stage: Dict[str, Any]) -> Optional[str]:
    atmosphere = stage.get("atmosphere")
    return str(atmosphere) if atmosphere else None


def _normalize_beats(items: Iterable[Any]) -> List[Dict[str, Any]]:
    beats: List[Dict[str, Any]] = []
    for item in list(items):
        if isinstance(item, dict):
            beats.append({key: value for key, value in item.items()})
        else:
            beats.append({"text": str(item)})
    return beats


def _resolve_locale_bucket(i18n: Dict[str, Any], locale: str) -> Optional[Dict[str, Any]]:
    if not i18n:
        return None
    candidates: List[str] = []
    locale_norm = (locale or "").lower()
    if locale_norm:
        candidates.append(locale_norm)
    if "-" in locale_norm:
        candidates.append(locale_norm.split("-")[0])
    if locale_norm not in ("ko", "kr"):
        candidates.extend(["ko", "kr"])
    candidates.append("default")

    for cand in candidates:
        data = i18n.get(cand)
        if isinstance(data, dict):
            return data
    return None


def get_i18n_entries(
    scenario: Dict[str, Any], key: Optional[str], locale: str = "ko"
) -> List[Dict[str, Any]]:
    if not key:
        return []
    root = scenario.get("i18n") or {}
    locale_bucket = _resolve_locale_bucket(root, locale) or {}
    data = locale_bucket.get(key)
    if isinstance(data, list):
        return _normalize_beats(data)
    return []

# beats_i18n 키를 읽어서, 실제 텍스트를 i18n["ko"][beats_i18n]에서 찾아 반환
def resolve_i18n_beats(stage: Dict[str, Any], scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    key = stage.get("beats_i18n")
    if not key:
        return []
    lang_data = (scenario.get("i18n") or {}).get("ko", {})
    return lang_data.get(key, [])


def get_stage_beats(
    stage: Dict[str, Any], scenario: Dict[str, Any], locale: str = "ko"
) -> List[Dict[str, Any]]:
    if isinstance(stage.get("beats"), list):
        return _normalize_beats(stage["beats"])
    beats_i18n = stage.get("beats_i18n")
    if isinstance(beats_i18n, dict):
        if locale in beats_i18n:
            return _normalize_beats(beats_i18n[locale])
        if "default" in beats_i18n:
            return _normalize_beats(beats_i18n["default"])
        for fallback_locale in ("ko", "kr", "default"):
            if fallback_locale in beats_i18n:
                return _normalize_beats(beats_i18n[fallback_locale])
    if isinstance(beats_i18n, str):
        return get_i18n_entries(scenario, beats_i18n, locale=locale)
    intro_key = stage.get("intro_i18n") or stage.get("scene_i18n")
    return get_i18n_entries(scenario, intro_key, locale=locale)


def get_speaker_pool(stage: Dict[str, Any], fallback: Iterable[str]) -> List[str]:
    pool = stage.get("speaker_pool") or stage.get("speakerPool")
    if isinstance(pool, list) and pool:
        return [str(item) for item in pool]
    return [str(item) for item in fallback]


def get_next_stage_tag(stage: Dict[str, Any]) -> Optional[str]:
    for key in ("next_stage", "next", "default_next", "default"):
        value = stage.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


__all__ = [
    "resolve_scenario",
    "list_stages",
    "get_stage",
    "get_stage_type",
    "get_stage_atmosphere",
    "get_stage_beats",
    "get_speaker_pool",
    "get_next_stage_tag",
    "get_i18n_entries",
]
