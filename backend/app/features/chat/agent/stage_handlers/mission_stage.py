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
from app.features.chat.services import MissionService, ContextService, MAX_ATTEMPTS

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

        # ✅ state에 scenario 추가 (mission_service가 keywords 접근 가능하도록)
        state["scenario_data"] = scenario

        # 타겟 결정
        target = self.mission_service.determine_mission_target(
            state, user_input, mission_state
        )

        logger.info("handle", f"Target determination result: {target}",
                   user_input=user_input[:50])

        if not target:
            # 미션 완료 또는 타겟 없음
            return self._handle_no_target(state, stage, scenario, stage_tag)

        # ✅ 미션 첫 활성화 여부 확인
        # turn이 없거나 (None), target이 바뀌었거나, active가 False면 첫 활성화
        mission_turn = mission_state.get("turn")
        current_target = mission_state.get("target")
        is_active = mission_state.get("active", False)

        # ✅ 기존 시도 횟수 확인 (이미 시도한 적 있으면 첫 활성화 아님)
        has_existing_attempts = state.get("recruit_attempts", {}).get(target, 0) > 0

        # 첫 활성화: turn이 None이거나, target이 다르거나, (active=False이면서 기존 시도 없음)
        is_first_activation = (
            mission_turn is None or
            current_target != target or
            (not is_active and not has_existing_attempts)
        )

        # mission_turn을 숫자로 변환 (None이면 0)
        mission_turn = mission_turn if mission_turn is not None else 0

        # Scene 전개 최소 턴 수 (scene을 한 번 보여준 후 설득 모드 진입)
        MIN_SCENE_TURNS = 1  # ✅ 1턴 후 설득 모드 진입

        if is_first_activation:
            # 첫 활성화: scene_context 사용 + 미션 시작 메시지 생성
            mission_state["active"] = True
            mission_state["target"] = target
            mission_state["scene_playing"] = True  # ✅ scene 전개 중
            mission_state["turn"] = 1  # ✅ 미션 턴 1부터 시작 (0은 미설정 상태)

            # ✅ stage_turn을 0으로 설정 (새로운 장면 시작으로 인식되도록)
            state["stage_turn"] = 0

            # 타겟별 scene_context 가져오기
            metadata = scenario.get("metadata", {})
            mission_config = metadata.get("mission", {})
            targets_config = mission_config.get("targets", {})
            target_config = targets_config.get(target, {})
            stage_context = target_config.get("scene_context", "")

            # ✅ 미션 시작 시스템 메시지 생성
            from app.features.chat.services import CHARACTER_NAMES_KR
            char_display = CHARACTER_NAMES_KR.get(target, target.capitalize())
            mission_start_beat = {
                "speaker": "narr",
                "text": f"🎯 미션: {char_display} 를 설득해주세요 (남은 시도: {MAX_ATTEMPTS}회)",
                "goal": f"미션 시작: {char_display} 설득",
                "fx": "ui_confirm|mission_start"
            }
            combined_beats = [mission_start_beat]

            # speaker_pool에 타겟 캐릭터 추가
            base_speaker_pool = stage.get("speaker_pool", [])
            if target not in base_speaker_pool:
                speaker_pool = base_speaker_pool + [target]
            else:
                speaker_pool = base_speaker_pool

            # 미션 유지 (scene 전개 계속)
            stage_complete = False
            next_stage = None

            logger.info("handle", f"First activation: {target} mission started")
        else:
            # ✅ 미션 계속 진행 - active 상태 유지 (deactivate되었다가 다시 시작되는 경우)
            if not is_active:
                mission_state["active"] = True
                mission_state["target"] = target

            # ✅ 미션 턴 증가
            mission_state["turn"] = mission_turn + 1

            # ✅ scene 전개 중인지 확인 (턴 수 기반)
            if mission_state.get("scene_playing") and mission_turn < MIN_SCENE_TURNS:
                # Scene 전개 모드 유지 (설득 평가 안 함)
                metadata = scenario.get("metadata", {})
                mission_config = metadata.get("mission", {})
                targets_config = mission_config.get("targets", {})
                target_config = targets_config.get(target, {})
                stage_context = target_config.get("scene_context", "")

                combined_beats = []
                base_speaker_pool = stage.get("speaker_pool", [])
                if target not in base_speaker_pool:
                    speaker_pool = base_speaker_pool + [target]
                else:
                    speaker_pool = base_speaker_pool

                stage_complete = False
                next_stage = None

                logger.info("handle", f"Scene playing: {target} (turn {mission_turn}/{MIN_SCENE_TURNS})")
            else:
                # ✅ MIN_SCENE_TURNS 도달 → 설득 모드 전환
                if mission_state.get("scene_playing"):
                    mission_state["scene_playing"] = False

                # 설득 평가 + 피드백
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

                # 현재 타겟 완료 여부
                current_target_done = success or self._all_attempts_exhausted(state, target)

                # ✅ 타겟 완료 시 (성공 또는 소진) → transition으로 바로 이동
                if current_target_done:
                    # 미션 비활성화
                    self.mission_service.deactivate_mission(state)

                    combined_beats = feedback_beats
                    stage_context = ""  # ❌ LLM 대화 생성 안 함 (기본값)
                    speaker_pool = ["tanjiro"]

                    # 모든 타겟 완료 여부 확인
                    all_targets_complete = self._check_all_targets_complete(state, scenario)

                    # transition_line 생성
                    from app.features.chat.services import CHARACTER_NAMES_KR

                    if all_targets_complete:
                        # ✅ 모든 타겟 완료 → success_dialogues 사용
                        logger.info("handle", "🎉 All targets complete! Generating completion dialogue")

                        metadata = scenario.get("metadata", {})
                        mission_config = metadata.get("mission", {})
                        success_dialogues = mission_config.get("success_dialogues", {})
                        targets_config = mission_config.get("targets", {})

                        # allies_recruited와 전체 타겟 비교
                        allies = state.get("allies_recruited", [])
                        all_target_ids = list(targets_config.keys())

                        # 완료 메시지 선택
                        if len(allies) == len(all_target_ids):
                            # 모두 성공
                            msg_template = success_dialogues.get("allies", "좋아, 모두 모았어! 이제 렌고쿠 님을 도우러 가자!")
                            allies_names = [CHARACTER_NAMES_KR.get(a, a) for a in allies]
                            allies_str = ", ".join(allies_names)
                            completion_msg = msg_template.replace("{allies}", allies_str)
                        elif len(allies) > 0:
                            # 일부 성공
                            msg_template = success_dialogues.get("partial", "{allies}는 합류했지만, {fails}는 설득하지 못했어... 그래도 서두르자!")
                            allies_names = [CHARACTER_NAMES_KR.get(a, a) for a in allies]
                            allies_str = ", ".join(allies_names)

                            # 실패한 타겟들
                            failed_targets = [t for t in all_target_ids if t not in allies]
                            failed_names = [CHARACTER_NAMES_KR.get(f, f) for f in failed_targets]
                            fails_str = ", ".join(failed_names)

                            completion_msg = msg_template.replace("{allies}", allies_str).replace("{fails}", fails_str)
                        else:
                            # 모두 실패
                            msg_template = success_dialogues.get("none", "아무도 합류하지 못했어... 그래도 우리라도 어서 돌아가자!")
                            completion_msg = msg_template

                        # 완료 메시지 추가
                        completion_beat = {
                            "speaker": "tanjiro",
                            "text": completion_msg,
                            "goal": completion_msg,
                            "fx": "ui_confirm|mission_complete"
                        }
                        combined_beats.append(completion_beat)

                        # 스테이지 완료 처리
                        stage_complete = True
                        next_stage = mission_config.get("complete_next_stage")

                        logger.info("handle", f"✅ Mission stage complete: {len(allies)}/{len(all_target_ids)} recruited | next_stage={next_stage}")

                    else:
                        # ✅ 다음 타겟으로 전환
                        next_target = self.mission_service.select_next_target(state, exclude=[target])

                        # ✅ 기본값 설정 (다음 타겟이 없을 경우를 대비)
                        stage_complete = False
                        next_stage = None

                        # transition_line 생성
                        result = "success" if success else "fail"
                        transition = self.mission_service.build_transition_line(
                            mission_result=result,
                            completed_ally=CHARACTER_NAMES_KR.get(target, target),
                            next_target=CHARACTER_NAMES_KR.get(next_target) if next_target else None
                        )

                        if transition:
                            combined_beats.append(transition)

                        # ✅ 다음 타겟이 있으면 즉시 미션 활성화 (유저 입력 없이 자동 전환)
                        if next_target:
                            logger.info("handle", f"🔄 Auto-transition: activating mission for {next_target}")

                            # 다음 타겟의 미션 활성화
                            self.mission_service.activate_mission(state, next_target)
                            mission_state["scene_playing"] = True
                            mission_state["turn"] = 1

                            # ✅ stage_turn을 0으로 설정 (새로운 장면 시작으로 인식)
                            state["stage_turn"] = 0

                            # 다음 타겟의 scene_context 가져오기
                            metadata = scenario.get("metadata", {})
                            mission_config = metadata.get("mission", {})
                            targets_config = mission_config.get("targets", {})
                            next_target_config = targets_config.get(next_target, {})
                            next_scene_context = next_target_config.get("scene_context", "")

                            # 다음 타겟의 미션 시작 메시지 추가
                            char_display = CHARACTER_NAMES_KR.get(next_target, next_target.capitalize())
                            mission_start_beat = {
                                "speaker": "narr",
                                "text": f"🎯 미션: {char_display} 를 설득해주세요 (남은 시도: {MAX_ATTEMPTS}회)",
                                "goal": f"미션 시작: {char_display} 설득",
                                "fx": "ui_confirm|mission_start"
                            }
                            combined_beats.append(mission_start_beat)

                            # stage_context를 다음 타겟의 scene_context로 설정
                            stage_context = next_scene_context

                            # speaker_pool에 다음 타겟 추가
                            base_speaker_pool = stage.get("speaker_pool", [])
                            if next_target not in base_speaker_pool:
                                speaker_pool = base_speaker_pool + [next_target]
                            else:
                                speaker_pool = base_speaker_pool

                            logger.info("handle", f"✅ Auto-activated next mission: {next_target} with scene_context")

                    logger.info("handle", f"Mission complete: {target} | success={success} | all_complete={all_targets_complete}")

                else:
                    # ✅ 시도 남음 → 계속 설득
                    combined_beats = feedback_beats

                    # speaker_pool에 타겟 캐릭터 추가
                    base_speaker_pool = stage.get("speaker_pool", [])
                    if target not in base_speaker_pool:
                        speaker_pool = base_speaker_pool + [target]
                    else:
                        speaker_pool = base_speaker_pool

                    # scene_context 재사용 (캐릭터 반응 생성)
                    metadata = scenario.get("metadata", {})
                    mission_config = metadata.get("mission", {})
                    targets_config = mission_config.get("targets", {})
                    target_config = targets_config.get(target, {})
                    stage_context = target_config.get("scene_context", "")

                    logger.info("handle", f"Mission continues: {target} | attempts={state.get('recruit_attempts', {}).get(target, 0)}/{MAX_ATTEMPTS}")

                    # ✅ 시도 남음 → 스테이지 유지
                    stage_complete = False
                    next_stage = None

        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": combined_beats,
            "speaker_pool": speaker_pool,
        }

        # ✅ stage_context 추가 (항상 추가하여 context_service가 stage.context를 덮어쓰지 못하게 함)
        if 'stage_context' in locals():
            base_ctx["stage_context"] = stage_context if stage_context is not None else ""

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

        # ✅ beats는 항상 비우고 stage.context 사용
        beats = []
        stage_context = stage.get("context", "")

        # # 첫 진입 시: stage.beats 사용 (있으면), 없으면 intro beat 생성
        # if stage_turn == 0:
        #     stage_beats = stage.get("beats", [])
        #     if stage_beats:
        #         # stage에 beats가 있으면 사용
        #         beats = stage_beats
        #         logger.info("_handle_no_target", "First entry - using stage beats", beats_count=len(beats))
        #     else:
        #         # beats 없으면 짧은 intro beat 생성
        #         intro_beat = {
        #             "speaker": "tanjiro",
        #             "goal": "탄지로: '냄새를 추적하면... 젠이츠는 뒤쪽, 이노스케는 앞쪽 기관실 쪽이야! {user}, 어느 쪽으로 갈까?'",
        #             "text": None
        #         }
        #         beats = [intro_beat]
        #         logger.info("_handle_no_target", "First entry - creating intro beat")
        # else:
        #     # 이후에는 beats 비우기 (context 기반 대화)
        #     beats = []

        # Base context 구성
        base_ctx = {
            "stage_tag": stage_tag,
            "stage_type": "mission",
            "beats": beats,
            "speaker_pool": stage.get("speaker_pool", ["tanjiro"]),
        }

        # ✅ stage_context 추가
        if stage_context:
            base_ctx["stage_context"] = stage_context

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
                return False

        logger.info("_check_all_targets_complete", "✅ All targets complete")
        return True


__all__ = ["MissionStageHandler"]
