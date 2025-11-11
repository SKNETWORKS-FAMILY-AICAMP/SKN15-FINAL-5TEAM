"""
Graph State 정의
LangGraph 에이전트 간 공유되는 상태

TypedDict를 사용하여 상태 스키마 정의
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict as TypedDictExtended
import operator


class GraphState(TypedDict):
    """
    LangGraph 상태 정의

    에이전트 간 공유되는 전역 상태
    """
    # 세션 정보
    session_id: str
    user_id: str
    scenario_id: str

    # 사용자 입력
    user_input: str
    user_name: str

    # 현재 스테이지 정보
    current_stage: str
    stage_type: str  # scene, mission, router, free_intent, open_narrative
    turn_count: int
    stage_turn: int

    # 시나리오 데이터
    scenario: Optional[Dict[str, Any]]
    stage_config: Optional[Dict[str, Any]]

    # 대화 히스토리 (누적)
    messages: Annotated[List[Dict[str, Any]], operator.add]

    # 컨텍스트
    conversation_summary: Optional[str]
    user_memories: List[Dict[str, Any]]
    character_affinity: Dict[str, float]

    # 엔티티 추출 결과
    entities: List[Dict[str, Any]]
    entity_mentions: List[Dict[str, Any]]

    # 라우팅 정보
    next_stage: Optional[str]
    routing_reason: Optional[str]

    # 미션 관련
    mission_progress: Optional[Dict[str, Any]]
    mission_completed: bool

    # AI 응답
    ai_response: Optional[str]
    speaker: Optional[str]
    emotion: Optional[str]

    # 이미지 정보
    image_url: Optional[str]
    thumbnail_url: Optional[str]

    # 가드레일 검증
    is_safe: bool
    guardrail_warnings: List[str]

    # 에러 처리
    error: Optional[str]

    # 메타데이터
    processing_time: float
    agent_trace: List[str]  # 어떤 에이전트가 실행되었는지 추적


class AgentDecision(TypedDict):
    """
    에이전트 결정 결과

    각 에이전트가 반환하는 결정 구조
    """
    action: str  # continue, route, end, error
    data: Optional[Dict[str, Any]]
    reasoning: Optional[str]
