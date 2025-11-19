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
        pass

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
        # ✅ 기존 상태를 먼저 병합한 후 필수 필드만 덮어쓰기 (mission 등 유지)
        state = {
            **session_state,  # 기존 상태 먼저 병합 (mission, recruit_attempts 등 유지)
            "scenario_id": scenario_id,
            "user_input": user_input,
            "current_stage": session_state.get("current_stage", "TRAIN_PRELUDE"),
            "stage_turn": session_state.get("stage_turn", 0),
            "turn_count": session_state.get("turn_count", 0),
        }

        # ✅ 없을 때만 빈 dict/list로 초기화 (기존 값 유지)
        state.setdefault("game", {})
        state.setdefault("scene", {})
        state.setdefault("temp_data", {})
        state.setdefault("mission", {})
        state.setdefault("recruit_attempts", {})
        state.setdefault("allies_recruited", [])
        state.setdefault("recruit_order", [])
        state.setdefault("conversation_history", [])

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
        # turn_count와 stage_turn 모두 항상 증가
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
            current_stage = state.get("current_stage")
            updated["current_stage"] = next_stage
            # 실제로 스테이지가 변경될 때만 stage_turn 리셋
            if next_stage != current_stage:
                updated["stage_turn"] = 0
                # 스테이지 전환 시 현재 user_input을 cached_user_input으로 저장
                # (다음 스테이지에서 routing을 위해 사용)
                updated["cached_user_input"] = state.get("user_input", "")

        # 스테이지 완료 플래그
        if stage_complete:
            scene_state = updated.get("scene", {})
            scene_state["stage_completed"] = True
            updated["scene"] = scene_state

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
