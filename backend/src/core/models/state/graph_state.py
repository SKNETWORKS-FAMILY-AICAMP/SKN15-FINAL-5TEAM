"""
GraphState - LangGraph 통합 상태 저장소

모든 하위 State를 통합한 중앙 데이터 저장소.
LangGraph의 모든 노드가 이 State를 공유함.

구조:
- SessionState: 세션 메타데이터
- GameState: 게임 진행 상태
- ConversationState: 대화 문맥
- ScenarioState: 시나리오 데이터
"""

from typing import TypedDict, Optional, Dict, Any
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage

from .session_state import SessionState
from .game_state import GameState
from .conversation_state import ConversationState
from .scenario_state import ScenarioState


class GraphState(TypedDict):
    """
    LangGraph 중앙 상태 저장소 (통합)

    이전 700줄 단일 파일에서 → 4개 도메인으로 분할
    """

    # ============================================================
    # LangGraph 핵심 필드
    # ============================================================
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]  # LangChain 메시지 체인
    next_node: str  # 다음 실행할 노드

    # ============================================================
    # 도메인별 State (분할됨!)
    # ============================================================
    session: SessionState  # 세션 메타데이터
    game: GameState  # 게임 진행 상태
    conversation: ConversationState  # 대화 문맥
    scenario: ScenarioState  # 시나리오 데이터

    # ============================================================
    # 라우팅 및 출력 (상위 레벨)
    # ============================================================
    routing_result: Optional[Dict[str, Any]]  # Router Agent 분류 결과
    output: Dict[str, Any]  # 사용자에게 보여줄 최종 출력

    # ============================================================
    # 런타임 컨텍스트 (Agent 간 데이터 전달)
    # ============================================================
    runtime: Optional[Dict[str, Any]]  # Parent → Children 등 agent 간 전달
    agent_inputs: Optional[Dict[str, Any]]  # Agent 간 입력 데이터
    children_ctx: Optional[Dict[str, Any]]  # Children Agent 컨텍스트

    # ============================================================
    # 툴 및 임시 데이터
    # ============================================================
    tool_outputs: Optional[Dict[str, Any]]  # 툴 실행 결과
    temp_data: Dict[str, Any]  # 임시 데이터 저장소

    # ============================================================
    # 에러 처리
    # ============================================================
    error_message: Optional[str]  # 에러 메시지


# ============================================================
# 하위 호환성 (기존 코드가 AgentState를 import하는 경우)
# ============================================================
AgentState = GraphState


# ============================================================
# GraphState 생성 헬퍼 함수
# ============================================================
def create_initial_graph_state(
    session_id: str,
    scenario_id: str = "scene5_akaza_encounter",
    user_name: str = "플레이어"
) -> GraphState:
    """
    초기 GraphState 생성

    Args:
        session_id: 세션 ID
        scenario_id: 시나리오 ID
        user_name: 사용자 이름

    Returns:
        초기화된 GraphState
    """
    return GraphState(
        # LangGraph 핵심
        messages=[],
        next_node="guardrail",

        # Session State
        session=SessionState(
            session_id=session_id,
            scenario_id=scenario_id,
            turn_count=0,
            is_timeout=False,
            current_node_name="INITIAL",
            current_scene_id="intro",
            user_name=user_name,
            meta={}
        ),

        # Game State
        game=GameState(
            current_stage=None,
            stage_history=[],
            stage_states={},
            stage_turn=0,
            affinity_scores={},
            mission_result=None,
            is_persuasion_successful=None,
            allies_recruited=None,
            recruit_attempts=None,
            recruit_failures=None,
            recruit_order=None,
            system_flags=[],
            event_flags=None,
            final_ending=None,
            current_image=None,
            image_transition_history=None
        ),

        # Conversation State
        conversation=ConversationState(
            messages=[],
            user_input="",
            user_inputs=[],
            agent_responses=[],
            active_character="",
            message_history=[],
            conversation_summary=None,
            summary_turn_count=0,
            has_more_dialogues=None,
            dialogue_batch_index=None,
            dialogues_generated_count=None,
            stage_dialogue_counts=None
        ),

        # Scenario State
        scenario=ScenarioState(
            scenario_data=None,
            scenario=None,
            scene={},
            available_choices=[],
            paths=None
        ),

        # 라우팅 및 출력
        routing_result=None,
        output={},

        # 런타임
        runtime=None,
        agent_inputs=None,
        children_ctx=None,

        # 툴 및 임시
        tool_outputs=None,
        temp_data={},

        # 에러
        error_message=None
    )
