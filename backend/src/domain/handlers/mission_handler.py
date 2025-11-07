"""
리팩터링 요약:
1. 타깃 선택 로직을 _determine_mission_target 메서드로 통합
2. 화자 풀 추출 로직을 _extract_speaker_pool_from_beats 메서드로 통합
3. 미션 상태 갱신을 _activate_mission / _deactivate_mission 메서드로 분리
4. 컨텍스트 생성 로직을 _build_children_context 메서드로 정리
5. 불필요한 재할당을 제거하고 명확한 이름을 사용
6. 인트로 처리 흐름을 단순화하고 중복을 제거
7. 일관된 코드 스타일과 가독성을 유지
8. IProgressionRepository를 사용하여 DatabaseManager 의존성 제거
"""

# ============================================================
# ⚔️ 미션 핸들러 — 동료 영입 스테이지 처리
# ============================================================
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.interfaces.repositories.progression_repository import IProgressionRepository

from src.infrastructure.shared.dependency_container import get_llm_provider as get_llm_client
from src.domain.services.orchestration.scene_tools import (
    get_i18n_entries,
    get_next_stage_tag,
    get_stage_type,
    get_speaker_pool,
)
from src.domain.services.generation.fallback_tools import trigger_fallback
from src.core.config.config_loader import get_config_loader
import logging
log = logging.getLogger(__name__)
# TODO: text_matcher 위치 확인 필요 # detect_mission_target

_PROMPTS = get_config_loader().get_prompts()
_MISSION_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("mission") or {})
_RECRUITMENT_PROMPT = (_MISSION_PROMPTS.get("recruitment_judge") or "").strip()
_RECRUITMENT_USER_TEMPLATE = (_MISSION_PROMPTS.get("recruitment_judge_user") or "").strip()
if not _RECRUITMENT_PROMPT:
    raise ValueError("MissionHandler recruitment_judge prompt missing in configs/prompts.yaml (llm_prompts.mission.recruitment_judge).")
if not _RECRUITMENT_USER_TEMPLATE:
    raise ValueError("MissionHandler recruitment_judge_user prompt missing in configs/prompts.yaml (llm_prompts.mission.recruitment_judge_user).")
from . import StageResult


class MissionHandler:
    """LLM 기반 동료 영입 미션 처리기"""

    MAX_ATTEMPTS = 3
    VALID_TARGETS = ("inosuke", "zenitsu")
    CHARACTER_NAMES_KR = {
        "inosuke": "이노스케",
        "zenitsu": "젠이츠",
        "tanjiro": "탄지로",
        "nezuko": "네즈코",
    }

    def __init__(
        self,
        locale: str = "ko",
        llm: Any = None,
        progression_repository: Optional['IProgressionRepository'] = None
    ):
        self.locale = locale
        self._llm = llm
        self._progression_repo = progression_repository

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

        intro_shown = temp_data.get("mission_intro_shown", False)
        if not intro_shown:
            return self._handle_intro(state, stage, scenario, user_input, stage_tag, speaker_pool)

        # 타겟 결정
        target = self._determine_mission_target(state, user_input, mission_state)

        # 타겟이 유효하지 않으면 폴백 또는 완료 처리
        if target not in self.VALID_TARGETS:
            return self._handle_invalid_target(state, stage, scenario, stage_tag, speaker_pool)

        if self._should_show_discovery(state, user_input, target, mission_state):
            return self._handle_discovery(state, stage, scenario, target, stage_tag, mission_state)

        return self._handle_persuasion(state, stage, scenario, target, stage_tag, mission_state)


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
        # 모든 미션이 완료된 경우
        if self._all_missions_resolved(state):
            return self._handle_mission_complete(state, stage, stage_tag, speaker_pool)

        temp_data = state.setdefault("temp_data", {})
        mission_intro_shown = temp_data.get("mission_intro_shown", False)

        # 단계 3 개선: 명확한 가이드 메시지 생성
        # - 사용자가 엉뚱한 말을 하면 탄지로가 명확히 안내
        # - "이노스케", "젠이츠" 구체적 이름 제시로 혼란 제거
        # - 부드러운 톤으로 게임 흐름 유지
        guide_message = {
            "speaker": "tanjiro",
            "text": (
                "지금은 동료를 찾는 데 집중해야 해. "
                "이노스케나 젠이츠를 찾아서 함께 싸우자고 설득해야 해. "
                "누구를 찾을지 말해줄래?"
            )
        }

        # 폴백 처리
        user_input = state.get("user_input", "")
        fallback_payload = trigger_fallback(state, stage, reason="invalid_target")

        # 단계 3 개선: 폴백 대화 구조 개선
        # - 가이드 메시지를 폴백 대화에 먼저 추가
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
        msg = self._generate_mission_complete_message(allies)

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

        self._deactivate_mission(state)

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

        self._activate_mission(state, target)
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
        self._activate_mission(state, target)
        self._increment_attempt(state, target)

        attempts_map = state.get("recruit_attempts", {})
        current_attempts = attempts_map.get(target, 0)
        remaining_attempts = max(0, self.MAX_ATTEMPTS - current_attempts)

        log(
            "mission",
            f"[ATTEMPT] {target} try={current_attempts}/{self.MAX_ATTEMPTS}",
            remaining=remaining_attempts,
        )

        success = self._evaluate_recruit_attempt_llm(state, target)
        self._update_recruit_result(state, target, success)

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
        self._deactivate_mission(state)

        log("mission", f"[PERSUASION] {target} → SUCCESS, discovery reset for next character")

        next_target = self._select_next_target(state, exclude=[target])
        feedback_dialogues = self._build_feedback_beats(state, target, True, scenario)
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

        stage_complete = self._all_missions_resolved(state)
        next_stage = None

        if stage_complete:
            queue = temp_data.setdefault("mission_success_queue", [])
            queue.extend(feedback_dialogues)
            self._deactivate_mission(state)
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
        feedback_dialogues = self._build_feedback_beats(state, target, False, scenario)
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
            next_target = self._select_next_target(state, exclude=[target])
            self._deactivate_mission(state)

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


    def _determine_mission_target(
        self,
        state: Dict[str, Any],
        user_input: str,
        mission_state: Dict[str, Any]
    ) -> Optional[str]:
        """미션 타겟 결정 (중복 로직 통합)"""
        temp_data = state.setdefault("temp_data", {})
        locked_target = temp_data.get("locked_mission_target")
        detected_target = detect_mission_target(user_input)

        # 이미 활성화된 미션이 있으면 해당 타겟 사용
        if mission_state.get("active") and mission_state.get("target") in self.VALID_TARGETS:
            target = mission_state["target"]
            temp_data["locked_mission_target"] = target
            state["mission_target"] = target
            return target

        if locked_target in self.VALID_TARGETS:
            mission_state["target"] = locked_target
            return locked_target

        # 사용자가 명시적으로 타겟을 지정했으면 사용
        if detected_target in self.VALID_TARGETS:
            temp_data["locked_mission_target"] = detected_target
            state["mission_target"] = detected_target
            mission_state["target"] = detected_target
            return detected_target

        allies = state.get("allies_recruited", [])
        attempts = state.get("recruit_attempts", {})

        for candidate in self.VALID_TARGETS:
            if candidate not in allies and attempts.get(candidate, 0) < self.MAX_ATTEMPTS:
                temp_data["locked_mission_target"] = candidate
                state["mission_target"] = candidate
                mission_state["target"] = candidate
                log("mission", f"[AUTO-TARGET] Selecting {candidate}")
                return candidate

        return None

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
            # 사용자 입력이 이름만 있는 경우는 로 간주하지 않음
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
        """Beats에서 speaker pool 추출 (중복 로직 통합)"""
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
        """Children context 생성 (중복 로직 통합)"""
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

    def _activate_mission(self, state: Dict[str, Any], target: str) -> None:
        """미션 활성화"""
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = True
        mission_state["target"] = target
        temp_data["locked_mission_target"] = target
        state["mission_target"] = target

        log("mission", f"🟢 Mission activated for {target}")

    def _deactivate_mission(self, state: Dict[str, Any]) -> None:
        """미션 비활성화"""
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = False
        mission_state["target"] = None
        temp_data.pop("locked_mission_target", None)
        state["mission_target"] = None

    def _increment_attempt(self, state: Dict[str, Any], character: str) -> None:
        """시도 횟수 증가"""
        attempts = state.setdefault("recruit_attempts", {})
        attempts[character] = attempts.get(character, 0) + 1

        order = state.setdefault("recruit_order", [])
        if character not in order:
            order.append(character)

    def _select_next_target(
        self,
        state: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> Optional[str]:
        """다음 타겟 선택"""
        exclude = set(exclude or [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        for candidate in self.VALID_TARGETS:
            if candidate in exclude or candidate in allies:
                continue
            if attempts.get(candidate, 0) < self.MAX_ATTEMPTS:
                return candidate

        return None

    def _evaluate_recruit_attempt_llm(self, state: Dict[str, Any], target: str) -> bool:
        """LLM을 사용한 설득 시도 평가"""
        client = self._llm or get_llm_client()
        user_text = state.get("user_input", "")

        system_prompt = _RECRUITMENT_PROMPT
        user_prompt = _RECRUITMENT_USER_TEMPLATE.format(
            target=target,
            user_text=user_text
        )
        try:
            get_setting = getattr(client, "get_agent_setting", None)
            if callable(get_setting):
                temperature = get_setting("mission", "temperature", 0.0)
                max_tokens = get_setting("mission", "max_tokens", 5)
            else:
                temperature = 0.0
                max_tokens = 5

            call_kwargs = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if callable(get_setting):
                call_kwargs["agent"] = "mission"

            result = client.call(**call_kwargs)
            decision = "true" in (result or "").lower()
            log("mission", f"[LLM DECISION] target={target} → {'SUCCESS' if decision else 'FAIL'}")
            return decision
        except Exception as exc:
            log("mission", f"[LLM ERROR] fallback heuristic used: {exc}", level=40)
            return self._heuristic_fallback(user_text, target)

    def _heuristic_fallback(self, text: str, target: str) -> bool:
        """휴리스틱 기반 fallback 판정"""
        lowered = (text or "").lower()
        if target == "zenitsu":
            return any(keyword in lowered for keyword in ["네즈코", "사랑", "지켜", "위험"])
        if target == "inosuke":
            return any(keyword in lowered for keyword in ["겁쟁", "약하", "싸우", "도전", "멧돼"])
        return False

    def _update_recruit_result(self, state: Dict[str, Any], character: str, success: bool) -> None:
        """설득 결과 업데이트"""
        attempts = state.get("recruit_attempts", {}).get(character, 0)
        remaining = max(0, self.MAX_ATTEMPTS - attempts)

        if success:
            allies = state.setdefault("allies_recruited", [])
            if character not in allies:
                allies.append(character)

            fails = state.get("recruit_failures", [])
            if character in fails:
                fails.remove(character)
        else:
            fails = state.setdefault("recruit_failures", [])
            if character not in fails:
                fails.append(character)

        state.setdefault("temp_data", {})["last_mission_status"] = {
            "target": character,
            "success": success,
            "remaining": remaining,
        }

        # 🎮 미션 기록 자동 저장 (Repository Pattern)
        if self._progression_repo:
            try:
                session_id = state.get("session_id")
                turn_count = state.get("turn_count", 0)

                if session_id:
                    # 미션 기록 저장
                    mission_id = self._progression_repo.save_mission_record(
                        session_id=session_id,
                        mission_type="recruit",
                        target_character=character,
                        attempt_count=attempts,
                        success=success
                    )
                    if mission_id:
                        log("mission", f"🎮 Mission record saved: {character} ({'SUCCESS' if success else 'FAIL'}, attempt {attempts})")

                    # 🎉 게임 이벤트 저장: 캐릭터 합류 성공
                    if success:
                        event_id = self._progression_repo.save_game_event(
                            session_id=session_id,
                            turn_number=turn_count,
                            event_type="character_recruited",
                            event_data={
                                "character": character,
                                "character_display": self.CHARACTER_NAMES_KR.get(character, character),
                                "mission_type": "recruit",
                                "attempts": attempts
                            }
                        )
                        if event_id:
                            log("mission", f"🎉 Game event saved: character_recruited ({character})")
            except Exception as e:
                log("mission", f"⚠️ Failed to save mission/game records: {e}", level=40)

        log(
            "mission",
            f"[RESULT] {character} → {'SUCCESS' if success else 'FAIL'}",
            attempts=state.get("recruit_attempts"),
            allies=state.get("allies_recruited"),
            failures=state.get("recruit_failures"),
        )

    def _build_feedback_beats(
        self,
        state: Dict[str, Any],
        character: str,
        success: bool,
        scenario: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """피드백 beats 생성"""
        char_display = self.CHARACTER_NAMES_KR.get(character.lower(), character.capitalize())

        temp_status = state.get("temp_data", {}).get("last_mission_status") or {}
        attempts_map = state.get("recruit_attempts", {})
        current_attempt = attempts_map.get(character, 0)
        remaining = temp_status.get("remaining")
        if remaining is None:
            remaining = max(0, self.MAX_ATTEMPTS - current_attempt)

        attempt_ratio = f"{current_attempt}/{self.MAX_ATTEMPTS}"

        if success:
            sys_text = f"{char_display} 🎉 설득 성공! 🎉 ({attempt_ratio})"
            fx = "ui_confirm|success_chime"
        else:
            remaining_note = f" 남은 시도 {remaining}회" if remaining is not None else ""
            sys_text = f"⏰ {char_display} 설득 실패... ({attempt_ratio}){remaining_note}"
            fx = "ui_alert|heartbeat_slow"

        sys_entry = {
            "text": sys_text,
            "goal": sys_text,
            "speaker": "system",
            "fx": fx,
        }

        feedback_key = (
            f"beats_feedback_success_{character}"
            if success
            else f"beats_feedback_fail_{character}"
        )

        if not success and remaining == 0:
            alt_key = f"beats_feedback_fail_{character}_end"
            alt_beats = get_i18n_entries(scenario, alt_key, locale=self.locale)
            if alt_beats:
                feedback_key = alt_key

        feedback_beats = self._to_dialogues(
            get_i18n_entries(scenario, feedback_key, locale=self.locale)
        )

        dialogues = list(feedback_beats)
        dialogues.append(sys_entry)

        # 최대 시도 소진 시 추가 메시지
        if not success and remaining == 0:
            exhaustion = {
                "speaker": "system",
                "text": "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
                "goal": "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
            }
            dialogues.append(exhaustion)
            log("codex_fix", "Mission attempts exhausted", character=character)

        # 전환 대사 추가: 캐릭터 미션이 완전히 끝났을 때만 출력
        final_transition_needed = success or (not success and remaining == 0)
        if final_transition_needed:
            next_target_raw = self._select_next_target(state, exclude=[character])
            next_target_display = (
                self.CHARACTER_NAMES_KR.get(next_target_raw)
                if next_target_raw
                else None
            )

            transition_line = self._generate_transition_line(
                "success" if success else "fail",
                char_display,
                next_target_display,
            )
            if transition_line:
                dialogues.append(transition_line)

        return dialogues

    def _generate_transition_line(
        self,
        mission_result: str,
        completed_ally: str,
        next_target: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """전환 대사 생성"""
        if mission_result not in {"success", "fail"}:
            return None

        if next_target:
            if mission_result == "success":
                text = f"탄지로: {completed_ally}를 데려오는 데 성공했어! 이제 {next_target}를 찾으러 가자."
            else:
                text = f"탄지로: {completed_ally}를 설득하지 못했어... 그래도 포기할 순 없어. 이번엔 {next_target}를 찾아보자."
        else:
            if mission_result == "success":
                text = f"탄지로: {completed_ally}를 데려오는 데 성공했어! 이제 전장으로 돌아가자."
            else:
                text = f"탄지로: {completed_ally}를 설득하지 못했어... 그래도 포기할 순 없어. 다른 길을 찾아보자."

        log("mission", text)
        return {
            "speaker": "tanjiro",
            "text": text,
            "goal": text,
        }

    def _to_dialogues(self, beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Beats를 대화 형식으로 변환"""
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

    def _all_missions_resolved(self, state: Dict[str, Any]) -> bool:
        """모든 미션이 완료되었는지 확인"""
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        for character in self.VALID_TARGETS:
            if character in allies:
                continue
            if attempts.get(character, 0) < self.MAX_ATTEMPTS:
                return False

        return True

    def _generate_mission_complete_message(self, allies: List[str]) -> str:
        """미션 완료 메시지 생성"""
        if not allies:
            return "동료를 더 설득할 시간이 없습니다. 곧바로 전장으로 돌아가야 해요!"

        converted_names = [self.CHARACTER_NAMES_KR.get(name, name) for name in allies]

        if len(converted_names) == 1:
            ally_text = converted_names[0]
        elif len(converted_names) == 2:
            ally_text = f"{converted_names[0]}와 {converted_names[1]}"
        else:
            ally_text = ", ".join(converted_names[:-1]) + f" 그리고 {converted_names[-1]}"

        return f"{ally_text}가 모두 합류했어요! 이제 바로 전장으로 돌아가 렌고쿠 님을 도와요!"
