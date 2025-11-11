"""
Dialogue Agent
대화 생성 에이전트
"""
from typing import Dict, Any
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger
from ..parent import ParentAgent as LegacyParentAgent
import os

logger = get_service_logger("DialogueAgent")


class DialogueAgent:
    """Dialogue Agent - AI 대화 생성"""

    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4")
        self.legacy_parent = LegacyParentAgent()

    async def generate_dialogue(self, state: GraphState) -> GraphState:
        """대화 생성 - Legacy Parent Agent 사용"""
        logger.info("generate_dialogue", "Generating dialogue using Legacy Parent Agent")

        user_input = state.get("user_input", "")
        scenario_id = state.get("scenario_id", "")
        session_id = state.get("session_id", "")
        user_id = state.get("user_id", "")
        turn_count = state.get("turn_count", 0)
        current_stage = state.get("current_stage", "")

        # session_state 구성
        session_state = {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "user_name": state.get("user_name", "User"),
            "current_stage": current_stage,
            "turn_count": turn_count,
            "stage_turn": state.get("stage_turn", 0),
        }

        try:
            # Legacy Parent Agent 실행
            result = await self.legacy_parent.run(
                user_message=user_input,
                session_state=session_state,
                scenario_id=scenario_id
            )

            # Legacy Parent Agent의 결과를 GraphState 형식으로 변환
            if "output" not in state:
                state["output"] = {}

            # ChatMessage 객체들을 dict로 변환
            dialogues_list = []
            for dialogue in result.dialogues:
                if hasattr(dialogue, '__dict__'):
                    # ChatMessage 객체인 경우
                    dialogues_list.append({
                        "speaker": dialogue.speaker,
                        "text": dialogue.text,
                        "emotion": dialogue.emotion,
                        "fx": dialogue.fx,
                        "image_index": dialogue.image_index,
                        "affinity_level": dialogue.affinity_level,
                        "emotion_intensity": dialogue.emotion_intensity
                    })
                elif isinstance(dialogue, dict):
                    # 이미 dict인 경우
                    dialogues_list.append(dialogue)

            state["output"]["dialogues"] = dialogues_list
            state["output"]["next_stage"] = result.next_stage
            state["output"]["stage_complete"] = result.stage_complete
            state["output"]["affinity_delta"] = result.affinity_delta or {}

            # 메시지 추가
            if "messages" not in state:
                state["messages"] = []

            for dialogue in dialogues_list:
                message = {
                    "role": "assistant" if dialogue.get("speaker") != "user" else "user",
                    "content": dialogue.get("text", ""),
                    "speaker": dialogue.get("speaker", "ai"),
                    "emotion": dialogue.get("emotion", "neutral")
                }
                state["messages"].append(message)

            logger.info("generate_dialogue", "Dialogue generated successfully using Legacy Parent Agent")

        except Exception as e:
            logger.error("generate_dialogue", f"Failed to generate dialogue: {e}")
            # Fallback to dummy response
            ai_response = f"죄송합니다. 응답 생성 중 오류가 발생했습니다."
            state["output"]["dialogues"] = [
                {
                    "speaker": "ai",
                    "text": ai_response,
                    "emotion": "neutral"
                }
            ]
            state["output"]["next_stage"] = current_stage
            state["output"]["stage_complete"] = False
            state["output"]["affinity_delta"] = {}

        return state
