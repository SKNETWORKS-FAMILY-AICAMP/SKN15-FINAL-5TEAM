from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.llm_client import get_llm_client

from ..scene_tools import (
    get_i18n_entries,
    get_next_stage_tag,
    get_stage_type,
    get_speaker_pool,
)
from ..utils.fallback import trigger_fallback
from ..utils.logger import log
from ..utils.text_matcher import detect_mission_target
from . import StageResult


class MissionHandler:
    """LLM 기반 동료 영입 미션 처리기"""

    MAX_ATTEMPTS = 3

    def __init__(self, locale: str = "ko", llm: Any = None):
        self.locale = locale
        self._llm = llm

    def handle(self, state: Dict[str, Any], stage: Dict[str, Any], scenario: Dict[str, Any]) -> StageResult:
        stage_tag = stage.get("tag") or stage.get("id") or "mission"
        speaker_pool = get_speaker_pool(stage, stage.get("speaker_pool", []))
        user_input = (state.get("user_input") or "").strip()
        stage_turn = int(state.get("stage_turn", 0) or 0)
        temp_data = state.setdefault("temp_data", {})
        intro_flag = temp_data.get("mission_intro_shown", False)
        locked_target = temp_data.get("locked_mission_target")

        target = detect_mission_target(user_input)
        mission_state = state.setdefault("mission", {})
        mission_active = bool(mission_state.get("active"))

        if not intro_flag:
            temp_data["mission_intro_shown"] = True
            if target in ("inosuke", "zenitsu") and not locked_target:
                temp_data["locked_mission_target"] = target
                state["mission_target"] = target
            intro_key = stage.get("intro_i18n") or "beats_smell"
            intro_beats = self._to_dialogues(get_i18n_entries(scenario, intro_key, locale=self.locale))
            log("mission", f"[INTRO] Showing mission intro via {intro_key}")
            children_ctx = {
                "stage_tag": stage_tag,
                "stage_type": get_stage_type(stage),
                "speaker_pool": speaker_pool,
                "beats": intro_beats,
                "atmosphere": stage.get("atmosphere"),
                "mission": {
                    "phase": "intro",
                },
            }
            return StageResult(children_ctx=children_ctx, stage_complete=False)

        # 🔧 타겟이 없으면 자동으로 다음 캐릭터 선택 (순서: inosuke → zenitsu)
        if locked_target in ("inosuke", "zenitsu"):
            target = locked_target
            mission_state["target"] = locked_target

        if target in ("inosuke", "zenitsu") and not locked_target:
            temp_data["locked_mission_target"] = target
            state["mission_target"] = target

        if target not in ("inosuke", "zenitsu") and intro_flag and not locked_target:
            allies = state.get("allies_recruited", [])
            attempts = state.get("recruit_attempts", {})

            # inosuke를 아직 설득 안 했으면 inosuke
            if "inosuke" not in allies and attempts.get("inosuke", 0) < self.MAX_ATTEMPTS:
                target = "inosuke"
                log("mission", "[AUTO-TARGET] Selecting inosuke (first priority)")
            # inosuke 완료했으면 zenitsu
            elif "zenitsu" not in allies and attempts.get("zenitsu", 0) < self.MAX_ATTEMPTS:
                target = "zenitsu"
                log("mission", "[AUTO-TARGET] Selecting zenitsu (inosuke already handled)")
            if target in ("inosuke", "zenitsu"):
                temp_data["locked_mission_target"] = target
                state["mission_target"] = target

        skip_discovery = False
        active_target = mission_state.get("target")
        if mission_active and active_target in ("inosuke", "zenitsu"):
            target = active_target
            mission_state["target"] = active_target
            temp_data["locked_mission_target"] = active_target
            state["mission_target"] = active_target
            skip_discovery = True
            attempts_snapshot = state.get("recruit_attempts", {})
            log("mission", f"🔁 Continuing active mission: {target}", attempts=attempts_snapshot.get(target, 0))
        elif target in ("inosuke", "zenitsu"):
            mission_state["target"] = target

        # 그래도 타겟이 없으면 fallback
        if target not in ("inosuke", "zenitsu"):
            if not intro_flag and stage_turn == 0:
                intro_key = stage.get("intro_i18n") or "beats_smell"
                intro_beats = self._to_dialogues(get_i18n_entries(scenario, intro_key, locale=self.locale))
                children_ctx = {
                    "stage_tag": stage_tag,
                    "stage_type": get_stage_type(stage),
                    "speaker_pool": speaker_pool,
                    "beats": intro_beats,
                    "atmosphere": stage.get("atmosphere"),
                    "mission": {"phase": "intro"},
                }
                temp_data["mission_intro_shown"] = True
                return StageResult(children_ctx=children_ctx, stage_complete=False)

            if self._all_missions_resolved(state):
                allies = state.get("allies_recruited", [])
                name_map = {
                    "inosuke": "이노스케",
                    "zenitsu": "젠이츠",
                    "tanjiro": "탄지로",
                    "nezuko": "네즈코",
                }

                def _display(names):
                    converted = [name_map.get(name, name) for name in names]
                    if not converted:
                        return ""
                    if len(converted) == 1:
                        return converted[0]
                    if len(converted) == 2:
                        return f"{converted[0]}와 {converted[1]}"
                    return ", ".join(converted[:-1]) + f" 그리고 {converted[-1]}"

                msg = (
                    f"{_display(allies)}가 모두 합류했어요! 이제 바로 전장으로 돌아가 렌고쿠 님을 도와요!"
                    if allies else "동료를 더 설득할 시간이 없습니다. 곧바로 전장으로 돌아가야 해요!"
                )
                wrap_up_dialogues = [
                    {"speaker": "tanjiro", "text": msg, "fx": "urgent_heartbeat|flame_flash"},
                ]
                queue = state.setdefault("temp_data", {}).setdefault("mission_success_queue", [])
                queue.extend(wrap_up_dialogues)
                temp_data.pop("locked_mission_target", None)
                state["mission_target"] = None
                mission_state["active"] = False
                mission_state["target"] = None
                children_ctx = {
                    "stage_tag": stage_tag,
                    "stage_type": get_stage_type(stage),
                    "speaker_pool": speaker_pool or ["tanjiro", "narr"],
                    "beats": [],
                    "atmosphere": stage.get("atmosphere"),
                    "mission": {"phase": "complete"},
                }
                next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
                log("mission", f"[AUTO-COMPLETE] all allies ready → {next_stage}", allies=allies)
                return StageResult(children_ctx=children_ctx, stage_complete=True, next_stage=next_stage)

            fallback_payload = trigger_fallback(state, stage, reason="invalid_target")
            beats_smell = self._to_dialogues(
                get_i18n_entries(scenario, "beats_smell", locale=self.locale)
            )
            fallback_dialogues = fallback_payload.setdefault("dialogues", [])
            fallback_dialogues.extend(beats_smell)
            children_ctx = {
                "stage_tag": stage_tag,
                "stage_type": get_stage_type(stage),
                "speaker_pool": speaker_pool,
                "beats": [],
                "fallback": {"dialogues": fallback_dialogues},
                "atmosphere": stage.get("atmosphere"),
            }
            log("mission", f"[FALLBACK] ambiguous target on {stage_tag}", user_input=user_input)
            return StageResult(children_ctx=children_ctx, fallback_payload=fallback_payload)

        # 🔧 단계 구분: 찾기 (discovery) vs 설득 (persuasion)
        current_discovery_target = state.get("temp_data", {}).get("current_discovery_target")

        # 사용자 입력이 이름만 있으면 discovery로 간주 (설득 시도 아님)
        user_input_lower = user_input.lower()
        is_name_only = (
            user_input_lower in (target, target + "요", target + "를", target + "을") or
            len(user_input.strip()) <= 5  # 매우 짧은 입력은 이름만 언급한 것으로 간주
        )

        if (current_discovery_target != target or is_name_only) and not skip_discovery:
            # 새로운 캐릭터를 찾으러 가는 경우 → discovery scene 표시
            state.setdefault("temp_data", {})["current_discovery_target"] = target
            log("mission", f"[DISCOVERY] Finding {target}")

            # {character}_scene beats 로드
            discovery_beats = get_i18n_entries(scenario, f"{target}_scene", locale=self.locale)

            # discovery beats에서 speaker_pool 추출 (speaker_hint 사용)
            discovery_speakers = set()
            for beat in discovery_beats:
                if isinstance(beat, dict):
                    hints = beat.get("speaker_hint", [])
                    if isinstance(hints, list):
                        discovery_speakers.update(str(h) for h in hints if h)
                    speaker = beat.get("speaker")
                    if speaker:
                        discovery_speakers.add(str(speaker))

            # narr는 항상 포함, target도 포함
            discovery_speakers.add("narr")
            discovery_speakers.add(target)
            discovery_pool = sorted(discovery_speakers)

            log("mission", f"[DISCOVERY] Speaker pool for {target}_scene: {discovery_pool}")

            children_ctx = {
                "stage_tag": stage_tag,
                "stage_type": get_stage_type(stage),
                "speaker_pool": discovery_pool,
                "beats": self._to_dialogues(discovery_beats),
                "atmosphere": stage.get("atmosphere"),
                "mission": {
                    "target": target,
                    "phase": "discovery",
                },
            }
            # discovery 단계에서는 stage_complete=False
            mission_state["active"] = True
            mission_state["target"] = target
            log("mission", f"🟢 Mission activated for {target}")
            return StageResult(children_ctx=children_ctx, stage_complete=False)

        # 이미 찾은 캐릭터에 대한 설득 시도
        mission_state["active"] = True
        mission_state["target"] = target
        self._increment_attempt(state, target)
        attempts_snapshot = state.get("recruit_attempts", {})
        current_attempts = attempts_snapshot.get(target, 0)
        remaining_attempts = max(0, self.MAX_ATTEMPTS - current_attempts)
        log(
            "mission",
            f"[ATTEMPT] {target} try={current_attempts}/{self.MAX_ATTEMPTS}",
            remaining=remaining_attempts,
        )
        success = self._evaluate_recruit_attempt_llm(state, target)
        self._update_recruit_result(state, target, success)

        # 🔥 설득 성공 시에만 discovery 리셋 (다음 캐릭터 찾기 가능)
        # 실패 시에는 리셋하지 않음 (같은 캐릭터 재시도)
        if success:
            state.setdefault("temp_data", {})["current_discovery_target"] = None
            temp_data["locked_mission_target"] = None
            state["mission_target"] = None
            mission_state["active"] = False
            mission_state["target"] = None
            log("mission", f"[PERSUASION] {target} → SUCCESS, discovery reset for next character")
        else:
            log("mission", f"[PERSUASION] {target} → FAIL, keeping discovery target for retry")

        next_target_after_success = None
        if success:
            next_target_after_success = self._select_next_target(state, exclude=[target])

        feedback_dialogues = self._build_feedback_beats(state, target, success, scenario)

        # 🔥 Feedback speaker_pool: 현재 타겟 + tanjiro + narr (다른 캐릭터 제외)
        feedback_speakers = sorted(set([target, "tanjiro", "narr"]))
        system_prefetch = [
            dict(entry)
            for entry in feedback_dialogues
            if isinstance(entry, dict) and str(entry.get("speaker", "")).lower() == "system"
        ]

        if success and next_target_after_success:
            log("mission", f"[AUTO-SWITCH] {target} succeeded → moving to {next_target_after_success}")
            temp_data["locked_mission_target"] = next_target_after_success
            temp_data["current_discovery_target"] = next_target_after_success
            state["mission_target"] = next_target_after_success
            mission_state["target"] = next_target_after_success
            mission_state["active"] = False
            rediscovery = self._rediscovery_context(stage, scenario, next_target_after_success, preface=feedback_dialogues)
            return StageResult(children_ctx=rediscovery, stage_complete=False)

        children_ctx = {
            "stage_tag": stage_tag,
            "stage_type": get_stage_type(stage),
            "speaker_pool": feedback_speakers,  # 타겟 캐릭터에 맞는 제한된 pool
            "beats": feedback_dialogues,
            "atmosphere": stage.get("atmosphere"),
            "mission": {
                "target": target,
                "success": success,
                "attempts": state.get("recruit_attempts", {}).get(target, 0),
            },
        }
        if not feedback_dialogues:
            children_ctx["fallback"] = {"dialogues": feedback_dialogues}
        if system_prefetch:
            prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
            prefetch_list.extend(system_prefetch)

        attempts_snapshot = state.get("recruit_attempts", {})
        current_attempts = attempts_snapshot.get(target, 0)
        remaining = max(0, self.MAX_ATTEMPTS - current_attempts)

        stage_complete = self._all_missions_resolved(state)
        next_stage = None
        if stage_complete:
            queue = state.setdefault("temp_data", {}).setdefault("mission_success_queue", [])
            queue.extend(feedback_dialogues)
            temp_data.pop("locked_mission_target", None)
            state["mission_target"] = None
            mission_state["active"] = False
            mission_state["target"] = None
            children_ctx.pop("fallback", None)
            next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
            log(
                "mission",
                f"[RESOLVED] stage={stage_tag}, next={next_stage}",
                recruited=state.get("allies_recruited"),
                attempts=state.get("recruit_attempts"),
            )
        else:
            if remaining == 0:
                queue = state.setdefault("temp_data", {}).setdefault("mission_success_queue", [])
                queue.extend(feedback_dialogues)
                next_target = self._select_next_target(state, exclude=[target])
                temp_data["locked_mission_target"] = None
                state["mission_target"] = None
                mission_state["active"] = False
                mission_state["target"] = None
                if next_target:
                    log("mission", f"[AUTO-SWITCH] Attempts exhausted for {target} → switching to {next_target}")
                    temp_data["locked_mission_target"] = next_target
                    state["mission_target"] = next_target
                    temp_data["current_discovery_target"] = next_target
                    mission_state["target"] = next_target
                    mission_state["active"] = False
                    rediscovery = self._rediscovery_context(stage, scenario, next_target, preface=feedback_dialogues)
                    return StageResult(children_ctx=rediscovery, stage_complete=False)

                log("mission", "[AUTO-SWITCH] All mission targets exhausted; finishing mission")
                stage_complete = True
                next_stage = stage.get("next") or get_next_stage_tag(stage) or "RETURN_TO_FRONT"
                children_ctx.pop("fallback", None)
                return StageResult(
                    children_ctx=children_ctx,
                    stage_complete=stage_complete,
                    next_stage=next_stage,
                )

            log(
                "codex_fix",
                "Mission still in progress",
                stage_tag=stage_tag,
                target=target,
            )

        return StageResult(
            children_ctx=children_ctx,
            stage_complete=stage_complete,
            next_stage=next_stage,
        )

    # ------------------------------------------------------------------ helpers
    def _increment_attempt(self, state: Dict[str, Any], character: str) -> None:
        attempts = state.setdefault("recruit_attempts", {})
        attempts[character] = attempts.get(character, 0) + 1

        order = state.setdefault("recruit_order", [])
        if character not in order:
            order.append(character)

    def _select_next_target(self, state: Dict[str, Any], exclude: Optional[List[str]] = None) -> Optional[str]:
        exclude = set(exclude or [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])
        candidates = []
        if "inosuke" not in exclude:
            candidates.append("inosuke")
        if "zenitsu" not in exclude:
            candidates.append("zenitsu")
        for character in candidates:
            if character in allies:
                continue
            if attempts.get(character, 0) < self.MAX_ATTEMPTS:
                return character
        return None

    def _rediscovery_context(self, stage: Dict[str, Any], scenario: Dict[str, Any], target: str, *, preface: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        discovery_beats = get_i18n_entries(scenario, f"{target}_scene", locale=self.locale)
        discovery_speakers = set()
        for beat in discovery_beats:
            if isinstance(beat, dict):
                hints = beat.get("speaker_hint", [])
                if isinstance(hints, list):
                    discovery_speakers.update(str(h) for h in hints if h)
                speaker = beat.get("speaker")
                if speaker:
                    discovery_speakers.add(str(speaker))

        discovery_speakers.add("narr")
        discovery_speakers.add(target)
        discovery_pool = sorted(discovery_speakers)
        ctx = {
            "stage_tag": stage.get("tag") or stage.get("id") or "mission",
            "stage_type": get_stage_type(stage),
            "speaker_pool": discovery_pool,
            "beats": self._to_dialogues(discovery_beats),
            "atmosphere": stage.get("atmosphere"),
            "mission": {
                "target": target,
                "phase": "discovery",
            },
        }
        if preface:
            ctx["prefetch_dialogues"] = preface
        return ctx

# 임베딩, 키워드 매핑보다 llm 붙임
    def _evaluate_recruit_attempt_llm(self, state: Dict[str, Any], target: str) -> bool:
        client = self._llm or get_llm_client()
        user_text = state.get("user_input", "")
        system_prompt = (
            "You are a mission adjudicator for a Demon Slayer interactive story. "
            "Return only True or False to indicate whether the recruitment attempt succeeded."
        )
        user_prompt = f"""
현재 캐릭터는 '{target}'을 설득하려고 한다.

플레이어의 대사: "{user_text}"

판정 기준:
- 젠이츠(Zenitsu)는 '네즈코', '사랑', '지켜야 해', '위험해' 같은 감정적 키워드나 설득 문맥이 포함되면 성공.
- 이노스케(Inosuke)는 '겁쟁이', '약하다', '싸우자', '도전해' 같은 도발성 발화가 있으면 성공.
- 그 외엔 실패.

성공이면 True, 실패면 False 만 출력해.
"""
        try:
            result = client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0,
                max_tokens=5,
            )
            decision = "true" in (result or "").lower()
            log("mission", f"[LLM DECISION] target={target} → {'SUCCESS' if decision else 'FAIL'}")
            return decision
        except Exception as exc:  # pragma: no cover - defensive
            log("mission", f"[LLM ERROR] fallback heuristic used: {exc}", level=40)
            return self._heuristic_fallback(user_text, target)

    def _heuristic_fallback(self, text: str, target: str) -> bool:
        lowered = (text or "").lower()
        if target == "zenitsu":
            return any(keyword in lowered for keyword in ["네즈코", "사랑", "지켜", "위험"])
        if target == "inosuke":
            return any(keyword in lowered for keyword in ["겁쟁", "약하", "싸우", "도전", "멧돼"])
        return False

    def _update_recruit_result(self, state: Dict[str, Any], character: str, success: bool) -> None:
        attempts = state.get("recruit_attempts", {}).get(character, 0)
        remaining = max(0, self.MAX_ATTEMPTS - attempts)

        if success:
            allies = state.setdefault("allies_recruited", [])
            if character not in allies:
                allies.append(character)
            # 🔥 SUCCESS 시 failures에서 제거 (이전에 실패했더라도)
            fails = state.get("recruit_failures", [])
            if character in fails:
                fails.remove(character)
        else:
            fails = state.setdefault("recruit_failures", [])
            if character not in fails:
                fails.append(character)

        sys_text = (
            f"{character} 설득 성공!"
            if success
            else f"{character} 설득 실패... 남은 시도 {remaining}회"
        )
        state.setdefault("temp_data", {})["last_mission_status"] = {
            "target": character,
            "success": success,
            "remaining": remaining,
        }
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
        # 캐릭터 이름 한글 매핑
        char_names = {
            "inosuke": "이노스케",
            "zenitsu": "젠이츠",
        }
        char_display = char_names.get(character.lower(), character.capitalize())

        temp_status = state.get("temp_data", {}).get("last_mission_status") or {}
        attempts_map = state.get("recruit_attempts", {})
        current_attempt = attempts_map.get(character, 0)
        max_attempts = self.MAX_ATTEMPTS
        remaining = temp_status.get("remaining")
        if remaining is None:
            remaining = max(0, max_attempts - current_attempt)
        attempt_ratio = f"{current_attempt}/{max_attempts}" if max_attempts else str(current_attempt)
        if success:
            sys_text = f"{char_display} 🎉 설득 성공! 🎉 ({attempt_ratio})"
        else:
            suffix = f" ({attempt_ratio})"
            remaining_note = f" 남은 시도 {remaining}회" if remaining is not None else ""
            sys_text = f"⏰ {char_display} 설득 실패...{suffix}{remaining_note}"
        sys_entry: Dict[str, Any] = {
            "text": (
                sys_text
            ),
            "goal": sys_text,
            "speaker": "system",
            "fx": "ui_confirm|success_chime" if success else "ui_alert|heartbeat_slow",
        }

        feedback_key = (
            f"beats_feedback_success_{character}"
            if success
            else f"beats_feedback_fail_{character}"
        )
        if not success and remaining is not None and remaining == 0:
            alt_key = f"beats_feedback_fail_{character}_end"
            alt_beats = get_i18n_entries(scenario, alt_key, locale=self.locale)
            if alt_beats:
                feedback_key = alt_key
        feedback_beats = self._to_dialogues(
            get_i18n_entries(scenario, feedback_key, locale=self.locale)
        )
        dialogues: List[Dict[str, Any]] = []
        dialogues.extend(feedback_beats)

        dialogues.append(sys_entry)

        # 🔥 최대 시도 소진 시에만 추가 메시지 표시 (sys_entry에 이미 "남은 시도 X회" 포함됨)
        if not success and remaining is not None and remaining == 0:
            exhaustion_text = "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다."
            exhaustion = {
                "speaker": "system",
                "text": exhaustion_text,
                "goal": exhaustion_text,
            }
            dialogues.append(exhaustion)
            log("codex_fix", "Mission attempts exhausted", character=character)
        return dialogues

    def _to_dialogues(self, beats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dialogues: List[Dict[str, Any]] = []
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
                # fx already present if existed; ensure no unexpected keys removed
                dialogues.append(entry)
            else:
                text = str(beat)
                dialogues.append({"text": text, "speaker": "narr", "goal": text})
        return dialogues

    def _all_missions_resolved(self, state: Dict[str, Any]) -> bool:
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])
        for character in ("inosuke", "zenitsu"):
            if character in allies:
                continue
            if attempts.get(character, 0) >= self.MAX_ATTEMPTS:
                continue
            return False
        return True
