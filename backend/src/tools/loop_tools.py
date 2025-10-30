"""
Loop 제어 도구
반복 입력을 감지하고 자동 전환 처리
"""

from typing import Dict, Any, List, Optional
from src.config.constants import (
    DEFAULT_LOOP_LIMIT,
    URGENT_LOOP_LIMIT,
    SYSTEM_MESSAGE_LOOP_EXCEEDED
)
from src.tools.scene_tools import get_stage_atmosphere


class LoopDetector:
    """반복 입력 감지 및 제어"""

    def __init__(self):
        """초기화"""
        pass

    def get_loop_limit(self, scene_atmosphere: str) -> int:
        """
        장면 분위기에 따른 루프 한계 반환

        Args:
            scene_atmosphere: 장면 분위기 ("normal", "urgent", "tense", "calm", "combat")

        Returns:
            루프 한계 횟수
        """
        if scene_atmosphere in ["urgent", "tense", "combat", "battle"]:
            return URGENT_LOOP_LIMIT
        else:
            return DEFAULT_LOOP_LIMIT

    def check_loop(self, state: Dict[str, Any], current_input: str, is_valid: bool) -> Dict[str, Any]:
        """
        반복 입력 감지 및 처리

        Args:
            state: AgentState 또는 GraphState
            current_input: 현재 사용자 입력
            is_valid: 입력이 유효한지 여부

        Returns:
            처리 결과 딕셔너리
            {
                "should_auto_advance": bool,  # 자동 전환 여부
                "loop_count": int,  # 현재 루프 카운트
                "message": str  # 사용자 안내 메시지
            }
        """
        # 1) on-topic(=is_valid) 입력인 경우: 루프 카운트 초기화만 수행 (자동 전환 제거)
        if is_valid:
            return {
                "should_auto_advance": False,
                "loop_count": 0,
                "message": "",
                "reset": True
            }

        # 이전 입력 기록 가져오기
        input_history = state.get("temp_data", {}).get("input_history", [])
        loop_count = state.get("temp_data", {}).get("loop_count", 0)

        # 입력이 이전 입력과 동일하거나 매우 유사한지 확인
        is_repeated = self._is_repeated_input(current_input, input_history)

        if is_repeated:
            loop_count += 1
        else:
            # 다른 입력이지만 여전히 유효하지 않은 경우
            loop_count = 1

        # 입력 기록에 추가 (최대 5개 유지)
        input_history.append(current_input)
        if len(input_history) > 5:
            input_history.pop(0)

        # 장면별 루프 한계 가져오기
        current_stage_data = self._get_current_stage_data(state)
        scene_atmosphere = current_stage_data.get("atmosphere", "normal")
        loop_limit = self.get_loop_limit(scene_atmosphere)

        # 루프 한계 초과 여부 확인
        should_auto_advance = loop_count > loop_limit

        # 메시지 생성
        message = ""
        if should_auto_advance:
            # 자동으로 다음 스테이지로 넘겨버리는 메시지
            message = self._generate_auto_advance_message(current_stage_data)
        elif loop_count >= loop_limit:
            message = f"⚠️  동일한 입력이 반복되고 있습니다. (남은 기회: {loop_limit - loop_count}회)"

        return {
            "should_auto_advance": should_auto_advance,
            "loop_count": loop_count,
            "message": message,
            "new_input_history": input_history,
            "reset": False
        }

    def _is_repeated_input(self, current_input: str, input_history: List[str]) -> bool:
        """
        입력이 반복되었는지 확인

        Args:
            current_input: 현재 입력
            input_history: 이전 입력 기록

        Returns:
            반복 여부
        """
        if not input_history:
            return False

        # 최근 3개 입력과 비교
        recent_inputs = input_history[-3:]

        # 정규화 (소문자, 공백 제거)
        normalized_current = current_input.lower().replace(" ", "")

        for prev_input in recent_inputs:
            normalized_prev = prev_input.lower().replace(" ", "")

            # 완전 일치 또는 80% 이상 유사
            if normalized_current == normalized_prev:
                return True

            # 간단한 유사도 체크 (문자열 포함)
            if len(normalized_current) > 3 and normalized_current in normalized_prev:
                return True
            if len(normalized_prev) > 3 and normalized_prev in normalized_current:
                return True

        return False

    def _get_current_stage_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """현재 스테이지 데이터 가져오기 (atmosphere 정규화 포함)"""
        scenario_data = state.get("scenario_data", {})
        current_stage = state.get("current_stage", "")
        stages = scenario_data.get("stages", {})

        # stages가 list인 경우 tag로 찾기
        if isinstance(stages, list):
            stage_data = next((s for s in stages if s.get("tag", "").upper() == current_stage.upper()), {})
        else:
            stage_data = stages.get(current_stage, {})

        # atmosphere를 정규화된 문자열로 변환
        if stage_data and "atmosphere" in stage_data:
            normalized_atmosphere = get_stage_atmosphere(stage_data)
            stage_data = {**stage_data, "atmosphere": normalized_atmosphere}

        return stage_data

    def _generate_auto_advance_message(self, stage_data: Dict[str, Any]) -> str:
        """
        자동 전환 메시지 생성

        Args:
            stage_data: 현재 스테이지 데이터

        Returns:
            메시지
        """
        auto_advance_path = stage_data.get("auto_advance_path", "")

        if auto_advance_path:
            return f"{SYSTEM_MESSAGE_LOOP_EXCEEDED}\n\n➡️  자동으로 '{auto_advance_path}'(으)로 진행합니다."
        else:
            return f"{SYSTEM_MESSAGE_LOOP_EXCEEDED}\n\n➡️  자동으로 다음 장면으로 진행합니다."

    def get_auto_advance_stage(self, state: Dict[str, Any]) -> Optional[str]:
        """
        자동 전환할 스테이지 ID 반환

        Args:
            state: AgentState 또는 GraphState

        Returns:
            다음 스테이지 ID (없으면 None)
        """
        current_stage_data = self._get_current_stage_data(state)
        auto_advance_path = current_stage_data.get("auto_advance_path")

        if auto_advance_path:
            return auto_advance_path

        # 기본 next_stage 사용
        return current_stage_data.get("next_stage")

    def apply_loop_to_state(self, state: Dict[str, Any], loop_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Loop 결과를 상태에 반영

        Args:
            state: AgentState 또는 GraphState
            loop_result: check_loop() 반환값

        Returns:
            업데이트된 상태
        """
        # temp_data 초기화
        if "temp_data" not in state:
            state["temp_data"] = {}

        # 리셋 또는 업데이트
        if loop_result.get("reset"):
            state["temp_data"]["loop_count"] = 0
            state["temp_data"]["input_history"] = []
        else:
            state["temp_data"]["loop_count"] = loop_result.get("loop_count", 0)
            state["temp_data"]["input_history"] = loop_result.get("new_input_history", [])

        # 자동 전환 플래그
        if loop_result.get("should_auto_advance"):
            state["temp_data"]["auto_advance"] = True
            # 자동 전환할 스테이지 결정
            next_stage = self.get_auto_advance_stage(state)
            if next_stage:
                state["temp_data"]["auto_advance_target"] = next_stage

        return state


# 싱글톤 인스턴스
loop_detector = LoopDetector()


def check_loop_detection(state: Dict[str, Any], current_input: str, is_valid: bool) -> Dict[str, Any]:
    """
    반복 입력 감지 (단축 함수)

    Args:
        state: AgentState 또는 GraphState
        current_input: 현재 사용자 입력
        is_valid: 입력이 유효한지 여부

    Returns:
        처리 결과 딕셔너리
    """
    return loop_detector.check_loop(state, current_input, is_valid)


def apply_loop_result(state: Dict[str, Any], loop_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Loop 결과를 상태에 반영 (단축 함수)

    Args:
        state: AgentState 또는 GraphState
        loop_result: check_loop() 반환값

    Returns:
        업데이트된 상태
    """
    return loop_detector.apply_loop_to_state(state, loop_result)
