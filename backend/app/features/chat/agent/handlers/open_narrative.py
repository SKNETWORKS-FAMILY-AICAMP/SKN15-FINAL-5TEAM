"""
Open Narrative Handler - 개방형 대화 스테이지
"""
from typing import Dict, Any
from ..agent_response import AgentResponse
from app.core.tools import scene_tools


class OpenNarrativeHandler:
    """
    Open Narrative 스테이지 핸들러

    역할:
    - 완전히 자유로운 대화 (beats 없음)
    - LLM이 즉흥적으로 대화 생성
    - 턴 수 기반 종료
    """

    def __init__(self, locale: str = "ko"):
        self.locale = locale

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> AgentResponse:
        """
        Open Narrative 스테이지 처리

        Args:
            state: GraphState
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            AgentResponse
        """
        # Open narrative는 beats가 없음 (LLM이 즉흥 생성)
        speaker_pool = stage.get("characters") or scene_tools.get_character_pool(scenario)

        # 컨텍스트 설명
        context_description = stage.get("context_description", "")

        children_ctx = {
            "beats": [],  # beats 없음!
            "speaker_pool": speaker_pool,
            "stage_tag": state.get("stage_tag"),
            "stage_type": "open_narrative",
            "context_description": context_description,
            "fallback": {
                "dialogues": [
                    {
                        "speaker": speaker_pool[0] if speaker_pool else "narr",
                        "text": "무슨 이야기를 나누고 싶으신가요?"
                    }
                ]
            }
        }

        # 턴 수 기반 종료 (5~10턴)
        turn_count = state.get("turn_count", 0)
        max_narrative_turns = stage.get("max_turns", 5)

        stage_complete = turn_count >= max_narrative_turns

        # 다음 스테이지
        next_stage = stage.get("next_stage") if stage_complete else None

        return AgentResponse(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )
