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
    """
    Return possible directories that may contain image mapping files.

    지원 환경:
    1. Monorepo (호스트) - <repo>/backend 및 <repo>/data
    2. Docker 컨테이너 - /app, /app/backend
    """
    current = Path(__file__).resolve()
    parents = list(current.parents)

    potential_roots = []
    for idx in range(min(len(parents), 5)):
        potential_roots.append(parents[idx])

    # Docker 컨테이너 기본 경로 추가 (/app)
    potential_roots.append(Path("/app"))

    candidate_dirs = []
    seen = set()

    for root in potential_roots:
        for sub in ("data/image_mappings", "backend/data/image_mappings"):
            candidate = (root / sub).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            candidate_dirs.append(candidate)

    return candidate_dirs


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
    
    # stage_id로 이미지 ID를 찾고, 없으면 기본 배경 ID를 사용
    image_id = stage_map.get(stage_id) or mapping.get("default_background_id")
    
    return image_id
