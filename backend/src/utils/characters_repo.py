'''캐릭터 JSON 스캔 + 캐시
API: list_characters(), get_character(id), default_affinity_of(id), flags(affinity_visible/applicable), build_character_rulebook(char)
'''

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAR_DIR = os.path.join(BASE_DIR, "data", "characters")


@lru_cache(maxsize=1)
def _scan() -> Dict[str, Dict[str, Any]]:
    data: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(CHAR_DIR):
        return data
    for name in os.listdir(CHAR_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CHAR_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            cid = (obj.get("id") or os.path.splitext(name)[0]).strip().lower()
            data[cid] = obj
        except Exception:
            continue
    return data


def list_characters() -> List[str]:
    return list(_scan().keys())


def get_character(char_id: str) -> Dict[str, Any] | None:
    return _scan().get(str(char_id).strip().lower())


def default_affinity_of(char_id: str) -> int:
    obj = get_character(char_id) or {}
    if "default_affinity" in obj:
        try:
            return int(obj.get("default_affinity") or 0)
        except Exception:
            return 0
    # legacy fallback
    prof = obj.get("profile") or {}
    try:
        return int(prof.get("default_affinity") or 0)
    except Exception:
        return 0


# def affinity_visible(char_id: str) -> bool:
#     obj = get_character(char_id) or {}
#     return bool(obj.get("affinity_visible", True))

def affinity_visible(char_id: str, base_dir: str = "data/characters") -> bool:
    fp = os.path.join(base_dir, f"{char_id}.json")
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        node = (data.get("characters") or {}).get(char_id) or data
        # 기본값 True (명시 안 되어 있으면 보이게)
        return bool(node.get("affinity_visible", True))
    except Exception:
        return True


def affinity_applicable(char_id: str) -> bool:
    obj = get_character(char_id) or {}
    return bool(obj.get("affinity_applicable", True))


def build_character_rulebook(char_id: str) -> Dict[str, Any]:
    obj = get_character(char_id) or {}
    rules = obj.get("intent_rules") or {}
    return {
        "weights": rules.get("weights", {}),
        "patterns": rules.get("patterns", {}),
        "sensitivities": rules.get("sensitivities", {}),
        "overrides": rules.get("overrides", {}),
        "priorities": rules.get("priorities", {}),
    }


def character_names_aliases() -> List[Tuple[str, List[str]]]:
    """Return list of (char_id, aliases) with primary name included.
    Aliases read from character JSON: name/name_ko and optional aliases.
    Cached via _scan.
    """
    out: List[Tuple[str, List[str]]] = []
    for cid, obj in _scan().items():
        names: List[str] = []
        # common fields across our data
        for k in ("name", "name_ko"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                names.append(v)
        # nested characters.<id>.name shape
        if "characters" in obj and isinstance(obj["characters"], dict):
            inner = obj["characters"].get(cid) or {}
            for k in ("name", "name_ko"):
                v = inner.get(k)
                if isinstance(v, str) and v:
                    names.append(v)
            # optional aliases list
            als = inner.get("aliases") or []
            if isinstance(als, list):
                for a in als:
                    if isinstance(a, str) and a:
                        names.append(a)
        # dedup and normalize
        uniq = []
        for n in names:
            n = n.strip()
            if n and n not in uniq:
                uniq.append(n)
        # ensure id also considered (romanized id)
        if cid not in uniq:
            uniq.append(cid)
        out.append((cid, uniq))
    return out
