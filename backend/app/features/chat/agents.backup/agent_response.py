"""
Agent Response - 에이전트 응답 구조
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    """
    에이전트 응답 표준 구조
    """
    # Children Agent 컨텍스트
    children_ctx: Dict[str, Any] = field(default_factory=dict)

    # 다음 스테이지
    next_stage: Optional[str] = None

    # 스테이지 완료 여부
    stage_complete: bool = False

    # SceneTool 응답 (이미지 등)
    scene_tool_response: Optional[Any] = None

    # StateTool 응답 (게임 상태 업데이트)
    state_tool_response: Optional[Any] = None

    # 생성된 대화 (agent_responses)
    dialogues: List[Dict[str, Any]] = field(default_factory=list)

    # 에러
    error: Optional[str] = None


def create_agent_response(**kwargs) -> AgentResponse:
    """AgentResponse 생성 헬퍼"""
    return AgentResponse(**kwargs)
