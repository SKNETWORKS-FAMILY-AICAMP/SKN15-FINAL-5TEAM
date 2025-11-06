"""
Game State - 게임 진행 상태 및 로직
게임플레이와 관련된 모든 상태 정보를 관리
"""

from typing import TypedDict, Optional, List, Dict, Any


class GameState(TypedDict):
    """
    게임 진행 상태
    - 스테이지 진행
    - 호감도 시스템
    - 미션 상태
    - 시스템 플래그
    """

    # ============================================================
    # 스테이지 진행
    # ============================================================
    current_stage: Optional[str]  # 현재 스테이지 ID (intro, fork, recruit_mission 등)
    stage_history: List[str]  # 진행한 스테이지 기록
    stage_states: Dict[str, Dict[str, Any]]  # 스테이지별 상태 저장
    stage_turn: Optional[int]  # 현재 스테이지 내 턴 수

    # ============================================================
    # 호감도 시스템
    # ============================================================
    affinity_scores: Dict[str, int]  # 캐릭터별 호감도 {"inosuke": 70, "zenitsu": 50}

    # ============================================================
    # 미션 상태
    # ============================================================
    mission_result: Optional[str]  # 'success', 'failure', 'partial_success'
    is_persuasion_successful: Optional[bool]  # 설득 성공 여부

    # RECRUIT 미션 관련
    allies_recruited: Optional[List[str]]  # 설득 성공한 캐릭터 목록
    recruit_attempts: Optional[Dict[str, int]]  # 캐릭터별 설득 시도 횟수
    recruit_failures: Optional[List[str]]  # 설득 실패한 캐릭터 목록
    recruit_order: Optional[List[str]]  # 설득 시도 순서

    # ============================================================
    # 시스템 플래그
    # ============================================================
    system_flags: List[str]  # 시스템 플래그 ["rengoku_arrived", "mission_started"]
    event_flags: Optional[List[str]]  # 이벤트 플래그 (특정 이벤트 발생 시)

    # ============================================================
    # 엔딩
    # ============================================================
    final_ending: Optional[str]  # "hidden_ending", "normal_ending", "bad_ending" 등

    # ============================================================
    # 이미지 관리
    # ============================================================
    current_image: Optional[str]  # 현재 표시 중인 이미지 파일명
    image_transition_history: Optional[List[Dict[str, Any]]]  # 이미지 전환 이력
