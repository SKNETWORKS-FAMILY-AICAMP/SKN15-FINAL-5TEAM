"""
Story Orchestrator

스토리 생성 및 오케스트레이션을 담당
TODO: 실제 구현 필요
"""

from typing import Dict, Any
import logging

log = logging.getLogger(__name__)


class StoryOrchestrator:
    """스토리 오케스트레이터 (스텁 구현)"""

    def __init__(self):
        """초기화"""
        log.debug("StoryOrchestrator initialized")

    def generate_narrative(
        self,
        state: Dict[str, Any],
        user_input: str,
        context: str = "",
        speaker_pool: list = None,
        turn_count: int = 0
    ) -> Dict[str, Any]:
        """
        사용자 입력 기반 내러티브 생성 (스텁)

        Args:
            state: 현재 상태
            user_input: 사용자 입력
            context: 컨텍스트 정보
            speaker_pool: 화자 풀
            turn_count: 턴 카운트

        Returns:
            생성된 내러티브 정보
        """
        # TODO: 실제 LLM 기반 내러티브 생성 구현
        log.warning("StoryOrchestrator.generate_narrative called - stub implementation")
        speaker = speaker_pool[0] if speaker_pool else "내레이터"
        return {
            "dialogues": [
                {
                    "speaker": speaker,
                    "text": f"'{user_input}'에 대한 이야기가 펼쳐집니다.",
                    "emotion": "neutral"
                }
            ],
            "state_update": {},
            "has_more": False
        }


# 싱글톤 인스턴스
_story_orchestrator_instance = None


def get_story_orchestrator() -> StoryOrchestrator:
    """StoryOrchestrator 싱글톤 인스턴스 반환"""
    global _story_orchestrator_instance
    if _story_orchestrator_instance is None:
        _story_orchestrator_instance = StoryOrchestrator()
        log.debug("StoryOrchestrator instance created")
    return _story_orchestrator_instance
