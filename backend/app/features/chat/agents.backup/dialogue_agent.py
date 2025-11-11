"""
Dialogue Agent
대화 생성 에이전트
"""
from typing import Dict, Any
from .graph_state import GraphState
from app.core.logging import get_service_logger
import os

logger = get_service_logger("DialogueAgent")


class DialogueAgent:
    """Dialogue Agent - AI 대화 생성"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4")

    def generate_dialogue(self, state: GraphState) -> GraphState:
        """대화 생성"""
        logger.info("generate_dialogue", "Generating dialogue")
        
        user_input = state.get("user_input", "")
        user_name = state.get("user_name", "User")
        stage_type = state.get("stage_type", "open_narrative")
        
        # TODO: LLM Service를 통해 실제 대화 생성
        # 현재는 더미 응답
        state["ai_response"] = f"[AI 응답] {user_name}님의 입력 '{user_input}'에 대한 응답입니다. (Stage: {stage_type})"
        state["speaker"] = "ai"
        state["emotion"] = "neutral"
        
        # 메시지 추가
        message = {
            "role": "assistant",
            "content": state["ai_response"],
            "speaker": state["speaker"],
            "emotion": state["emotion"]
        }
        
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append(message)
        
        logger.info("generate_dialogue", "Dialogue generated successfully")
        return state
