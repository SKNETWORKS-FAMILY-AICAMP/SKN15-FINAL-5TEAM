"""
Dialogue Agent - 대화 검증/생성 에이전트

Features:
- validate_and_correct(): 대화 검증 및 자동 수정 (ParentAgent용)
- generate_dialogue(): 대화 생성 (LangGraph용)
- DialogueService 활용
"""
from typing import Dict, Any, Optional
import os

from app.core.logging import get_parent_logger
from app.features.chat.services import DialogueService
from .graph_state import GraphState

logger = get_parent_logger("DialogueAgent")


class DialogueAgent:
    """
    대화 검증 및 생성 에이전트 (Layer 3 - Agent)

    Features:
    - validate_and_correct(): 대화 검증 및 자동 수정 (ParentAgent용)
    - generate_dialogue(): ParentAgent 래핑 (LangGraph용)

    Example (검증):
        agent = DialogueAgent(dialogue_service=service)
        result = await agent.validate_and_correct(
            dialogue_text="탄지로가 외친다",
            speaker="tanjiro",
            state=state
        )

    Example (생성):
        agent = DialogueAgent(parent_agent=parent)
        state = await agent.generate_dialogue(state)
    """

    def __init__(
        self,
        dialogue_service: Optional[DialogueService] = None,
        enable_validation: bool = True,
        parent_agent=None  # LangGraph용 ParentAgent
    ):
        """
        Args:
            dialogue_service: DialogueService 인스턴스
            enable_validation: 검증 활성화 여부
            parent_agent: ParentAgent (LangGraph 통합용, optional)
        """
        self.dialogue_service = dialogue_service or DialogueService()
        self.enable_validation = enable_validation
        self.legacy_parent = parent_agent  # ParentAgent (LangGraph용)
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4")

        logger.info("__init__", "DialogueAgent initialized",
                   enable_validation=enable_validation,
                   has_parent_agent=parent_agent is not None)

    async def validate_and_correct(
        self,
        dialogue_text: str,
        speaker: str,
        state: Dict[str, Any],
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """
        대화 검증 및 자동 수정

        Args:
            dialogue_text: 검증할 대화
            speaker: 화자
            state: 게임 상태
            max_retries: 최대 재시도 횟수

        Returns:
            {
                "passed": bool,
                "corrected": bool,
                "original_text": str,
                "corrected_text": str,
                "validation_result": {...}
            }
        """
        if not self.enable_validation:
            # 검증 비활성화 시 원본 그대로 반환
            return {
                "passed": True,
                "corrected": False,
                "original_text": dialogue_text,
                "corrected_text": dialogue_text,
                "validation_result": {}
            }

        original_text = dialogue_text
        corrected = False

        logger.debug("validate_and_correct", "Validating dialogue",
                    speaker=speaker,
                    text_len=len(dialogue_text))

        # 검증
        validation_result = await self.dialogue_service.validate_dialogue(
            dialogue_text=dialogue_text,
            speaker=speaker,
            state=state,
            use_llm=True
        )

        # 검증 통과 시 원본 반환
        if validation_result.get("passed", True):
            logger.info("validate_and_correct", "Validation passed", speaker=speaker)
            return {
                "passed": True,
                "corrected": False,
                "original_text": original_text,
                "corrected_text": dialogue_text,
                "validation_result": validation_result
            }

        # 검증 실패 시 수정 시도
        logger.warning("validate_and_correct", "Validation failed, attempting correction",
                      speaker=speaker,
                      issues=validation_result.get("issues", []))

        for attempt in range(max_retries):
            corrected_text = await self.dialogue_service.correct_dialogue(
                dialogue_text=dialogue_text,
                speaker=speaker,
                validation_result=validation_result,
                state=state
            )

            if corrected_text and corrected_text != dialogue_text:
                # 수정된 대화 재검증
                revalidation_result = await self.dialogue_service.validate_dialogue(
                    dialogue_text=corrected_text,
                    speaker=speaker,
                    state=state,
                    use_llm=True
                )

                if revalidation_result.get("passed", False):
                    logger.info("validate_and_correct", "Correction successful",
                               speaker=speaker,
                               attempt=attempt + 1)
                    return {
                        "passed": True,
                        "corrected": True,
                        "original_text": original_text,
                        "corrected_text": corrected_text,
                        "validation_result": revalidation_result
                    }

                # 재검증 실패 시 다음 시도
                dialogue_text = corrected_text
                validation_result = revalidation_result

        # 모든 수정 시도 실패 - 원본 반환
        logger.warning("validate_and_correct", "All correction attempts failed, using original",
                      speaker=speaker)

        return {
            "passed": False,
            "corrected": False,
            "original_text": original_text,
            "corrected_text": original_text,
            "validation_result": validation_result
        }

    async def generate_dialogue(self, state: GraphState) -> GraphState:
        """
        대화 생성 - LangGraph 워크플로우용
        ParentAgent를 래핑하여 GraphState 형식으로 변환

        Args:
            state: GraphState

        Returns:
            업데이트된 GraphState
        """
        if self.legacy_parent is None:
            logger.error("generate_dialogue", "ParentAgent not provided")
            raise ValueError("DialogueAgent.generate_dialogue requires parent_agent parameter in __init__")

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


__all__ = ["DialogueAgent"]
