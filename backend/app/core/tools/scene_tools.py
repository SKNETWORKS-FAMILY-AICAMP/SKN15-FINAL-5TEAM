"""
SceneTools - 시나리오 및 스테이지 관리 도구
tm_work의 scene_tools를 현재 아키텍처에 맞게 간소화
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


def load_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    """
    시나리오 JSON 로드

    Args:
        scenario_id: 시나리오 ID (예: "mugen-train")

    Returns:
        시나리오 데이터 또는 None
    """
    # data/scenarios/ 디렉토리에서 로드
    scenarios_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "scenarios"

    # 파일명 변환 (mugen-train -> mugen_train.json)
    scenario_file = scenarios_dir / f"{scenario_id.replace('-', '_')}.json"

    if not scenario_file.exists():
        print(f"⚠️ Scenario file not found: {scenario_file}")
        return None

    try:
        with open(scenario_file, 'r', encoding='utf-8') as f:
            scenario = json.load(f)
        print(f"✅ Loaded scenario: {scenario_id}")
        return scenario
    except Exception as e:
        print(f"❌ Failed to load scenario {scenario_id}: {e}")
        return None


def get_stage(scenario: Dict[str, Any], stage_tag: str) -> Optional[Dict[str, Any]]:
    """
    시나리오에서 특정 스테이지 조회

    Args:
        scenario: 시나리오 데이터
        stage_tag: 스테이지 태그 (예: "TRAIN_INTRO")

    Returns:
        스테이지 정의 또는 None
    """
    if not scenario:
        return None

    stages = scenario.get("stages", [])

    for stage in stages:
        if stage.get("id", "").upper() == stage_tag.upper():
            return stage

    print(f"⚠️ Stage '{stage_tag}' not found in scenario")
    return None


def resolve_i18n_beats(stage: Dict[str, Any], scenario: Dict[str, Any], locale: str = "ko") -> Optional[List[Dict[str, Any]]]:
    """
    스테이지의 i18n beats 해석

    Args:
        stage: 스테이지 정의
        scenario: 시나리오 데이터
        locale: 언어 코드 (기본값: "ko")

    Returns:
        beats 리스트 또는 None
    """
    beats_i18n = stage.get("beats_i18n")
    if not beats_i18n:
        return None

    i18n_data = scenario.get("i18n", {}).get(locale, {})

    if isinstance(beats_i18n, str):
        # "beats_train_intro" 같은 키
        beats = i18n_data.get(beats_i18n)
        if beats:
            return beats

    return None


def get_metadata(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    시나리오 메타데이터 조회

    Args:
        scenario: 시나리오 데이터

    Returns:
        메타데이터 딕셔너리
    """
    if not scenario:
        return {}

    return scenario.get("metadata", {})


def get_character_pool(scenario: Dict[str, Any]) -> List[str]:
    """
    시나리오의 캐릭터 풀 조회

    Args:
        scenario: 시나리오 데이터

    Returns:
        캐릭터 ID 리스트
    """
    if not scenario:
        return []

    character_refs = scenario.get("character_refs", {})
    return list(character_refs.keys())


def get_stage_type(stage: Dict[str, Any]) -> str:
    """
    스테이지 타입 조회

    Args:
        stage: 스테이지 정의

    Returns:
        스테이지 타입 ("scene", "mission", "router", "free_intent", "open_narrative")
    """
    if not stage:
        return "scene"

    return stage.get("type", "scene").lower()


def get_next_stage_from_mapping(
    stage: Dict[str, Any],
    intent: Optional[str] = None,
    outcome: Optional[str] = None
) -> Optional[str]:
    """
    intent_mapping 또는 next_by_outcome에서 다음 스테이지 조회

    Args:
        stage: 스테이지 정의
        intent: 사용자 의도 (free_intent stage용)
        outcome: 결과 (router stage용)

    Returns:
        다음 스테이지 ID 또는 None
    """
    if not stage:
        return None

    # intent_mapping 우선 확인 (free_intent stage)
    if intent:
        intent_mapping = stage.get("intent_mapping", {})
        next_stage = intent_mapping.get(intent)
        if next_stage:
            return next_stage

    # next_by_outcome 확인 (router stage)
    if outcome:
        next_by_outcome = stage.get("next_by_outcome", {})
        next_stage = next_by_outcome.get(outcome)
        if next_stage:
            return next_stage

    # 기본 next_stage
    return stage.get("next_stage")


def validate_scenario_structure(scenario: Dict[str, Any]) -> bool:
    """
    시나리오 구조 검증

    Args:
        scenario: 시나리오 데이터

    Returns:
        유효하면 True
    """
    if not scenario:
        return False

    required_keys = ["scenario_id", "title", "stages"]
    for key in required_keys:
        if key not in scenario:
            print(f"❌ Missing required key: {key}")
            return False

    stages = scenario.get("stages", [])
    if not isinstance(stages, list) or len(stages) == 0:
        print("❌ Invalid or empty stages array")
        return False

    return True
