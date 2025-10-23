"""
Fallback 정책 도구
장면별 허용 횟수에 따라 엉뚱한 입력을 처리하고 스토리로 유도
"""

from typing import Dict, Any, Optional
from src.config.constants import (
    FALLBACK_ALLOW_NORMAL,
    FALLBACK_ALLOW_URGENT
)


class FallbackManager:
    """Fallback 관리자"""

    def __init__(self):
        """초기화"""
        pass

    def get_fallback_limit(self, scene_atmosphere: str) -> int:
        """
        장면 분위기에 따른 Fallback 허용 횟수 반환

        Args:
            scene_atmosphere: 장면 분위기 ("normal", "urgent", "combat")

        Returns:
            허용 횟수
        """
        if scene_atmosphere in ["urgent", "combat", "battle"]:
            return FALLBACK_ALLOW_URGENT
        else:
            return FALLBACK_ALLOW_NORMAL

    def check_fallback(self, state: Dict[str, Any], is_off_topic: bool) -> Dict[str, Any]:
        """
        Fallback 상태 확인 및 처리

        Args:
            state: AgentState 또는 GraphState
            is_off_topic: 입력이 off_topic인지 여부

        Returns:
            처리 결과 딕셔너리
            {
                "should_block": bool,  # 차단 여부
                "remaining_count": int,  # 남은 허용 횟수
                "message": str  # 사용자 안내 메시지
            }
        """
        # 현재 스테이지 데이터 가져오기
        current_stage_data = self._get_current_stage_data(state)
        # cutscene5_llm_driven.json에서 stage에 한 블록에서 atmosphere 가져오고 없으면 normal 키 사용
        scene_atmosphere = current_stage_data.get("atmosphere", "normal")

        # 허용 횟수 가져오기
        fallback_limit = self.get_fallback_limit(scene_atmosphere)

        # 현재 fallback 카운트 가져오기
        fallback_count = state.get("temp_data", {}).get("fallback_count", 0)

        # off_topic이 아니면 카운트 초기화
        if not is_off_topic:
            return {
                "should_block": False,
                "remaining_count": fallback_limit,
                "message": "",
                "reset_count": True
            }

        # 카운트 증가
        fallback_count += 1

        # 허용 횟수 초과 여부 확인
        should_block = fallback_count > fallback_limit
        remaining_count = max(0, fallback_limit - fallback_count)

        # 메시지 생성
        message = self._generate_fallback_message(
            scene_atmosphere,
            fallback_count,
            fallback_limit,
            should_block,
            current_stage_data
        )

        return {
            "should_block": should_block,
            "remaining_count": remaining_count,
            "message": message,
            "new_count": fallback_count,
            "reset_count": False
        }

    def _get_current_stage_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """현재 스테이지 데이터 가져오기"""
        scenario_data = state.get("scenario_data", {})
        current_stage = state.get("current_stage", "")
        stages = scenario_data.get("stages", {})

        # stages가 list인 경우 tag로 찾기
        if isinstance(stages, list):
            return next((s for s in stages if s.get("tag", "").upper() == current_stage.upper()), {})
        else:
            return stages.get(current_stage, {})

    def _generate_fallback_message(
        self,
        scene_atmosphere: str,
        fallback_count: int,
        fallback_limit: int,
        should_block: bool,
        stage_data: Dict[str, Any]
    ) -> str:
        """
        Fallback 메시지 생성

        허용 범위 내: 캐릭터 대사 톤으로 부드럽게 유도
        범위 초과: 시스템 메시지 톤으로 강하게 유도
        """
        # 현재 목표와 선택지 추출
        objective = stage_data.get("objective", "")
        choices = stage_data.get("choices", [])

        # 급박한 장면
        if scene_atmosphere in ["urgent", "combat", "battle"]:
            if should_block:
                return f"⚠️  지금은 선택할 시간이 없습니다! 즉시 결정해주세요.\n\n{self._format_choices(choices)}"
            else:
                return f"💥 지금은 농담할 상황이 아닙니다. 빨리 행동하세요!"

        # 일반 장면
        else:
            remaining_count = max(0, fallback_limit - fallback_count)
            if should_block:
                return f"🤔 계속 다른 이야기를 하시네요. 이제 스토리를 진행하겠습니다.\n\n{objective}\n\n{self._format_choices(choices)}"
            elif fallback_count == fallback_limit:
                return f"😅 잠깐, 지금은 이 상황에 집중해야 할 것 같아요. ({remaining_count}회 남음)\n\n{objective}"
            elif fallback_count >= fallback_limit - 1:
                return f"🙂 재미있는 얘기지만, 지금은 이 일을 먼저 해결해야 해요."
            else:
                return f"😊 그것도 좋지만, 지금은 이 상황을 먼저 처리하는 게 어떨까요?"

    def _format_choices(self, choices: list) -> str:
        """선택지 포맷팅"""
        if not choices:
            return ""

        formatted = "**가능한 선택지:**\n"
        for idx, choice in enumerate(choices, 1):
            formatted += f"{idx}. {choice.get('text', '')}\n"

        return formatted.strip()

    def apply_fallback_to_state(self, state: Dict[str, Any], fallback_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback 결과를 상태에 반영

        Args:
            state: AgentState 또는 GraphState
            fallback_result: check_fallback() 반환값

        Returns:
            업데이트된 상태
        """
        # temp_data 초기화
        if "temp_data" not in state:
            state["temp_data"] = {}

        # 카운트 업데이트 또는 리셋
        if fallback_result.get("reset_count"):
            state["temp_data"]["fallback_count"] = 0
        else:
            state["temp_data"]["fallback_count"] = fallback_result.get("new_count", 0)

        # 차단 플래그 설정
        if fallback_result.get("should_block"):
            state["temp_data"]["fallback_blocked"] = True

        return state


# 싱글톤 인스턴스
fallback_manager = FallbackManager()


def check_fallback_policy(state: Dict[str, Any], is_off_topic: bool) -> Dict[str, Any]:
    """
    Fallback 정책 확인 (단축 함수)

    Args:
        state: AgentState 또는 GraphState
        is_off_topic: 입력이 off_topic인지 여부

    Returns:
        처리 결과 딕셔너리
    """
    return fallback_manager.check_fallback(state, is_off_topic)


def apply_fallback_result(state: Dict[str, Any], fallback_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback 결과를 상태에 반영 (단축 함수)

    Args:
        state: AgentState 또는 GraphState
        fallback_result: check_fallback() 반환값

    Returns:
        업데이트된 상태
    """
    return fallback_manager.apply_fallback_to_state(state, fallback_result)
