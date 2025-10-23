"""
Scene Tools - 시나리오(Stage / Beats / Scene) 관리 유틸리티
------------------------------------------------------------
ParentAgent, ChildrenAgent 등에서 공용으로 사용되는 함수 집합.
- 시나리오 로드 및 스테이지 접근
- i18n (국제화) beats 해석
- 스테이지 타입, 화자 풀, 대사 비트 정리
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..agents.utils.logger import log


# ============================================================
# 🧱 기본 시나리오 로드 / 탐색
# ============================================================

def load_scenario(scenario_path: str | Path) -> Optional[Dict[str, Any]]:
    """JSON 파일 기반 시나리오 로드"""
    try:
        p = Path(scenario_path)
        if not p.exists():
            log("scene", f"❌ Scenario not found: {p}")
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        log("scene", f"✅ Loaded scenario file: {p.name}")
        return data
    except Exception as e:
        log("scene", f"⚠️ Failed to load scenario: {e}")
        return None


def get_stage(scenario: Dict[str, Any], stage_tag: str) -> Optional[Dict[str, Any]]:
    """시나리오 내부에서 특정 stage_tag에 해당하는 스테이지 정의 반환"""
    try:
        stages = scenario.get("stages", [])
        for s in stages:
            tag = s.get("tag") or s.get("stage_tag")
            if tag and tag.upper() == stage_tag.upper():
                return s
        return None
    except Exception as e:
        log("scene", f"⚠️ get_stage() failed: {e}", stage_tag=stage_tag)
        return None


def get_stage_type(stage: Dict[str, Any]) -> str:
    """스테이지 타입 추출 (scene / mission / router / free_intent 등)"""
    if not stage:
        return "scene"
    return (stage.get("type") or "scene").lower()


# ============================================================
# 🌐 i18n Beats 해석
# ============================================================

def resolve_i18n_beats(stage: Dict[str, Any], scenario: Dict[str, Any], locale: str = "ko") -> List[Dict[str, Any]]:
    """
    i18n 구조의 beats를 현재 locale 기준으로 해석
    예:
      "beats_i18n": {
        "ko": [{"speaker":"tanjiro","text":"..."}, ...],
        "en": [...]
      }
    """
    try:
        # 방어 코드: stage와 scenario가 dict인지 확인
        if not isinstance(stage, dict):
            log("scene", f"⚠️ resolve_i18n_beats() received non-dict stage: {type(stage)}")
            return []
        if not isinstance(scenario, dict):
            log("scene", f"⚠️ resolve_i18n_beats() received non-dict scenario: {type(scenario)}")
            return []

        if "beats" in stage and isinstance(stage["beats"], list):
            return stage["beats"]

        beats_i18n = stage.get("beats_i18n")
        if not beats_i18n:
            return []

        # beats_i18n가 문자열이면 scenario.i18n에서 참조 해석
        if isinstance(beats_i18n, str):
            i18n_root = scenario.get("i18n") or {}
            candidates = []
            locale_lower = (locale or "").lower()
            if locale_lower:
                candidates.append(locale_lower)
                if "-" in locale_lower:
                    candidates.append(locale_lower.split("-")[0])
            if "ko" not in candidates:
                candidates.append("ko")
            candidates.append("default")

            for loc in candidates:
                loc_bucket = i18n_root.get(loc)
                if isinstance(loc_bucket, dict):
                    data = loc_bucket.get(beats_i18n)
                    if isinstance(data, list):
                        return data
            log("scene", f"⚠️ Missing beats_i18n key '{beats_i18n}' for stage {stage.get('tag')}")
            return []

        # 딕셔너리 형태일 때 locale 기반 선택
        if isinstance(beats_i18n, dict):
            locale_keys: List[str] = []
            if isinstance(locale, str) and locale:
                locale_lower = locale.lower()
                locale_keys.append(locale_lower)
                if "-" in locale_lower:
                    locale_keys.append(locale_lower.split("-")[0])
            if "ko" not in locale_keys:
                locale_keys.append("ko")
            locale_keys.append("default")

            for key in locale_keys:
                data = beats_i18n.get(key)
                if isinstance(data, list):
                    return data
            log("scene", f"⚠️ Invalid i18n beats format at {stage.get('tag')}")
            return []

        # 리스트 등 다른 형태면 그대로 반환 시도
        if isinstance(beats_i18n, list):
            return beats_i18n

        log("scene", f"⚠️ Unsupported beats_i18n type {type(beats_i18n)} at {stage.get('tag')}")
        return []
    except Exception as e:
        log("scene", f"⚠️ resolve_i18n_beats() failed: {e}")
        return []


# ============================================================
# 🧩 스테이지 / 화자 / 시나리오 관리
# ============================================================

def get_speaker_pool(stage: Dict[str, Any], scenario: Dict[str, Any]) -> List[str]:
    """stage 또는 scenario 기준 speaker_pool 확보"""
    try:
        if "speaker_pool" in stage:
            return stage["speaker_pool"]
        return scenario.get("default_speakers", [])
    except Exception:
        return []


def resolve_scenario(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    현재 state에서 시나리오 데이터를 안전하게 추출.
    - state["scenario"] → 우선 사용
    - state["scenario_data"] → 백업 사용
    """
    try:
        if "scenario" in state and state["scenario"]:
            return state["scenario"]
        if "scenario_data" in state and state["scenario_data"]:
            return state["scenario_data"]
        return None
    except Exception:
        return None


def extract_stage_tags(scenario: Dict[str, Any]) -> List[str]:
    """모든 스테이지 tag 목록 반환"""
    try:
        return [s.get("tag", "").upper() for s in scenario.get("stages", []) if s.get("tag")]
    except Exception:
        return []


def get_default_stage(scenario: Dict[str, Any]) -> str:
    """시나리오의 기본 시작 스테이지 반환"""
    return scenario.get("default_stage", "INTRO")


# ============================================================
# 🎭 로그 / 디버깅 헬퍼
# ============================================================

def preview_stage(stage: Dict[str, Any], limit: int = 3):
    """해당 stage의 beats 미리보기"""
    if not stage:
        log("scene", "⚠️ No stage to preview")
        return
    beats = stage.get("beats") or []
    log("scene", f"🎬 Preview stage={stage.get('tag')} ({len(beats)} beats)")
    for i, b in enumerate(beats[:limit]):
        t = b.get("text", "")[:60]
        log("scene", f"  {i+1}. {b.get('speaker', '?')}: {t}")


# ============================================================
# 🧩 시나리오 JSON 디버깅용
# ============================================================

def validate_scenario_structure(scenario: Dict[str, Any]) -> bool:
    """기본 시나리오 구조 유효성 검사"""
    try:
        if "stages" not in scenario or not isinstance(scenario["stages"], list):
            log("scene", "❌ Invalid scenario: missing 'stages'")
            return False
        for s in scenario["stages"]:
            if "tag" not in s:
                log("scene", f"⚠️ Stage missing tag: {s}")
        return True
    except Exception as e:
        log("scene", f"⚠️ validate_scenario_structure() failed: {e}")
        return False


# ============================================================
# 📦 Export
# ============================================================
__all__ = [
    "load_scenario",
    "get_stage",
    "get_stage_type",
    "resolve_i18n_beats",
    "get_speaker_pool",
    "resolve_scenario",
    "extract_stage_tags",
    "get_default_stage",
    "preview_stage",
    "validate_scenario_structure",
]
