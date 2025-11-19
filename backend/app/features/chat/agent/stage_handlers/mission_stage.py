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
from app.features.chat.services import MissionService, ContextService

from . import StageResult

logger = get_parent_logger("MissionStageHandler")


class MissionStageHandler:
    """
    미션 스테이지 핸들러

    동료 영입 미션을 처리합니다.
    """

    def __init__(
        self,
        mission_service: Optional[MissionService] = None,
        context_service: Optional[ContextService] = None
    ):
        """
        Args:
            mission_service: MissionService 인스턴스
            context_service: ContextService 인스턴스
        """
        self.mission_service = mission_service or MissionService()
        self.context_service = context_service or ContextService()

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

        # scenario를 state에 저장 (MissionService가 접근할 수 있도록)
        if "scenario" not in state and scenario:
            state["scenario"] = scenario

        logger.info("handle", f"🎯 Handling RECRUIT stage | User input: '{user_input}' | Mission active: {mission_state.get('active')} | Scenario keys in state: {list(state.keys())}")

        # 타겟 결정
        target = self.mission_service.determine_mission_target(
            state, user_input, mission_state
        )

        if not target:
            # 미션 완료 또는 타겟 없음
            return self._handle_no_target(state, stage, scenario, stage_tag)

        # 미션 첫 활성화 여부 확인
        is_first_activation = not mission_state.get("active")

        if is_first_activation:
            # 첫 활성화: scene_beats만 보여주기 (설득 평가 안 함)
            self.mission_service.activate_mission(state, target)

            # 타겟별 scene beats 가져오기
            metadata = scenario.get("metadata", {})
            mission_config = metadata.get("mission", {})
            targets_config = mission_config.get("targets", {})
            target_config = targets_config.get(target, {})
            scene_beats = target_config.get("scene_beats", [])

            combined_beats = scene_beats

            # speaker_pool에 타겟 캐릭터 추가
            base_speaker_pool = stage.get("speaker_pool", [])
            if target not in base_speaker_pool:
                speaker_pool = base_speaker_pool + [target]
            else:
                speaker_pool = base_speaker_pool

            # 미션 유지 (다음 턴에서 설득 시도)
            stage_complete = False
            next_stage = None

            logger.info("handle", f"First activation - showing scene_beats for {target}",
                       scene_beats_count=len(scene_beats))
        else:
            # 이후 시도: 설득 평가 + 피드백
            success = await self.mission_service.evaluate_recruit_attempt(state, target)
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

            combined_beats = feedback_beats
            speaker_pool = stage.get("speaker_pool", [])

            # 현재 타겟 완료 여부
            current_target_done = success or self._all_attempts_exhausted(state, target)

            # 모든 타겟 완료 여부 확인
            all_targets_complete = self._check_all_targets_complete(state, scenario)

            # 스테이지 완료는 모든 타겟이 완료되었을 때만
            stage_complete = all_targets_complete
            next_stage = stage.get("next") if stage_complete else None

            logger.info("handle", "Persuasion attempt",
                       target=target,
                       success=success,
                       current_target_done=current_target_done,
                       all_targets_complete=all_targets_complete)

        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": combined_beats,
            "speaker_pool": speaker_pool,
        }

        # ContextService로 공통 정보 추가 (recent_dialogues 자동 추가됨)
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

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
        """
        타겟이 없을 때 처리

        사용자가 선택하지 않았으면 stage_complete=False로 대기

        첫 진입 시 (stage_turn=0): intro beat 생성 (탄지로가 질문)
        이후 (stage_turn>0): beats 비우기 (context만으로 대화)
        """
        stage_turn = state.get("stage_turn", 0)

        # 첫 진입 시: stage.beats 사용 (있으면), 없으면 intro beat 생성
        if stage_turn == 0:
            stage_beats = stage.get("beats", [])
            if stage_beats:
                # stage에 beats가 있으면 사용
                beats = stage_beats
                logger.info("_handle_no_target", "First entry - using stage beats", beats_count=len(beats))
            else:
                # beats 없으면 짧은 intro beat 생성
                intro_beat = {
                    "speaker": "tanjiro",
                    "goal": "탄지로: '냄새를 추적하면... 젠이츠는 뒤쪽, 이노스케는 앞쪽 기관실 쪽이야! {user}, 어느 쪽으로 갈까?'",
                    "text": None
                }
                beats = [intro_beat]
                logger.info("_handle_no_target", "First entry - creating intro beat")
        else:
            # 이후에는 beats 비우기 (context 기반 대화)
            beats = []
            logger.debug("_handle_no_target", "Subsequent entry - waiting for selection")

        # Base context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": beats,
            "speaker_pool": stage.get("speaker_pool", ["tanjiro"]),
        }

        # ContextService로 공통 정보 추가 (recent_dialogues 자동 추가됨)
        children_ctx = self.context_service.build_children_context(
            base_ctx=base_ctx,
            state=state,
            scenario=scenario,
            stage=stage
        )

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=False,  # 선택 대기 - 스테이지 계속 유지
            next_stage=None
        )

    def _all_attempts_exhausted(self, state: Dict[str, Any], target: str) -> bool:
        """모든 시도 소진 여부"""
        from app.features.chat.services import MAX_ATTEMPTS
        attempts = state.get("recruit_attempts", {})
        return attempts.get(target, 0) >= MAX_ATTEMPTS

    def _check_all_targets_complete(self, state: Dict[str, Any], scenario: Dict[str, Any]) -> bool:
        """
        모든 타겟 완료 여부 확인

        타겟이 완료되었다는 것은:
        - allies_recruited에 포함되어 있거나
        - recruit_attempts가 MAX_ATTEMPTS에 도달했을 때

        Args:
            state: 게임 상태
            scenario: 시나리오 데이터

        Returns:
            모든 타겟이 완료되었으면 True
        """
        from app.features.chat.services import MAX_ATTEMPTS

        # scenario.metadata.mission.targets에서 타겟 목록 가져오기
        metadata = scenario.get("metadata", {})
        mission = metadata.get("mission", {})
        targets = mission.get("targets", {})
        if not targets:
            logger.warning("_check_all_targets_complete", "No targets found in scenario")
            return True  # 타겟이 없으면 완료로 간주

        allies = state.get("allies_recruited", [])
        attempts = state.get("recruit_attempts", {})

        for target_id in targets.keys():
            # 성공적으로 영입했거나, 모든 시도를 소진했으면 완료
            is_recruited = target_id in allies
            is_exhausted = attempts.get(target_id, 0) >= MAX_ATTEMPTS

            if not (is_recruited or is_exhausted):
                logger.debug("_check_all_targets_complete",
                            f"Target '{target_id}' not complete",
                            recruited=is_recruited,
                            attempts=attempts.get(target_id, 0))
                return False

        logger.info("_check_all_targets_complete", "✅ All targets complete")
        return True


__all__ = ["MissionStageHandler"]
