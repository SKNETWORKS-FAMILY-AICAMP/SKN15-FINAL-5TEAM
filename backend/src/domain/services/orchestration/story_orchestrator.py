"""
Story Orchestrator

스토리 생성 및 오케스트레이션을 담당.
현재는 LLM 호출 없이 임시(stub) 로직으로 작동함.
"""

from typing import Dict, Any
from src.core.utils.logger import log


class StoryOrchestrator:
    """스토리 오케스트레이터 (임시 stub 구현)"""

    def __init__(self):
        log.info("StoryOrchestrator initialized")

    def generate_narrative(
        self,
        state: Dict[str, Any],
        user_input: str,
        context: str = "",
        speaker_pool: list = None,
        turn_count: int = 0,
    ) -> Dict[str, Any]:
        """
        사용자 입력 기반 내러티브 생성 (임시 stub)

        Args:
            state: 현재 상태
            user_input: 사용자 입력
            context: 시나리오 컨텍스트
            speaker_pool: 대화 가능한 캐릭터 목록
            turn_count: 현재 턴 수
        Returns:
            dict: beats 및 상태 업데이트 정보
        """
        log.warning("StoryOrchestrator.generate_narrative called - stub implementation")

        speaker = speaker_pool[0] if speaker_pool else "narr"
        input_text = user_input.strip() or "..."
        generated_text = f"'{input_text}'에 대한 이야기가 펼쳐집니다. 열차가 흔들리며 긴장감이 감돕니다."

        return {
            "beats": [
                {
                    "speaker": speaker,
                    "text": generated_text,
                    "emotion": "neutral"
                }
            ],
            "state_update": {
                "last_user_input": input_text,
                "story_summary": f"{context}\n사용자 입력: {input_text}",
            },
            "has_more": False,
        }


# ✅ 싱글톤 인스턴스 (핸들러에서 get_story_orchestrator로 접근)
_story_orchestrator_instance = None


def get_story_orchestrator() -> StoryOrchestrator:
    global _story_orchestrator_instance
    if _story_orchestrator_instance is None:
        _story_orchestrator_instance = StoryOrchestrator()
        log.info("StoryOrchestrator instance created")
    return _story_orchestrator_instance
