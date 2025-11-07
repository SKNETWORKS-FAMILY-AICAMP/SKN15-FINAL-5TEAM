"""
Scenario State - 시나리오 데이터 및 씬 정보
시나리오 JSON 데이터와 현재 씬 상태를 관리
"""

from typing import TypedDict, Optional, List, Dict, Any


class ScenarioState(TypedDict):
    """
    시나리오 데이터 및 씬 정보
    - 시나리오 JSON
    - 현재 씬
    - 선택지
    - 파일 경로
    """

    # ============================================================
    # 시나리오 데이터 (JSON 기반)
    # ============================================================
    scenario_data: Optional[Dict[str, Any]]  # 로드된 전체 시나리오 JSON
    scenario: Optional[Dict[str, Any]]  # parent_agent용 scenario alias (호환성)

    # ============================================================
    # 씬 상태 (Scene)
    # ============================================================
    scene: Dict[str, Any]  # 씬 상태 (turn_count, current_scene, speaker_pool 등)

    # ============================================================
    # 선택지
    # ============================================================
    available_choices: List[Dict]  # [{"id": "A", "text": "..."}, ...]

    # ============================================================
    # 파일 경로 정보
    # ============================================================
    paths: Optional[Dict[str, Any]]  # 파일 경로 정보 (images, scenarios 등)
