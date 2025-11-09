"""
Mission Stage Handler - 미션 스테이지 처리

Features:
- 동료 영입 미션 처리
- LLM 기반 설득 평가
- 시도 횟수 관리
- 피드백 생성
"""
from typing import Dict, Any, List, Optional

from app.core.logging import get_parent_logger
from app.features.chat.services import MissionService

from . import StageResult

logger = get_parent_logger("MissionStageHandler")


class MissionStageHandler:
    """
    미션 스테이지 핸들러

    동료 영입 미션을 처리합니다.
    """

    def __init__(self, mission_service: Optional[MissionService] = None):
        """
        Args:
            mission_service: MissionService 인스턴스
        """
        self.mission_service = mission_service or MissionService()

        logger.info("__init__", "MissionStageHandler initialized")

    async def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """
        미션 스테이지 처리

        Args:
            state: 게임 상태
            stage: 스테이지 정의
            scenario: 시나리오 데이터

        Returns:
            StageResult
        """
        stage_tag = stage.get("tag", "mission")
        user_input = state.get("user_input", "")
        mission_state = state.setdefault("mission", {})

        logger.debug("handle", "Handling mission stage",
                    stage_tag=stage_tag,
                    mission_active=mission_state.get("active"))

        # 타겟 결정
        target = self.mission_service.determine_mission_target(
            state, user_input, mission_state
        )

        if not target:
            # 미션 완료 또는 타겟 없음
            return self._handle_no_target(state, stage, scenario, stage_tag)

        # 미션 활성화
        if not mission_state.get("active"):
            self.mission_service.activate_mission(state, target)

        # 설득 시도
        success = await self.mission_service.evaluate_recruit_attempt(state, target)

        # 시도 횟수 증가
        self.mission_service.increment_attempt(state, target)

        # 피드백 생성
        feedback_beats = self.mission_service.build_feedback_beats(
            state, target, success
        )

        # 성공 시 동료 추가
        if success:
            allies = state.setdefault("allies_recruited", [])
            if target not in allies:
                allies.append(target)
                logger.info("handle", f"✅ Ally recruited: {target}")

        # 미션 비활성화
        self.mission_service.deactivate_mission(state)

        # Children context 구성
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": feedback_beats,
            "speaker_pool": stage.get("speaker_pool", []),
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        # 스테이지 완료 여부
        stage_complete = success or self._all_attempts_exhausted(state, target)
        next_stage = stage.get("next") if stage_complete else None

        logger.info("handle", "Mission stage processed",
                   target=target,
                   success=success,
                   stage_complete=stage_complete)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage
        )

    def _handle_no_target(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        stage_tag: str
    ) -> StageResult:
        """타겟이 없을 때 처리"""
        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": [{
                "speaker": "tanjiro",
                "text": "이제 누구를 찾아야 할까?",
                "goal": "다음 동료를 찾는다"
            }],
            "speaker_pool": stage.get("speaker_pool", ["tanjiro"]),
            "scenario_id": scenario.get("scenario_id", "unknown"),
        }

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=True,
            next_stage=stage.get("next")
        )

    def _all_attempts_exhausted(self, state: Dict[str, Any], target: str) -> bool:
        """모든 시도 소진 여부"""
        from app.features.chat.services import MAX_ATTEMPTS
        attempts = state.get("recruit_attempts", {})
        return attempts.get(target, 0) >= MAX_ATTEMPTS


__all__ = ["MissionStageHandler"]
