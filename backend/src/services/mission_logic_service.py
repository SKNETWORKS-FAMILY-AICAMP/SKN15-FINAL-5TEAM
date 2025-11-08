"""
============================================================
🎯 Mission Logic Service — 미션 비즈니스 로직
============================================================
미션 타겟 관리, LLM 평가, 상태 관리를 담당합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.text_matcher import detect_mission_target
from src.utils.logger import log
from src.utils.config_loader import get_config_loader

_PROMPTS = get_config_loader().get_prompts()
_MISSION_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("mission") or {})
_RECRUITMENT_PROMPT = (_MISSION_PROMPTS.get("recruitment_judge") or "").strip()
_RECRUITMENT_USER_TEMPLATE = (_MISSION_PROMPTS.get("recruitment_judge_user") or "").strip()

if not _RECRUITMENT_PROMPT:
    raise ValueError("MissionHandler recruitment_judge prompt missing in configs/prompts.yaml")
if not _RECRUITMENT_USER_TEMPLATE:
    raise ValueError("MissionHandler recruitment_judge_user prompt missing in configs/prompts.yaml")


class MissionLogicService:
    """
    미션 비즈니스 로직 서비스

    책임:
    - 타겟 결정 및 선택
    - 미션 활성화/비활성화
    - LLM 기반 설득 평가
    - 시도 횟수 관리
    """

    MAX_ATTEMPTS = 3
    VALID_TARGETS = ("inosuke", "zenitsu")

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self._llm = llm_client or get_llm_client()

    def determine_mission_target(
        self,
        state: Dict[str, Any],
        user_input: str,
        mission_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        미션 타겟 결정

        Args:
            state: 전체 state 객체
            user_input: 사용자 입력
            mission_state: 미션 상태

        Returns:
            타겟 캐릭터 ID 또는 None
        """
        temp_data = state.setdefault("temp_data", {})
        locked_target = temp_data.get("locked_mission_target")
        detected_target = detect_mission_target(user_input)

        # 이미 활성화된 미션이 있으면 해당 타겟 사용
        if mission_state.get("active") and mission_state.get("target") in self.VALID_TARGETS:
            target = mission_state["target"]
            temp_data["locked_mission_target"] = target
            state["mission_target"] = target
            return target

        # locked_target이 있으면 사용
        if locked_target in self.VALID_TARGETS:
            mission_state["target"] = locked_target
            return locked_target

        # 사용자가 명시적으로 타겟을 지정했으면 사용
        if detected_target in self.VALID_TARGETS:
            temp_data["locked_mission_target"] = detected_target
            state["mission_target"] = detected_target
            mission_state["target"] = detected_target
            return detected_target

        # 자동 타겟 선택 (우선순위: inosuke → zenitsu)
        allies = state.get("allies_recruited", [])
        attempts = state.get("recruit_attempts", {})

        for candidate in self.VALID_TARGETS:
            if candidate not in allies and attempts.get(candidate, 0) < self.MAX_ATTEMPTS:
                temp_data["locked_mission_target"] = candidate
                state["mission_target"] = candidate
                mission_state["target"] = candidate
                log("mission_logic", f"[AUTO-TARGET] Selecting {candidate}")
                return candidate

        return None

    def select_next_target(
        self,
        state: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        다음 타겟 선택

        Args:
            state: 전체 state 객체
            exclude: 제외할 타겟 리스트

        Returns:
            다음 타겟 캐릭터 ID 또는 None
        """
        exclude = set(exclude or [])
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        for candidate in self.VALID_TARGETS:
            if candidate in exclude or candidate in allies:
                continue
            if attempts.get(candidate, 0) < self.MAX_ATTEMPTS:
                return candidate

        return None

    def activate_mission(self, state: Dict[str, Any], target: str) -> None:
        """
        미션 활성화

        Args:
            state: 전체 state 객체
            target: 타겟 캐릭터 ID
        """
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = True
        mission_state["target"] = target
        temp_data["locked_mission_target"] = target
        state["mission_target"] = target

        log("mission_logic", f"🟢 Mission activated for {target}")

    def deactivate_mission(self, state: Dict[str, Any]) -> None:
        """
        미션 비활성화

        Args:
            state: 전체 state 객체
        """
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = False
        mission_state["target"] = None
        temp_data.pop("locked_mission_target", None)
        state["mission_target"] = None

    def increment_attempt(self, state: Dict[str, Any], character: str) -> None:
        """
        시도 횟수 증가

        Args:
            state: 전체 state 객체
            character: 캐릭터 ID
        """
        attempts = state.setdefault("recruit_attempts", {})
        attempts[character] = attempts.get(character, 0) + 1

        order = state.setdefault("recruit_order", [])
        if character not in order:
            order.append(character)

    def evaluate_recruit_attempt(self, state: Dict[str, Any], target: str) -> bool:
        """
        LLM을 사용한 설득 시도 평가

        Args:
            state: 전체 state 객체
            target: 타겟 캐릭터 ID

        Returns:
            설득 성공 여부
        """
        user_text = state.get("user_input", "")

        system_prompt = _RECRUITMENT_PROMPT
        user_prompt = _RECRUITMENT_USER_TEMPLATE.format(
            target=target,
            user_text=user_text
        )

        try:
            temperature = self._llm.get_agent_setting("mission", "temperature", 0.0)
            max_tokens = self._llm.get_agent_setting("mission", "max_tokens", 5)

            result = self._llm.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                agent="mission",
            )

            decision = "true" in (result or "").lower()
            log("mission_logic", f"[LLM DECISION] target={target} → {'SUCCESS' if decision else 'FAIL'}")
            return decision

        except Exception as exc:
            log("mission_logic", f"[LLM ERROR] fallback heuristic used: {exc}", level=40)
            return self._heuristic_fallback(user_text, target)

    def _heuristic_fallback(self, text: str, target: str) -> bool:
        """휴리스틱 기반 fallback 판정"""
        lowered = (text or "").lower()
        if target == "zenitsu":
            return any(keyword in lowered for keyword in ["네즈코", "사랑", "지켜", "위험"])
        if target == "inosuke":
            return any(keyword in lowered for keyword in ["겁쟁", "약하", "싸우", "도전", "멧돼"])
        return False

    def update_recruit_result(self, state: Dict[str, Any], character: str, success: bool) -> None:
        """
        설득 결과 업데이트 (state만 업데이트, DB 저장은 MissionRecordService에서)

        Args:
            state: 전체 state 객체
            character: 캐릭터 ID
            success: 설득 성공 여부
        """
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

        log(
            "mission_logic",
            f"[RESULT] {character} → {'SUCCESS' if success else 'FAIL'}",
            attempts=state.get("recruit_attempts"),
            allies=state.get("allies_recruited"),
            failures=state.get("recruit_failures"),
        )

    def all_missions_resolved(self, state: Dict[str, Any]) -> bool:
        """
        모든 미션이 완료되었는지 확인

        Args:
            state: 전체 state 객체

        Returns:
            모든 미션 완료 여부
        """
        attempts = state.get("recruit_attempts", {})
        allies = state.get("allies_recruited", [])

        for character in self.VALID_TARGETS:
            if character in allies:
                continue
            if attempts.get(character, 0) < self.MAX_ATTEMPTS:
                return False

        return True


__all__ = ["MissionLogicService"]
