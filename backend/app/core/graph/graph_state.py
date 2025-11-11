"""
GraphState - LangGraph 상태 정의
현재 4-layer 아키텍처에 맞게 간소화된 버전
"""
from typing import TypedDict, Dict, Any, List, Optional


class GraphState(TypedDict, total=False):
    """
    LangGraph 워크플로우 상태

    tm_work의 GraphState를 현재 아키텍처에 맞게 간소화
    """
    # 세션 정보
    session_id: str
    user_id: str
    scenario_id: str
    user_name: Optional[str]

    # 사용자 입력
    user_input: str

    # 시나리오 상태
    current_stage: Optional[str]
    stage_tag: Optional[str]
    turn_count: int
    stage_turn: int

    # 시나리오 데이터
    scenario: Optional[Dict[str, Any]]
    scenario_data: Optional[Dict[str, Any]]

    # 에이전트 통신
    agent_inputs: Dict[str, Any]  # 에이전트 간 입력
    agent_responses: List[Dict[str, Any]]  # 생성된 대화

    # 워크플로우 제어
    next_node: Optional[str]  # 다음 노드 (router, parent_agent, etc.)

    # 컨텍스트
    children_ctx: Optional[Dict[str, Any]]  # Children Agent 컨텍스트
    temp_data: Dict[str, Any]  # 임시 데이터

    # 게임 상태
    game: Dict[str, Any]  # 게임 플래그, 변수
    scene: Dict[str, Any]  # Scene 상태

    # 출력
    output: Dict[str, Any]  # 최종 출력 데이터

    # 요약 및 메모리
    conversation_summary: Optional[str]
    summary_turn_count: int

    # 친밀도
    affinity_scores: Dict[str, int]

    # 엔딩
    final_ending: Optional[str]
    is_active: bool

    # 라우팅 결과
    routing_result: Optional[Dict[str, Any]]
    user_intent: Optional[str]

    # 미션 (stage type: mission)
    mission_target: Optional[str]

    # 다음 스테이지
    next_stage: Optional[str]
    has_more_dialogues: bool
