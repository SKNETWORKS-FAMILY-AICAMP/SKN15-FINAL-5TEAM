"""
State Service - 세션 상태 관리
대화 세션의 상태를 관리하고 추적
"""
from typing import Dict, Any, Optional
from app.core.logging import get_parent_logger

logger = get_parent_logger("StateService")


class StateService:
    """
    세션 상태 관리 서비스

    책임:
    - 세션 상태 초기화
    - 상태 검증 및 보정
    - 상태 업데이트
    - 진행도 추적
    """

    def __init__(self):
        """StateService 초기화"""
        logger.info("__init__", "StateService initialized")

    def prepare_state(
        self,
        session_state: Dict[str, Any],
        scenario_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        """
        세션 상태 준비 및 검증

        Args:
            session_state: 현재 세션 상태
            scenario_id: 시나리오 ID
            user_input: 사용자 입력

        Returns:
            준비된 상태 dict
        """
        # 기본 상태 구조 보장
        state = {
            "scenario_id": scenario_id,
            "user_input": user_input,
            "current_stage": session_state.get("current_stage", "intro"),
            "stage_turn": session_state.get("stage_turn", 0),
            "turn_count": session_state.get("turn_count", 0),
            "game": session_state.get("game", {}),
            "scene": session_state.get("scene", {}),
            "temp_data": session_state.get("temp_data", {}),
            "conversation_history": session_state.get("conversation_history", []),
            **session_state  # 기존 상태 병합
        }

        logger.info(
            "prepare_state",
            "State prepared",
            scenario_id=scenario_id,
            current_stage=state["current_stage"],
            turn_count=state["turn_count"]
        )

        return state

    def update_state(
        self,
        state: Dict[str, Any],
        dialogues: list,
        next_stage: Optional[str] = None,
        stage_complete: bool = False
    ) -> Dict[str, Any]:
        """
        상태 업데이트

        Args:
            state: 현재 상태
            dialogues: 생성된 대화 목록
            next_stage: 다음 스테이지 (있다면)
            stage_complete: 스테이지 완료 여부

        Returns:
            업데이트된 상태
        """
        updated = {
            **state,
            "turn_count": state.get("turn_count", 0) + 1,
            "stage_turn": state.get("stage_turn", 0) + 1,
        }

        # 대화 이력 업데이트 (최근 20개만 유지)
        history = state.get("conversation_history", [])
        history.extend(dialogues)
        updated["conversation_history"] = history[-20:]

        # 스테이지 전환 처리
        if next_stage:
            updated["current_stage"] = next_stage
            updated["stage_turn"] = 0  # 스테이지 턴 리셋

        # 스테이지 완료 플래그
        if stage_complete:
            scene_state = updated.get("scene", {})
            scene_state["stage_completed"] = True
            updated["scene"] = scene_state

        logger.info(
            "update_state",
            "State updated",
            turn_count=updated["turn_count"],
            stage_turn=updated["stage_turn"],
            current_stage=updated["current_stage"]
        )

        return updated

    def reset_stage(self, state: Dict[str, Any], new_stage: str) -> Dict[str, Any]:
        """
        새 스테이지로 전환 (턴 카운트 리셋)

        Args:
            state: 현재 상태
            new_stage: 새로운 스테이지 ID

        Returns:
            업데이트된 상태
        """
        updated = {
            **state,
            "current_stage": new_stage,
            "stage_turn": 0,
        }

        # scene 상태 초기화
        scene_state = updated.get("scene", {})
        scene_state["stage_completed"] = False
        updated["scene"] = scene_state

        # temp_data에서 스테이지 관련 데이터 제거
        temp_data = updated.get("temp_data", {})
        temp_data.pop("completed_stage", None)
        updated["temp_data"] = temp_data

        logger.info(
            "reset_stage",
            "Stage reset",
            new_stage=new_stage
        )

        return updated

    def get_progress_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        진행도 통계

        Args:
            state: 현재 상태

        Returns:
            통계 dict
        """
        return {
            "scenario_id": state.get("scenario_id"),
            "current_stage": state.get("current_stage"),
            "turn_count": state.get("turn_count", 0),
            "stage_turn": state.get("stage_turn", 0),
            "conversation_length": len(state.get("conversation_history", [])),
        }
