"""
로컬 JSON 기반 이미지 매핑 로더

DB에 데이터가 없을 때를 대비한 스테이지→배경 매핑 fallback.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


def _candidate_dirs() -> list[Path]:
    current = Path(__file__).resolve()
    repo_root = current.parents[4]
    return [
        repo_root / "backend" / "data" / "image_mappings",
        repo_root / "data" / "image_mappings",
    ]


def _candidate_names(scenario_id: str) -> list[str]:
    names = {scenario_id}
    if "-" in scenario_id:
        names.add(scenario_id.replace("-", "_"))
    if "_" in scenario_id:
        names.add(scenario_id.replace("_", "-"))
    return list(names)


@lru_cache(maxsize=16)
def _load_stage_map(scenario_id: str) -> Optional[Dict[str, Any]]:
    if not scenario_id:
        return None

    for name in _candidate_names(scenario_id):
        filename = f"{name}_stage_map.json"
        for base in _candidate_dirs():
            path = base / filename
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data
                except Exception:
                    continue
    return None


def get_stage_image_identifier(scenario_id: str, stage_id: str) -> Optional[str]:
    """
    로컬 스테이지 매핑에서 이미지 식별자를 조회.
    """
    mapping = _load_stage_map(scenario_id)
    if not mapping:
        return None

    stage_map = mapping.get("stage_map", {})
    entry = stage_map.get(stage_id) or mapping.get("default_background")
    if not entry:
        return None

    if isinstance(entry, str):
        return entry

    for key in ("frontend_id", "background_id", "id", "image_key"):
        value = entry.get(key)
        if value:
            return str(value)

    if entry.get("index") is not None:
        return str(entry["index"])

    if entry.get("image_url"):
        return entry["image_url"]

    return None
