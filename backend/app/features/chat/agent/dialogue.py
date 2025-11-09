"""
Dialogue Agent - 대화 검증 및 수정 에이전트

Features:
- LLM 기반 대화 검증
- 검증 실패 시 자동 수정
- DialogueService 활용
"""
from typing import Dict, Any, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import DialogueService

logger = get_parent_logger("DialogueAgent")


class DialogueAgent:
    """
    대화 검증 및 수정 에이전트 (Layer 3 - Agent)

    Features:
    - validate_and_correct(): 대화 검증 및 자동 수정
    - 품질 관리

    Example:
        agent = DialogueAgent(dialogue_service=service)

        result = await agent.validate_and_correct(
            dialogue_text="탄지로가 외친다",
            speaker="tanjiro",
            state=state
        )

        if result["corrected"]:
            dialogue_text = result["corrected_text"]
    """

    def __init__(
        self,
        dialogue_service: Optional[DialogueService] = None,
        enable_validation: bool = True
    ):
        """
        Args:
            dialogue_service: DialogueService 인스턴스
            enable_validation: 검증 활성화 여부
        """
        self.dialogue_service = dialogue_service or DialogueService()
        self.enable_validation = enable_validation

        logger.info("__init__", "DialogueAgent initialized",
                   enable_validation=enable_validation)

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


__all__ = ["DialogueAgent"]
