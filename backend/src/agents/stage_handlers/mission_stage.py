"""
============================================================
🎮 Mission Stage Handler — 동료 영입 미션
============================================================
LLM 기반 동료 영입 미션 처리 (서비스 레이어 사용)

리팩토링 완료:
- MissionLogicService: 타겟 관리 + LLM 평가
- MissionFeedbackService: 피드백 + 메시지 생성
- MissionRecordService: DB 저장 + 이벤트
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.services import (
    MissionLogicService,
    MissionFeedbackService,
    MissionRecordService,
    DialogueFormatterService,
)
from src.tools.scene_tools import (
    get_i18n_entries,
    get_next_stage_tag,
    get_stage_type,
    get_speaker_pool,
)
from src.tools.fallback_tools import trigger_fallback
from src.utils.logger import log

from . import StageResult


class MissionHandler:
    """
    LLM 기반 동료 영입 미션 처리기

    서비스 레이어를 활용하여 비즈니스 로직을 분리했습니다.
    """

    MAX_ATTEMPTS = 3
    VALID_TARGETS = ("inosuke", "zenitsu")
    CHARACTER_NAMES_KR = {
        "inosuke": "이노스케",
        "zenitsu": "젠이츠",
        "tanjiro": "탄지로",
        "nezuko": "네즈코",
    }

    def __init__(self, locale: str = "ko", llm: Any = None):
        """
        Args:
            locale: 로케일 (기본값: "ko")
            llm: LLM 클라이언트 (선택)
        """
        self.locale = locale

        # 🆕 서비스 레이어 초기화
        self._logic_service = MissionLogicService(llm_client=llm)
        self._feedback_service = MissionFeedbackService(locale=locale)
        self._record_service = MissionRecordService()
        self._formatter_service = DialogueFormatterService()

    def handle(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any]
    ) -> StageResult:
        """미션 스테이지 처리 메인 로직"""
        stage_tag = stage.get("tag") or stage.get("id") or "mission"
        speaker_pool = get_speaker_pool(stage, stage.get("speaker_pool", []))
        user_input = (state.get("user_input") or "").strip()
        temp_data = state.setdefault("temp_data", {})
        mission_state = state.setdefault("mission", {})

        # Intro 처리
        intro_shown = temp_data.get("mission_intro_shown", False)
        if not intro_shown:
            return self._handle_intro(state, stage, scenario, user_input, stage_tag, speaker_pool)

        # ✅ 타겟 결정 (서비스 사용)
        target = self._logic_service.determine_mission_target(state, user_input, mission_state)

        # 타겟이 유효하지 않으면 fallback 또는 완료 처리
        if target not in self.VALID_TARGETS:
            return self._handle_invalid_target(state, stage, scenario, stage_tag, speaker_pool)

        # Discovery 단계 처리
        if self._should_show_discovery(state, user_input, target, mission_state):
            return self._handle_discovery(state, stage, scenario, target, stage_tag, mission_state)

        # Persuasion 단계 처리
        return self._handle_persuasion(state, stage, scenario, target, stage_tag, mission_state)

    # ==================== Handler Methods ====================

    def _handle_intro(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        user_input: str,
        stage_tag: str,
        speaker_pool: List[str]
    ) -> StageResult:
        """미션 인트로 처리"""
        temp_data = state.setdefault("temp_data", {})
        temp_data["mission_intro_shown"] = True

        # 타겟 감지 (단순 감지)
        from src.utils.text_matcher import detect_mission_target
        detected_target = detect_mission_target(user_input)
        if detected_target in self.VALID_TARGETS:
            temp_data["locked_mission_target"] = detected_target
            state["mission_target"] = detected_target

        intro_key = stage.get("intro_i18n") or "beats_smell"
        intro_beats = self._to_dialogues(
            get_i18n_entries(scenario, intro_key, locale=self.locale)
        )
        log("mission", f"[INTRO] Showing mission intro via {intro_key}")

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=speaker_pool,
            beats=intro_beats,
            mission_info={"phase": "intro"}
        )
        return StageResult(children_ctx=children_ctx, stage_complete=False)

    def _handle_invalid_target(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        stage_tag: str,
        speaker_pool: List[str]
    ) -> StageResult:
        """유효하지 않은 타겟 처리"""
        # ✅ 모든 미션 완료 확인 (서비스 사용)
        if self._logic_service.all_missions_resolved(state):
            return self._handle_mission_complete(state, stage, stage_tag, speaker_pool)

        temp_data = state.setdefault("temp_data", {})
        mission_intro_shown = temp_data.get("mission_intro_shown", False)

        guide_message = {
            "speaker": "tanjiro",
            "text": (
                "지금은 동료를 찾는 데 집중해야 해. "
                "이노스케나 젠이츠를 찾아서 함께 싸우자고 설득해야 해. "
                "누구를 찾을지 말해줄래?"
            )
        }

        # Fallback 처리
        user_input = state.get("user_input", "")
        fallback_payload = trigger_fallback(state, stage, reason="invalid_target")

        fallback_dialogues = [guide_message]

        if not mission_intro_shown:
            beats_smell = self._to_dialogues(
                get_i18n_entries(scenario, "beats_smell", locale=self.locale)
            )
            fallback_dialogues.extend(beats_smell)
            temp_data["mission_intro_shown"] = True

        fallback_payload.setdefault("dialogues", []).extend(fallback_dialogues)

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=speaker_pool,
            beats=[],
            fallback={"dialogues": fallback_payload.get("dialogues", [])}
        )
        log("mission", f"[FALLBACK] ambiguous target on {stage_tag} - guiding user back", user_input=user_input)

        return StageResult(
            children_ctx=children_ctx,
            fallback_payload=fallback_payload,
            stage_complete=False
        )

    def _handle_mission_complete(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        stage_tag: str,
        speaker_pool: List[str]
    ) -> StageResult:
        """모든 미션 완료 처리"""
        allies = state.get("allies_recruited", [])

        # ✅ 완료 메시지 생성 (서비스 사용)
        msg = self._feedback_service.generate_mission_complete_message(allies)

        wrap_up_dialogues = [
            {
                "speaker": "tanjiro",
                "text": msg,
                "fx": "urgent_heartbeat|flame_flash"
            }
        ]

        temp_data = state.setdefault("temp_data", {})
        queue = temp_data.setdefault("mission_success_queue", [])
        queue.extend(wrap_up_dialogues)

        # ✅ 미션 비활성화 (서비스 사용)
        self._logic_service.deactivate_mission(state)

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=speaker_pool or ["tanjiro", "narr"],
            beats=[],
            mission_info={"phase": "complete"}
        )

        next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
        log("mission", f"[AUTO-COMPLETE] all allies ready → {next_stage}", allies=allies)
        return StageResult(
            children_ctx=children_ctx,
            stage_complete=True,
            next_stage=next_stage
        )

    def _handle_discovery(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        target: str,
        stage_tag: str,
        mission_state: Dict[str, Any]
    ) -> StageResult:
        """Discovery 단계 처리"""
        temp_data = state.setdefault("temp_data", {})
        temp_data["current_discovery_target"] = target
        log("mission", f"[DISCOVERY] Finding {target}")

        discovery_beats = get_i18n_entries(scenario, f"{target}_scene", locale=self.locale)
        discovery_pool = self._extract_speaker_pool_from_beats(discovery_beats, target)

        log("mission", f"[DISCOVERY] Speaker pool for {target}_scene: {discovery_pool}")

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=discovery_pool,
            beats=self._to_dialogues(discovery_beats),
            mission_info={
                "target": target,
                "phase": "discovery",
            }
        )

        # ✅ 미션 활성화 (서비스 사용)
        self._logic_service.activate_mission(state, target)
        return StageResult(children_ctx=children_ctx, stage_complete=False)

    def _handle_persuasion(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        target: str,
        stage_tag: str,
        mission_state: Dict[str, Any]
    ) -> StageResult:
        """Persuasion 단계 처리"""
        # ✅ 미션 활성화 + 시도 증가 (서비스 사용)
        self._logic_service.activate_mission(state, target)
        self._logic_service.increment_attempt(state, target)

        attempts_map = state.get("recruit_attempts", {})
        current_attempts = attempts_map.get(target, 0)
        remaining_attempts = max(0, self.MAX_ATTEMPTS - current_attempts)

        log(
            "mission",
            f"[ATTEMPT] {target} try={current_attempts}/{self.MAX_ATTEMPTS}",
            remaining=remaining_attempts,
        )

        # ✅ LLM 평가 (서비스 사용)
        success = self._logic_service.evaluate_recruit_attempt(state, target)

        # ✅ 결과 업데이트 (서비스 사용)
        self._logic_service.update_recruit_result(state, target, success)

        # ✅ DB 저장 (서비스 사용)
        self._record_service.save_recruit_result(state, target, success, current_attempts)

        if success:
            return self._handle_persuasion_success(
                state, stage, scenario, target, stage_tag
            )
        else:
            return self._handle_persuasion_failure(
                state, stage, scenario, target, stage_tag, remaining_attempts
            )

    def _handle_persuasion_success(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        target: str,
        stage_tag: str
    ) -> StageResult:
        """설득 성공 처리"""
        temp_data = state.setdefault("temp_data", {})
        temp_data["current_discovery_target"] = None

        # ✅ 미션 비활성화 (서비스 사용)
        self._logic_service.deactivate_mission(state)

        log("mission", f"[PERSUASION] {target} → SUCCESS, discovery reset for next character")

        # ✅ 다음 타겟 선택 (서비스 사용)
        next_target = self._logic_service.select_next_target(state, exclude=[target])

        # ✅ 피드백 beats 생성 (서비스 사용)
        feedback_dialogues = self._feedback_service.build_feedback_beats(state, target, True, scenario)

        # ✅ 전환 대사 추가 (서비스 사용)
        if next_target:
            transition = self._feedback_service.build_transition_line(
                "success",
                self.CHARACTER_NAMES_KR.get(target, target),
                self.CHARACTER_NAMES_KR.get(next_target)
            )
            if transition:
                feedback_dialogues.append(transition)

        feedback_speakers = sorted(set([target, "tanjiro", "narr"]))

        if next_target:
            log("mission", f"[AUTO-SWITCH] {target} succeeded → moving to {next_target}")
            temp_data["locked_mission_target"] = next_target
            temp_data["current_discovery_target"] = next_target
            state["mission_target"] = next_target
            state["mission"]["target"] = next_target
            state["mission"]["active"] = False

            rediscovery_ctx = self._build_rediscovery_context(
                stage, scenario, next_target, preface=feedback_dialogues
            )
            return StageResult(children_ctx=rediscovery_ctx, stage_complete=False)

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=feedback_speakers,
            beats=feedback_dialogues,
            mission_info={
                "target": target,
                "success": True,
                "attempts": state.get("recruit_attempts", {}).get(target, 0),
            }
        )

        # ✅ 모든 미션 완료 확인 (서비스 사용)
        stage_complete = self._logic_service.all_missions_resolved(state)
        next_stage = None

        if stage_complete:
            queue = temp_data.setdefault("mission_success_queue", [])
            queue.extend(feedback_dialogues)
            self._logic_service.deactivate_mission(state)
            children_ctx.pop("fallback", None)
            next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
            log(
                "mission",
                f"[RESOLVED] stage={stage_tag}, next={next_stage}",
                recruited=state.get("allies_recruited"),
                attempts=state.get("recruit_attempts"),
            )

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,
        )

    def _handle_persuasion_failure(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        target: str,
        stage_tag: str,
        remaining_attempts: int
    ) -> StageResult:
        """설득 실패 처리"""
        log("mission", f"[PERSUASION] {target} → FAIL, keeping discovery target for retry")

        temp_data = state.setdefault("temp_data", {})

        # ✅ 피드백 beats 생성 (서비스 사용)
        feedback_dialogues = self._feedback_service.build_feedback_beats(state, target, False, scenario)

        # ✅ 전환 대사 추가 (서비스 사용) - 최대 시도 소진 시에만
        if remaining_attempts == 0:
            next_target = self._logic_service.select_next_target(state, exclude=[target])
            if next_target:
                transition = self._feedback_service.build_transition_line(
                    "fail",
                    self.CHARACTER_NAMES_KR.get(target, target),
                    self.CHARACTER_NAMES_KR.get(next_target)
                )
                if transition:
                    feedback_dialogues.append(transition)
            else:
                transition = self._feedback_service.build_transition_line(
                    "fail",
                    self.CHARACTER_NAMES_KR.get(target, target),
                    None
                )
                if transition:
                    feedback_dialogues.append(transition)

        feedback_speakers = sorted(set([target, "tanjiro", "narr"]))

        children_ctx = self._build_children_context(
            stage_tag=stage_tag,
            stage=stage,
            speaker_pool=feedback_speakers,
            beats=feedback_dialogues,
            mission_info={
                "target": target,
                "success": False,
                "attempts": state.get("recruit_attempts", {}).get(target, 0),
            }
        )

        stage_complete = False
        next_stage = None

        if remaining_attempts == 0:
            queue = temp_data.setdefault("mission_success_queue", [])
            queue.extend(feedback_dialogues)

            # ✅ 다음 타겟 선택 (서비스 사용)
            next_target = self._logic_service.select_next_target(state, exclude=[target])
            self._logic_service.deactivate_mission(state)

            if next_target:
                log("mission", f"[AUTO-SWITCH] Attempts exhausted for {target} → switching to {next_target}")
                temp_data["locked_mission_target"] = next_target
                state["mission_target"] = next_target
                temp_data["current_discovery_target"] = next_target
                state["mission"]["target"] = next_target
                state["mission"]["active"] = False

                rediscovery_ctx = self._build_rediscovery_context(
                    stage, scenario, next_target, preface=feedback_dialogues
                )
                return StageResult(children_ctx=rediscovery_ctx, stage_complete=False)

            log("mission", "[AUTO-SWITCH] All mission targets exhausted; finishing mission")
            stage_complete = True
            next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
            children_ctx.pop("fallback", None)
        else:
            log("codex_fix", "Mission still in progress", stage_tag=stage_tag, target=target)

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,
        )

    # ==================== Helper Methods ====================

    def _should_show_discovery(
        self,
        state: Dict[str, Any],
        user_input: str,
        target: str,
        mission_state: Dict[str, Any]
    ) -> bool:
        """Discovery 단계를 보여줄지 판단"""
        if mission_state.get("active") and mission_state.get("target") == target:
            return False

        current_discovery_target = state.get("temp_data", {}).get("current_discovery_target")
        if current_discovery_target == target:
            user_input_lower = user_input.lower()
            is_name_only = (
                user_input_lower in (target, target + "요", target + "를", target + "을") or
                len(user_input.strip()) <= 5
            )
            if not is_name_only:
                return False

        return True

    def _extract_speaker_pool_from_beats(
        self,
        beats: List[Dict[str, Any]],
        target: str
    ) -> List[str]:
        """Beats에서 speaker pool 추출"""
        speakers = set()
        for beat in beats:
            if isinstance(beat, dict):
                hints = beat.get("speaker_hint", [])
                if isinstance(hints, list):
                    speakers.update(str(h) for h in hints if h)
                speaker = beat.get("speaker")
                if speaker:
                    speakers.add(str(speaker))

        speakers.add("narr")
        speakers.add(target)
        return sorted(speakers)

    def _build_children_context(
        self,
        stage_tag: str,
        stage: Dict[str, Any],
        speaker_pool: List[str],
        beats: List[Dict[str, Any]],
        mission_info: Optional[Dict[str, Any]] = None,
        fallback: Optional[Dict[str, Any]] = None,
        prefetch: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Children context 생성"""
        ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": speaker_pool,
            "beats": beats,
            "atmosphere": stage.get("atmosphere"),
        }

        if mission_info:
            ctx["mission"] = mission_info

        if fallback:
            ctx["fallback"] = fallback

        if prefetch:
            ctx["prefetch_dialogues"] = prefetch

        return ctx

    def _build_rediscovery_context(
        self,
        stage: Dict[str, Any],
        scenario: Dict[str, Any],
        target: str,
        preface: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """재발견 context 생성"""
        discovery_beats = get_i18n_entries(scenario, f"{target}_scene", locale=self.locale)
        discovery_pool = self._extract_speaker_pool_from_beats(discovery_beats, target)

        ctx = self._build_children_context(
            stage_tag=stage.get("tag") or stage.get("id") or "mission",
            stage=stage,
            speaker_pool=discovery_pool,
            beats=self._to_dialogues(discovery_beats),
            mission_info={
                "target": target,
                "phase": "discovery",
            }
        )

        if preface:
            ctx["prefetch_dialogues"] = preface

        return ctx

    def _to_dialogues(self, beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Beats를 대화 형식으로 변환

        Note: DialogueFormatterService의 normalize_dialogues()와 유사하지만,
        mission_stage에서 사용하는 beats 형식에 최적화되어 있습니다.
        """
        dialogues = []
        for beat in beats:
            if isinstance(beat, dict):
                text = beat.get("text") or beat.get("goal") or ""
                if not text:
                    continue

                speaker = beat.get("speaker")
                if not speaker:
                    hints = beat.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]

                entry = dict(beat)
                entry["text"] = text
                entry["speaker"] = speaker or "narr"
                entry.setdefault("goal", beat.get("goal") or text)
                dialogues.append(entry)
            else:
                text = str(beat)
                dialogues.append({"text": text, "speaker": "narr", "goal": text})

        return dialogues


__all__ = ["MissionHandler"]
