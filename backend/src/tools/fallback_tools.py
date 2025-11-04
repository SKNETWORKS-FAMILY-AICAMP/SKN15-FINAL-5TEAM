# ============================================================
# 🛡️ Fallback Tools — Atmosphere 기반 오프토픽 제한 정책
# ============================================================
# GuardrailAgent의 차단 구조(system_blocked, blocked_until)를 재사용하며,
# scene의 atmosphere 값을 **직접** 허용 횟수로 사용합니다.
#
# [정책 담당 모듈]
# - atmosphere 값 = 허용 횟수 (0-3)
# - 경고 → 차단 흐름 관리
# - GuardrailAgent 연동 구조 유지
#
# [MOB 캐릭터 처리]
# - fallback_tools.py에서는 mob 로직을 포함하지 않습니다.
# - mob은 별도의 연출 레이어(children_agent 등)에서 처리합니다.
#
# atmosphere 값 = 허용 횟수:
#   0 (긴급/전투) → 0회 허용
#   1 (긴장)     → 1회 허용
#   2 (평온)     → 2회 허용
#   3 (일반)     → 3회 허용
#
# 차단 흐름:
#   - count ≤ limit: LLM 대사 생성
#   - count == limit + 1: 경고 (⚠️)
#   - count ≥ limit + 2: 10분 차단 (⛔️)
# ============================================================

from __future__ import annotations

import time
import random
import re
from typing import Dict, Any, Optional, List

from src.utils.llm_client import get_llm_client
from src.utils.config_loader import get_config_loader
from src.tools.scene_tools import get_stage_atmosphere
from src.config.constants import FALLBACK_ALLOW_NORMAL
from src.utils.logger import log
from src.core.scene_dialogue_tools import load_tone_profiles


# ============================================================
# 🧠 FallbackManager 클래스
# ============================================================
class FallbackManager:
    """
    Atmosphere 기반 Off-topic 처리 관리자 (정책 담당)

    - GuardrailAgent의 차단 구조 재사용 (system_blocked, blocked_until)
    - LLM 기반 캐릭터 대사 생성
    - speaker는 speaker_pool에서만 선택 (mob 제외)
    - atmosphere 값을 직접 허용 횟수로 사용
    - scene_tools.get_stage_atmosphere() 활용하여 표시 변환
    """

    def __init__(self):
        """초기화"""
        cfg = get_config_loader()
        self._llm = get_llm_client()
        self._prompts = cfg.get_prompts().get("llm_prompts", {}).get("fallback", {})
        self._check_templates()

    def _check_templates(self):
        """필수 프롬프트 템플릿 확인"""
        required = ["off_topic_base", "off_topic_user", "urgent_off_topic_base", "urgent_off_topic_user"]
        for key in required:
            if not self._prompts.get(key):
                log("fallback", f"⚠️ Missing prompt template: {key}")

    # ============================================================
    # 🔹 메인 처리 함수 — Atmosphere 기반 오프토픽 제한 정책
    # ============================================================
    def handle_off_topic(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Off-topic 입력 처리 (Atmosphere 값 = 허용 횟수)

        Returns:
            {
                "should_block": bool,
                "remaining_count": int,
                "message": str,
                "speaker": str,
                "action": "allow" | "warning" | "block",
                "dialogue": {"speaker": str, "text": str} | None,
                "new_count": int,
            }
        """
        # ✅ 차단 상태 확인
        if self._is_currently_blocked(state):
            return self._enforce_block(state)

        # ✅ 현재 스테이지 데이터 가져오기
        stage_data = self._get_stage_data(state)
        atmosphere_value = stage_data.get("atmosphere")

        # 🔹 atmosphere 값을 직접 limit으로 사용 (0-3)
        if isinstance(atmosphere_value, (int, float)):
            limit = int(atmosphere_value)
        else:
            # ⚠️ atmosphere가 없으면 기본값 3 사용
            limit = FALLBACK_ALLOW_NORMAL
            log("fallback", f"No atmosphere value, using default limit={limit}")

        # ✅ 카운트 증가
        temp = state.setdefault("temp_data", {})
        count = temp.get("offtopic_count", 0) + 1
        temp["offtopic_count"] = count

        remaining = max(0, limit - count)

        log("fallback", f"Off-topic count: {count}/{limit} (atmosphere={atmosphere_value})")

        # 🔹 limit + 2 이상: 차단
        if count > limit + 1:
            return self._handle_block(state, count, limit)

        # ⚠️ limit + 1: 경고
        if count == limit + 1:
            return self._handle_warning(state, count, limit)

        # ✅ limit 이하: LLM 대사 생성
        return self._handle_allow(state, stage_data, user_input, count, limit, remaining)

    # ============================================================
    # 🚫 차단 관련 함수 — Guardrail 연동 구조 유지
    # ============================================================
    def _is_currently_blocked(self, state: Dict[str, Any]) -> bool:
        """차단 상태 확인 (타이머 만료 시 자동 해제)"""
        if not state.get("system_blocked"):
            return False
        blocked_until = float(state.get("blocked_until") or 0.0)
        if blocked_until <= time.time():
            # ✅ 타이머 만료 → 차단 해제
            state["system_blocked"] = False
            state.pop("blocked_until", None)
            log("fallback", "Block timer expired, unlocking user")
            return False
        return True

    def _enforce_block(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """차단 중 메시지 출력"""
        blocked_until = float(state.get("blocked_until") or 0.0)
        remaining = int(blocked_until - time.time())
        minutes = remaining // 60
        seconds = remaining % 60

        message = f"[꺾쇠 까마귀]⛔️ 자유 대화 제한 중입니다. {minutes}분 {seconds}초 후 다시 시도하세요."

        # ✅ Guardrail 방식으로 메시지 삽입
        self._inject_dialogue(state, speaker="system", text=message)

        log("fallback", f"User blocked, remaining: {minutes}m {seconds}s")

        return {
            "should_block": True,
            "remaining_count": 0,
            "message": message,
            "speaker": "system",
            "action": "block",
            "dialogue": None,
            "new_count": state.get("temp_data", {}).get("offtopic_count", 0),
        }

    def _handle_block(self, state: Dict[str, Any], count: int, limit: int) -> Dict[str, Any]:
        """10분 차단 처리 (limit + 2)"""
        now = time.time()
        message = "[꺾쇠 까마귀]⛔️ 반복된 잡담으로 인해 10분 동안 대화가 제한됩니다."

        # ✅ 차단 상태 설정
        state["system_blocked"] = True
        state["blocked_until"] = now + 600  # 10분

        # ✅ Guardrail 방식으로 메시지 삽입
        self._inject_dialogue(state, speaker="system", text=message)

        log("fallback", f"User soft-blocked for repeated off-topic (count={count}, limit={limit})")

        return {
            "should_block": True,
            "remaining_count": 0,
            "message": message,
            "speaker": "system",
            "action": "block",
            "dialogue": None,
            "new_count": count,
        }

    def _handle_warning(self, state: Dict[str, Any], count: int, limit: int) -> Dict[str, Any]:
        """경고 메시지 출력 (limit + 1)"""
        message = "[꺾쇠 까마귀]⚠️ 또 한 번 반복되면 대화가 제한됩니다."

        # ✅ Guardrail 방식으로 메시지 삽입
        self._inject_dialogue(state, speaker="system", text=message)

        log("fallback", f"Off-topic warning issued (count={count}, limit={limit})")

        return {
            "should_block": False,
            "remaining_count": 0,
            "message": message,
            "speaker": "system",
            "action": "warning",
            "dialogue": None,
            "new_count": count,
        }

    def _handle_allow(
        self,
        state: Dict[str, Any],
        stage_data: Dict[str, Any],
        user_input: str,
        count: int,
        limit: int,
        remaining: int
    ) -> Dict[str, Any]:
        """LLM 대사 생성 허용 (limit 이하)"""
        # ✅ LLM 대사 생성
        # 🔹 마지막 카운트일 때만 임무로 유도 (is_last_chance=True)
        is_last_chance = (count >= limit)
        dialogue = self._generate_dialogue(state, stage_data, user_input, blocking=False, is_last_chance=is_last_chance)

        if dialogue:
            msg = dialogue["text"]
            speaker = dialogue["speaker"]
        else:
            # ⚠️ LLM 실패 시 기본 메시지
            msg = self._default_message("normal", count, limit, False, stage_data)
            speaker = "narr"

        log("fallback", f"Off-topic allowed with LLM response (count={count}/{limit})")

        return {
            "should_block": False,
            "remaining_count": remaining,
            "message": msg,
            "speaker": speaker,
            "action": "allow",
            "dialogue": dialogue,
            "new_count": count,
        }

    # ============================================================
    # 🎨 LLM 대사 생성 — speaker_pool 기반
    # ============================================================
    def _generate_dialogue(
        self,
        state: Dict[str, Any],
        stage: Dict[str, Any],
        user_input: str,
        blocking: bool,
        is_last_chance: bool = False
    ) -> Optional[Dict[str, str]]:
        """
        LLM 호출하여 캐릭터 대사 생성 (children_agent와 동일한 tone_profile 구조 사용)

        - speaker_pool에서만 캐릭터 선택 (akaza, narr, enmu 제외)
        - pool이 비어있으면 "narr" 사용
        - tone_profile (tone, emotion, relationships)을 children_agent와 동일하게 로드
        - world_context를 세계관 정보로 활용
        - is_last_chance: 마지막 허용 카운트일 때 True (임무로 유도)
        """
        try:
            # 🔹 Speaker 선택 (speaker_pool 전용)
            char = self._select_speaker(state, stage)

            # 🔹 tone_profile 로드 (children_agent와 동일한 방식)
            tone_profile = self._load_tone_profile(state, char)

            # 🌍 world_context 로드
            world_context = self._load_world_context(state)

            # 🔹 프롬프트 템플릿 선택
            # blocking일 때는 urgent, is_last_chance일 때는 normal이지만 임무 유도 필요
            if blocking:
                sys_tmpl = self._prompts["urgent_off_topic_base"]
                usr_tmpl = self._prompts["urgent_off_topic_user"]
            else:
                sys_tmpl = self._prompts["off_topic_base"]
                usr_tmpl = self._prompts["off_topic_user"]

            # 🔹 템플릿 포맷팅
            # ✅ scene_tools.get_stage_atmosphere()로 숫자→문자열 변환 활용
            atmosphere_str = get_stage_atmosphere(stage) or "normal"

            # 한글 표시용 매핑
            atmosphere_display_map = {
                "urgent": "긴급",
                "tense": "긴장",
                "calm": "평온",
                "normal": "일반",
                "combat": "전투"
            }
            atmosphere_display = atmosphere_display_map.get(atmosphere_str, "일반")

            stage_tag = stage.get("tag", "unknown")
            mission_hint = stage.get("mission_hint", "현재 미션을 진행하세요")

            # 🔹 tone_profile에서 정보 추출
            tone_data = tone_profile.get("tone", {})
            if isinstance(tone_data, dict):
                # tone_profile 구조: { "mid": { "style": "...", "emotion": "..." } }
                mid_tone = tone_data.get("mid", {})
                tone_style = mid_tone.get("style", "담백하고 단호한 말투")
                emotion = mid_tone.get("emotion", "차분함")
            else:
                # tone이 문자열인 경우 (레거시)
                tone_style = str(tone_data) if tone_data else "담백하고 단호한 말투"
                emotion = "차분함"

            # 🔹 관계성 정보 포맷팅
            relationships = tone_profile.get("relationships", {})
            relationships_section = self._format_relationships(relationships) if relationships else ""

            # 🌍 world_context 섹션 포맷팅
            world_context_section = ""
            if world_context:
                world_context_section = f"\n\n### 세계관\n{world_context}"

            sys = sys_tmpl.format(
                name=char,
                atmosphere_display=atmosphere_display,
                tone=tone_style,
                emotion=emotion,
                relationships_section=relationships_section,
                world_context_section=world_context_section
            )
            # 🔹 마지막 기회일 때 힌트 추가
            if is_last_chance:
                mission_hint = f"{mission_hint}\n\n⚠️ 중요: 이제 슬슬 현재 임무나 상황으로 자연스럽게 유도하세요. (마지막 허용)"

            usr = usr_tmpl.format(
                user_input=user_input,
                stage_tag=stage_tag,
                mission_hint=mission_hint
            )

            # 🔹 LLM 호출 설정
            temp = self._llm.get_agent_setting("fallback", "urgent_temperature" if blocking else "temperature")
            tokens = self._llm.get_agent_setting("fallback", "urgent_max_tokens" if blocking else "max_tokens")

            # ✅ LLM 호출
            response_text = self._llm.call(system_prompt=sys, user_prompt=usr, temperature=temp, max_tokens=tokens)

            # 🛑 플레이어 대사 금지 (강화)
            response_text = self._remove_player_speakers(state, response_text)

            cleaned_text = response_text.strip() or "…"

            return {"speaker": char, "text": cleaned_text}

        except Exception as e:
            log("fallback", f"LLM generation failed: {e}")
            return None

    def _load_tone_profile(self, state: Dict[str, Any], char: str) -> Dict[str, Any]:
        """
        캐릭터의 tone_profile 로드 (children_agent와 동일한 구조)

        Returns:
            {
                "tone": { "mid": { "style": "...", "emotion": "..." } },
                "relationships": { "target": { "description": "...", "type": "..." } }
            }
        """
        try:
            # 🔹 scenario에서 character_refs 가져오기
            scenario = state.get("scenario_data", {}) or state.get("scenario", {})
            character_refs = scenario.get("character_refs", {})

            if char not in character_refs:
                log("fallback", f"⚠️ Character {char} not in character_refs, using defaults")
                return self._get_default_tone_profile()

            # 🔹 scenario_key 추출
            metadata = scenario.get("metadata", {})
            tone_meta = metadata.get("tone", {})
            scenario_key = tone_meta.get("scenario_key")

            # 🔹 load_tone_profiles 호출 (children_agent와 동일)
            profiles = load_tone_profiles({char: character_refs[char]}, scenario_key)

            if char in profiles:
                return profiles[char]
            else:
                log("fallback", f"⚠️ Failed to load tone_profile for {char}, using defaults")
                return self._get_default_tone_profile()

        except Exception as e:
            log("fallback", f"⚠️ Exception loading tone_profile for {char}: {e}, using defaults")
            return self._get_default_tone_profile()

    def _load_world_context(self, state: Dict[str, Any]) -> Optional[str]:
        """
        세계관 정보 로드

        Returns:
            world_context 문자열 (없으면 None)
        """
        try:
            from src.utils.world_loader import WorldLoader

            # 🔹 scenario에서 world_id 가져오기
            scenario = state.get("scenario_data", {}) or state.get("scenario", {})
            world_id = scenario.get("world_id")

            if not world_id:
                log("fallback", "⚠️ No world_id in scenario")
                return None

            # 🔹 WorldLoader로 world_context 로드
            world_context = WorldLoader.get_world_context(world_id)

            if world_context:
                log("fallback", f"🌍 Loaded world context: {world_id}")
                return world_context
            else:
                log("fallback", f"⚠️ Empty world_context for {world_id}")
                return None

        except Exception as e:
            log("fallback", f"⚠️ Failed to load world_context: {e}")
            return None

    def _get_default_tone_profile(self) -> Dict[str, Any]:
        """tone_profile 로드 실패 시 기본값"""
        return {
            "tone": {
                "mid": {
                    "style": "담백하고 단호한 말투",
                    "emotion": "차분함"
                }
            },
            "relationships": {}
        }

    def _format_relationships(self, relationships: Dict[str, Any]) -> str:
        """관계성 정보를 프롬프트용 문자열로 포맷팅"""
        if not relationships:
            return ""

        lines = []
        for target, info in relationships.items():
            if isinstance(info, dict):
                description = info.get("description", "")
                rel_type = info.get("type", "")
                if description:
                    lines.append(f"- {target} ({rel_type}): {description}")

        if lines:
            return "\n관계:\n" + "\n".join(lines)
        return ""

    def _remove_player_speakers(self, state: Dict[str, Any], response_text: str) -> str:
        """
        LLM 응답에서 플레이어 speaker 제거 (강화)

        - user, player, you, 당신, 유저, 플레이어
        - state["player_name"] (예: "츠구코")
        위 speaker를 모두 "narr"로 치환
        """
        # 🔹 금지 speaker 목록
        prohibited_names = {
            "user", "player", "you", "당신", "유저", "플레이어",
            state.get("player_name", "").lower(),
            state.get("user_name", "").lower(),
        }

        # 빈 문자열 제거
        prohibited_names.discard("")

        # 🔹 치환 처리
        for name in prohibited_names:
            if not name:
                continue

            # JSON 형식의 speaker 필드 검색 및 치환
            patterns = [
                f'"speaker": "{name}"',
                f'"speaker":"{name}"',
                f'"speaker": \'{name}\'',
                f'"speaker":\'{name}\'',
            ]

            for pattern in patterns:
                if pattern in response_text.lower():
                    log("fallback", f"❌ Removing invalid speaker '{name}' from LLM response")
                    # 대소문자 무관하게 치환
                    response_text = re.sub(
                        pattern.replace(name, name),
                        '"speaker": "narr"',
                        response_text,
                        flags=re.IGNORECASE
                    )

        return response_text

    def _select_speaker(self, state: Dict[str, Any], stage_data: Dict[str, Any]) -> str:
        """
        응답할 캐릭터 선택 (speaker_pool 전용)

        - speaker_pool에서 선택 (akaza, narr, enmu 제외)
        - 후보 없으면 "narr" 사용
        """
        speaker_pool = stage_data.get("speaker_pool", [])

        # 🔹 제외 캐릭터 필터링
        exclude = {"akaza", "narr", "enmu"}
        candidates = [
            sp for sp in speaker_pool
            if isinstance(sp, str) and sp.lower() not in exclude
        ]

        # ⚠️ 후보 없으면 narr 사용
        if not candidates:
            log("fallback", "No valid speakers in pool, using 'narr'")
            return "narr"

        return random.choice(candidates)

    # ============================================================
    # 🔧 Guardrail 호환 함수
    # ============================================================
    def _is_player_speaker(self, speaker: str) -> bool:
        """
        주어진 speaker가 플레이어/유저 이름인지 확인

        금지된 speaker 이름:
        - "user", "player", "you", "당신", "유저", "플레이어"
        """
        if not speaker:
            return False

        speaker_lower = speaker.lower().strip()

        # 고정된 금지 이름 목록
        prohibited = {
            "user", "player", "you", "당신", "유저", "플레이어",
            "츠구코",  # 기본 플레이어 이름
        }

        return speaker_lower in prohibited

    def _inject_dialogue(
        self,
        state: Dict[str, Any],
        *,
        speaker: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        대화를 state에 삽입 (GuardrailAgent와 동일한 구조)

        🛑 플레이어 speaker 자동 필터링
        """
        # 🛑 플레이어 speaker 체크
        if self._is_player_speaker(speaker):
            log("fallback", f"❌ Filtering player speaker in inject: '{speaker}' → 'narr'")
            speaker = "narr"

        payload = {
            "speaker": speaker,
            "text": text,
            "order": 0,
        }
        if metadata:
            for key, value in metadata.items():
                payload.setdefault(key, value)

        state["agent_responses"] = [payload]
        state["has_more_dialogues"] = False
        state["next_node"] = "dialogue_agent"

        temp = state.setdefault("temp_data", {})
        temp["skip_parent_after_dialogue"] = True

    # ============================================================
    # 🛠️ 헬퍼 함수
    # ============================================================
    def _get_stage_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """현재 스테이지 데이터 추출"""
        scenario = state.get("scenario_data", {})
        tag = state.get("current_stage", "")
        stages = scenario.get("stages", [])

        if isinstance(stages, list):
            return next((s for s in stages if s.get("tag") == tag), {})
        return stages.get(tag, {})

    def _default_message(self, atmosphere: str, count: int, limit: int, block: bool, stage: Dict[str, Any]) -> str:
        """LLM 실패 시 기본 메시지"""
        choices = stage.get("choices", [])
        if block:
            return f"지금은 선택이 더 중요해요. {self._format_choices(choices)}"
        if atmosphere in ["urgent", "tense"]:
            return "⚠️ 지금은 농담할 시간이 아닙니다."
        if count >= limit:
            return "이제 임무에 집중하죠."
        return "그것도 좋지만, 지금은 상황에 집중해야 해요."

    def _format_choices(self, choices: List[Dict[str, Any]]) -> str:
        """선택지 포맷팅"""
        if not choices:
            return ""
        return "\n".join([f"{i+1}. {c.get('text','')}" for i, c in enumerate(choices)])

    def reset_off_topic_count(self, state: Dict[str, Any]) -> None:
        """
        on-topic 판정 시 off-topic 카운트를 리셋

        Args:
            state: 현재 상태 딕셔너리
        """
        temp = state.setdefault("temp_data", {})
        previous_count = temp.get("offtopic_count", 0)
        temp["offtopic_count"] = 0

        if previous_count > 0:
            log("fallback", f"✅ Off-topic count reset: {previous_count} → 0 (on-topic detected)")
        else:
            log("fallback", "✅ Off-topic count reset (already at 0)")


# ============================================================
# 🌐 싱글톤 인스턴스 & 모듈 레벨 함수
# ============================================================

fallback_manager = FallbackManager()


def handle_off_topic(state: Dict[str, Any], user_input: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Off-topic 처리 통합 함수 (router_agent.py에서 사용)

    Args:
        state: 현재 상태
        user_input: 사용자 입력
        use_llm: LLM 사용 여부 (현재는 ���상 True)

    Returns:
        {
            "should_block": bool,
            "remaining_count": int,
            "message": str,
            "speaker": str,
            "action": "allow" | "warning" | "block",
            "dialogue": {"speaker": str, "text": str} | None,
            "new_count": int,
        }
    """
    return fallback_manager.handle_off_topic(state, user_input)


def trigger_fallback(state: Dict[str, Any], stage: Dict[str, Any], reason: str = "off_topic") -> Dict[str, Any]:
    """
    Fallback 페이로드 생성 (레거시 호환 함수)

    mission_stage.py와 state_tools.py에서 사용하는 레거시 함수.
    간단한 fallback 페이로드를 반환합니다.

    Args:
        state: 현재 상태
        stage: 현재 스테이지 데이터
        reason: fallback 사유 (예: "invalid_target", "urgent_atmosphere")

    Returns:
        {
            "dialogues": [],  # 추가 대화를 위한 빈 리스트
            "reason": str,
            "should_block": bool,
            "atmosphere": str,
        }
    """
    atmosphere = get_stage_atmosphere(stage) or "normal"
    should_block = (atmosphere == "urgent")

    return {
        "dialogues": [],
        "reason": reason,
        "should_block": should_block,
        "atmosphere": atmosphere,
    }


def check_fallback_policy(state: Dict[str, Any], is_off_topic: bool) -> Dict[str, Any]:
    """
    Fallback 정책 확인 (레거시 호환)

    Note: 이 함수는 레거시 호환성을 위해 유지되지만,
    실제로는 handle_off_topic()을 사용하는 것을 권장합니다.
    """
    if not is_off_topic:
        return {"action": "pass", "should_block": False}

    # ✅ 간단한 정책 체크 (실제 처리는 handle_off_topic에서)
    temp = state.get("temp_data", {})
    count = temp.get("offtopic_count", 0)

    return {
        "action": "check",
        "should_block": False,
        "current_count": count,
    }


def apply_fallback_result(state: Dict[str, Any], fallback_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback 결과를 상태에 반영 (레거시 호환)

    Note: handle_off_topic()이 직접 state를 수정하므로,
    이 함수는 레거시 호환성을 위해서만 유지됩니다.
    """
    # ✅ fallback_result가 이미 state에 반영되어 있으므로 그대로 반환
    return state


def reset_fallback_count(state: Dict[str, Any]) -> None:
    """
    Fallback 카운트 리셋 (on-topic 복귀 시 호출)

    이 함수는 router_agent.py의 _handle_on_topic에서 호출되어
    on-topic 판정이 나올 때마다 off-topic 누적 count를 자동 초기화합니다.
    """
    fallback_manager.reset_off_topic_count(state)


__all__ = [
    "FallbackManager",
    "fallback_manager",
    "handle_off_topic",
    "trigger_fallback",
    "check_fallback_policy",
    "apply_fallback_result",
    "reset_fallback_count",
]
