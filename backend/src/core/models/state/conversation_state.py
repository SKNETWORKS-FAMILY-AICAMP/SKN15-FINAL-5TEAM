"""
Conversation State - 대화 문맥 및 히스토리
사용자와 AI 간의 대화 흐름을 관리
"""

from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from typing_extensions import Annotated


class ConversationState(TypedDict):
    """
    대화 문맥 및 히스토리
    - 사용자 입력
    - Agent 응답
    - 대화 히스토리
    - 장기 기억
    """

    # ============================================================
    # LangGraph 메시지 (LangChain 호환)
    # ============================================================
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]

    # ============================================================
    # 사용자 입력
    # ============================================================
    user_input: str  # 현재 사용자 입력
    user_inputs: List[str]  # 사용자 입력 히스토리

    # ============================================================
    # Agent 응답
    # ============================================================
    agent_responses: List[Dict]  # [{"speaker": "Tanjiro", "text": "..."}]
    active_character: str  # 현재 대화 중인 캐릭터

    # ============================================================
    # 대화 히스토리
    # ============================================================
    message_history: List[Dict[str, Any]]  # 최근 메시지 목록 (turn, speaker, text)

    # ============================================================
    # 장기 기억 (Long-term Memory)
    # ============================================================
    conversation_summary: Optional[str]  # 대화 요약 (10턴마다 자동 생성)
    summary_turn_count: int  # 요약에 포함된 마지막 턴 번호

    # ============================================================
    # 배치 모드 (Batch Mode) - 대화 생성
    # ============================================================
    has_more_dialogues: Optional[bool]  # 추가 대화 생성 필요 여부
    dialogue_batch_index: Optional[int]  # 현재 배치 인덱스
    dialogues_generated_count: Optional[int]  # 총 생성된 대화 수
    stage_dialogue_counts: Optional[Dict[str, int]]  # 스테이지별 대화 수
