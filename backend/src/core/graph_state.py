"""
GraphState - LangGraph의 중앙 상태 저장소

LangGraph의 모든 노드가 공유하는 중앙 데이터 저장소(State).
Notion에 정의된 변수명 규칙을 따름.

기존 AgentState에서 GraphState로 변경하고 변수명을 표준화함.
"""

from typing import TypedDict, List, Dict, Optional, Any
from langchain_core.messages import BaseMessage
from typing_extensions import Annotated
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class NodeType(Enum):
    """워크플로우 노드 타입"""
    ROUTER = "router"
    GUARDRAIL = "guardrail"
    PARENT = "parent"
    CHILDREN = "children"
    DIALOGUE = "dialogue"
    STATE_TOOLS = "state_tools"
    SCENE_TOOLS = "scene_tools"
    END = "end"


class GraphState(TypedDict):
    """
    LangGraph의 모든 노드가 공유하는 중앙 데이터 저장소(State).
    Notion에 정의된 변수명 규칙을 따름.
    """
    # ============================================================
    # LangGraph 핵심
    # ============================================================
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    next_node: str

    # ============================================================
    # 세션 및 진행 상태
    # ============================================================
    session_id: str
    current_node_name: str  # 예: "CUTSCENE_5_INTRO"
    current_scene_id: str  # 현재 씬 ID
    turn_count: int
    is_timeout: bool  # 타임아웃 여부

    # ============================================================
    # 상호작용
    # ============================================================
    user_input: str  # 현재 사용자 입력
    user_inputs: List[str]  # 사용자 입력 히스토리 (user_inputs_history 별칭)
    user_name: str  # 사용자 이름
    agent_responses: List[Dict]  # [{"speaker": "Tanjiro", "text": "..."}]
    active_character: str  # 현재 대화 중인 캐릭터
    available_choices: List[Dict]  # [{"id": "A", "text": "..."}]

    # ============================================================
    # 게임 로직
    # ============================================================
    affinity_scores: Dict[str, int]  # {"inosuke": 70, "zenitsu": 50}
    is_persuasion_successful: Optional[bool]
    mission_result: Optional[str]  # 'success', 'failure'
    system_flags: List[str]  # 시스템 플래그 ["rengoku_arrived", "mission_started"]

    # RECRUIT 미션 관련
    allies_recruited: Optional[List[str]]  # 설득 성공한 캐릭터 목록
    recruit_attempts: Optional[Dict[str, int]]  # 캐릭터별 설득 시도 횟수
    recruit_failures: Optional[List[str]]  # 설득 실패한 캐릭터 목록
    recruit_order: Optional[List[str]]  # 설득 시도 순서

    # ============================================================
    # 엔딩
    # ============================================================
    final_ending: Optional[str]  # "hidden_ending", "normal_ending", etc.

    # ============================================================
    # 시나리오 관리 (JSON 기반)
    # ============================================================
    scenario_id: str  # 현재 시나리오 ID
    scenario_data: Optional[Dict[str, Any]]  # 로드된 전체 시나리오 JSON
    scenario: Optional[Dict[str, Any]]  # parent_agent용 scenario alias
    current_stage: Optional[str]  # 현재 스테이지 ID (intro, fork, recruit_mission 등)
    stage_history: List[str]  # 진행한 스테이지 기록
    stage_states: Dict[str, Dict[str, Any]]  # 스테이지별 상태 저장
    stage_turn: Optional[int]  # 현재 스테이지 내 턴 수 (scene["stage_turn"]의 복사본)

    # ============================================================
    # 메타데이터
    # ============================================================
    meta: Dict[str, Any]  # session_id, timestamp, version, processed_by 등

    # ============================================================
    # 메시지 히스토리
    # ============================================================
    message_history: List[Dict[str, Any]]  # 최근 메시지 목록

    # ============================================================
    # 라우팅 결과
    # ============================================================
    routing_result: Optional[Dict[str, Any]]  # Router Agent의 분류 결과

    # ============================================================
    # 출력
    # ============================================================
    output: Dict[str, Any]  # 사용자에게 보여줄 출력

    # ============================================================
    # 씬 상태 (scene)
    # ============================================================
    scene: Dict[str, Any]  # 씬 상태 (turn_count, current_scene, speaker_pool 등)

    # ============================================================
    # 임시 데이터 (fallback_blocked)
    # ============================================================
    temp_data: Dict[str, Any]  # 임시 데이터 저장소

    # ============================================================
    # 에러 및 예외 처리
    # ============================================================
    error_message: Optional[str]  # 에러 메시지

    # ============================================================
    # 툴 실행 결과
    # ============================================================
    tool_outputs: Optional[Dict[str, Any]]  # 툴 실행 결과

    # ============================================================
    # 런타임 컨텍스트 (Agent 간 데이터 전달)
    # ============================================================
    runtime: Optional[Dict[str, Any]]  # Parent → Children 등 agent 간 컨텍스트 전달

    # ============================================================
    # 배치 모드 (Batch Mode) - 대화 생성 상태
    # ============================================================
    has_more_dialogues: Optional[bool]  # 추가 대화 생성 필요 여부
    dialogue_batch_index: Optional[int]  # 현재 배치 인덱스
    dialogues_generated_count: Optional[int]  # 총 생성된 대화 수 (세션 전체 누적)
    stage_dialogue_counts: Optional[Dict[str, int]]  # 스테이지별 대화 수 {"INTRO": 12, "ROUTE_CHOICE": 5}

    # ============================================================
    # 이미지 관리 (Image Management)
    # ============================================================
    current_image: Optional[str]  # 현재 표시 중인 이미지 파일명
    image_transition_history: Optional[List[Dict[str, Any]]]  # 이미지 전환 이력
    event_flags: Optional[List[str]]  # 이벤트 플래그 (특정 이벤트 발생 시)

    # ============================================================
    # Agent 입력 (Parent → Children 등)
    # ============================================================
    agent_inputs: Optional[Dict[str, Any]]  # Agent 간 입력 데이터 전달
    children_ctx: Optional[Dict[str, Any]]  # Children Agent 컨텍스트
    paths: Optional[Dict[str, Any]]  # 파일 경로 정보


# ============================================================
# 호환성을 위한 별칭 (기존 코드가 AgentState를 import하는 경우)
# ============================================================
AgentState = GraphState  # 하위 호환성


# ============================================================
# GraphState 생성 헬퍼 함수
# ============================================================
def create_initial_graph_state(
    session_id: str,
    scenario_id: str = "scene5_akaza_encounter"
) -> GraphState:
    """
    초기 GraphState 생성

    Args:
        session_id: 세션 ID
        scenario_id: 시나리오 ID

    Returns:
        초기화된 GraphState
    """
    return GraphState(
        # LangGraph 핵심
        messages=[],
        next_node="router",

        # 세션 및 진행 상태
        session_id=session_id,
        current_node_name="INITIAL",
        current_scene_id="intro",
        turn_count=0,
        is_timeout=False,

        # 상호작용
        user_input="",
        user_inputs=[],
        user_name="여행자",  # 기본 이름
        agent_responses=[],
        active_character="tanjiro",
        available_choices=[],

        # 게임 로직
        affinity_scores={
            "inosuke": 300,  # 기본값
            "zenitsu": 400,
            "tanjiro": 500
        },
        is_persuasion_successful=None,
        mission_result=None,
        system_flags=[],

        # RECRUIT 미션 관련
        allies_recruited=[],
        recruit_attempts={},
        recruit_failures=[],
        recruit_order=[],

        # 엔딩
        final_ending=None,

        # 시나리오 관리
        scenario_id=scenario_id,
        scenario_data=None,
        scenario=None,
        current_stage=None,
        stage_history=[],
        stage_states={},
        stage_turn=0,

        # 메타데이터
        meta={
            "session_id": session_id,
            "timestamp": "",
            "version": "2.0",
            "processed_by": None
        },

        # 메시지 히스토리
        message_history=[],

        # 라우팅 결과
        routing_result=None,

        # 출력
        output={
            "dialogues": [],
            "images": [],
            "system_messages": []
        },

        # 씬 상태
        scene={
            "turn_count": 0,
            "current_scene": None,
            "speaker_pool": [],
            "stage_turn": 0
        },

        # 임시 데이터
        temp_data={},

        # 에러 및 예외 처리
        error_message=None,

        # 툴 실행 결과
        tool_outputs=None
    )


# ============================================================
# 에이전트 및 툴에서 사용하는 데이터 클래스들
# ============================================================

@dataclass
class RoutingResult:
    """Router Agent의 분류 결과"""
    classification: str  # "on_topic", "off_topic"
    confidence: float  # 0.0 ~ 1.0
    detected_intent: str  # "game_action", "casual_chat" 등
    keywords_found: List[str]
    reasoning: str = ""


@dataclass
class GuardrailResult:
    """Guardrail Agent의 검증 결과"""
    status: str  # "passed", "warning", "blocked"
    violated_rules: List[str]
    action_taken: str  # "proceed", "warn_and_proceed", "block"
    warning_message: Optional[str] = None


@dataclass
class UserChatInput:
    """사용자 입력"""
    content: str
    chat_no: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SceneToolRequest:
    """Scene Tools 요청"""
    action: str  # "get_cutscene", "get_emotion_image" 등
    scene_id: Optional[str] = None
    character_id: Optional[str] = None
    emotion: Optional[str] = None
    turn: Optional[int] = None
    asset_type: Optional[str] = None  # "cutscene", "emotion", "special_clear"
    summary_context: Optional[str] = None


@dataclass
class SceneToolResponse:
    """Scene Tools 응답"""
    status: str  # "success", "error"
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    generated: bool = False
    error_message: Optional[str] = None


@dataclass
class StateToolRequest:
    """State Tools 요청"""
    action: str  # "get_state", "update_state", "save_checkpoint"
    updates: Optional[Dict] = None
    character_updates: Optional[Dict] = None


@dataclass
class StateToolResponse:
    """State Tools 응답"""
    status: str  # "success", "error"
    updated_state: Optional[Dict] = None
    validation_errors: Optional[List[str]] = None
    hidden_ending_triggered: bool = False
    ending_type: Optional[str] = None


@dataclass
class ParentDecisions:
    """Parent Agent의 결정 사항"""
    should_speak: Dict[str, bool]  # 캐릭터별 발언 여부
    affinity_changes: Dict[str, int]  # 친밀도 변경
    special_events: List[str]  # 특별 이벤트
    next_stage: Optional[str] = None


@dataclass
class Dialogue:
    """대화 데이터"""
    speaker: str
    content: str
    emotion: str = "neutral"
    intensity: str = "normal"


@dataclass
class StoryContext:
    """스토리 컨텍스트"""
    current_scene: str
    key_events: List[str]


@dataclass
class DailyContext:
    """일상 컨텍스트"""
    topic: str
    mood: str


@dataclass
class EventContext:
    """이벤트 컨텍스트"""
    event_type: str
    participants: List[str]


# create_enhanced_initial_state 별칭 (하위 호환성)
create_enhanced_initial_state = create_initial_graph_state
