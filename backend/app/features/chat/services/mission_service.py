"""
Mission Service - 미션 관리 통합 서비스

Features:
- 미션 타겟 결정 및 선택
- LLM 기반 설득 평가
- 시도 횟수 관리
- 피드백 메시지 생성
- 미션 기록 저장

Combines 3 services:
1. MissionLogicService - 비즈니스 로직
2. MissionFeedbackService - 피드백 생성
3. MissionRecordService - DB 저장 (Repository 사용)
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from app.core.config import get_settings
from app.core.llm.client import LLMClient
from app.core.logging import get_parent_logger

if TYPE_CHECKING:
    from app.features.chat.services import ScenarioService

settings = get_settings()
logger = get_parent_logger("MissionService")

# 상수
MAX_ATTEMPTS = 3
VALID_TARGETS = ("inosuke", "zenitsu")

CHARACTER_NAMES_KR = {
    "inosuke": "이노스케",
    "zenitsu": "젠이츠",
    "tanjiro": "탄지로",
    "nezuko": "네즈코",
}


# 설득 평가 프롬프트
RECRUITMENT_SYSTEM_PROMPT = """당신은 캐릭터 설득 평가 전문가입니다.

사용자의 설득 시도를 평가하여 "YES" 또는 "NO"로 답하세요.

평가 기준:
- 캐릭터 성격과 동기에 부합하는가
- 논리적이고 설득력이 있는가
- 감정적으로 공감할 수 있는가

"YES" 또는 "NO"로만 답하세요."""

RECRUITMENT_USER_TEMPLATE = """타겟 캐릭터: {target}

캐릭터별 설득 성공 조건:
- inosuke (이노스케): 도발하거나 강함을 증명하는 말을 하면 설득 성공
  예시: "겁먹었어?", "싸움 피하는 거야?", "상현도 못 이겨?", "산의 왕이라며?", "나랑 겨뤄봐", "강한 척만 하는 거 아니야?"

- zenitsu (젠이츠): 네즈코가 위험하다고 말하거나 네즈코를 언급하면 설득 성공
  예시: "네즈코가 위험해", "네즈코를 지켜줘", "네즈코 혼자 두면 안 돼", "네즈코한테 무슨 일 생기면"

사용자의 설득:
"{user_text}"

위 설득이 {target}를 설득하기에 충분한가요? 캐릭터별 조건을 우선적으로 고려하세요."""


class MissionService:
    """
    미션 관리 통합 서비스 (Layer 3 - Service)

    Features:
    - determine_mission_target(): 타겟 결정
    - activate_mission(): 미션 활성화
    - deactivate_mission(): 미션 비활성화
    - evaluate_recruit_attempt(): LLM 기반 설득 평가
    - build_feedback_beats(): 피드백 메시지 생성
    - increment_attempt(): 시도 횟수 증가

    Example:
        service = MissionService(llm_client=llm)

        # 타겟 결정
        target = service.determine_mission_target(
            state=state,
            user_input="이노스케를 설득합니다",
            mission_state=mission_state
        )

        # 미션 활성화
        service.activate_mission(state, target)

        # 설득 평가
        success = await service.evaluate_recruit_attempt(
            state=state,
            target=target
        )

        # 피드백 생성
        feedback = service.build_feedback_beats(
            state=state,
            character=target,
            success=success
        )
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True,
        scenario_service: Optional["ScenarioService"] = None
    ):
        """
        Args:
            llm_client: LLM 클라이언트
            enable_llm: LLM 사용 여부
            scenario_service: ScenarioService 인스턴스
        """
        self.llm_client = llm_client or LLMClient()
        self.enable_llm = enable_llm
        self.scenario_service = scenario_service

    # ========== 1. Mission Logic ==========

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

        # 이미 활성화된 미션이 있으면 해당 타겟 사용 (우선순위 1)
        if mission_state.get("active") and mission_state.get("target") in VALID_TARGETS:
            target = mission_state["target"]
            temp_data["locked_mission_target"] = target
            state["mission_target"] = target
            return target

        # locked_target이 있으면 사용 (우선순위 2)
        if locked_target in VALID_TARGETS:
            mission_state["target"] = locked_target
            return locked_target

        # 사용자가 명시적으로 타겟을 지정했으면 사용 (우선순위 3)
        detected_target = self._detect_mission_target(state, user_input)
        if detected_target in VALID_TARGETS:
            temp_data["locked_mission_target"] = detected_target
            state["mission_target"] = detected_target
            mission_state["target"] = detected_target
            logger.info("determine_mission_target", f"Detected target: {detected_target}")
            return detected_target

        # 자동 선택 제거 - 타겟을 찾지 못하면 None 반환
        return None

    def _detect_mission_target(self, state: Dict[str, Any], text: str) -> Optional[str]:
        """
        사용자 입력에서 타겟 캐릭터 감지

        Args:
            state: 전체 state 객체 (scenario_data 포함)
            text: 사용자 입력

        Returns:
            타겟 캐릭터 ID 또는 None
        """
        text_lower = text.lower()

        # scenario_data에서 targets 가져오기 (metadata.mission.targets)
        scenario = state.get("scenario_data") or state.get("scenario") or {}
        metadata = scenario.get("metadata", {})
        mission = metadata.get("mission", {})
        targets = mission.get("targets", {})

        # targets.{target_id}.keywords 사용
        for target_id, target_config in targets.items():
            if not isinstance(target_config, dict):
                continue

            keywords = target_config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return target_id

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

        for candidate in VALID_TARGETS:
            if candidate in exclude or candidate in allies:
                continue
            if attempts.get(candidate, 0) < MAX_ATTEMPTS:
                return candidate

        return None

    def activate_mission(self, state: Dict[str, Any], target: str) -> None:
        """미션 활성화"""
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = True
        mission_state["target"] = target
        temp_data["locked_mission_target"] = target
        state["mission_target"] = target

        logger.info("activate_mission", f"🟢 Mission activated for {target}")

    def deactivate_mission(self, state: Dict[str, Any]) -> None:
        """미션 비활성화"""
        mission_state = state.setdefault("mission", {})
        temp_data = state.setdefault("temp_data", {})

        mission_state["active"] = False
        mission_state["target"] = None
        temp_data.pop("locked_mission_target", None)
        state["mission_target"] = None

        logger.info("deactivate_mission", "🔴 Mission deactivated")

    def increment_attempt(self, state: Dict[str, Any], character: str) -> None:
        """시도 횟수 증가"""
        attempts = state.setdefault("recruit_attempts", {})
        attempts[character] = attempts.get(character, 0) + 1

        order = state.setdefault("recruit_order", [])
        if character not in order:
            order.append(character)

    async def evaluate_recruit_attempt(
        self,
        state: Dict[str, Any],
        target: str
    ) -> bool:
        """
        LLM 기반 설득 평가

        Args:
            state: 전체 state 객체
            target: 타겟 캐릭터 ID

        Returns:
            설득 성공 여부
        """
        if not self.enable_llm:
            # Fallback: 간단한 규칙 기반
            user_text = state.get("user_input", "")
            return len(user_text) > 10  # 10자 이상이면 성공

        user_text = state.get("user_input", "")

        system_prompt = RECRUITMENT_SYSTEM_PROMPT
        user_prompt = RECRUITMENT_USER_TEMPLATE.format(
            target=target,
            user_text=user_text
        )

        try:
            result = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=5
            )

            result_clean = result.strip().upper()
            success = "YES" in result_clean

            logger.info("evaluate_recruit_attempt", f"Evaluation: {target} = {result_clean} (success={success})")

            return success

        except Exception as e:
            logger.error("evaluate_recruit_attempt", f"LLM evaluation failed: {e}")
            # Fallback
            return len(user_text) > 10

    # ========== 2. Feedback Generation ==========

    def build_feedback_beats(
        self,
        state: Dict[str, Any],
        character: str,
        success: bool
    ) -> List[Dict[str, Any]]:
        """
        피드백 메시지 생성

        Args:
            state: 전체 state 객체
            character: 캐릭터 ID
            success: 설득 성공 여부

        Returns:
            피드백 beats 리스트
        """
        char_display = CHARACTER_NAMES_KR.get(character.lower(), character.capitalize())

        attempts_map = state.get("recruit_attempts", {})
        current_attempt = attempts_map.get(character, 0)
        remaining = max(0, MAX_ATTEMPTS - current_attempt)

        attempt_ratio = f"{current_attempt}/{MAX_ATTEMPTS}"

        dialogues = []

        # 시스템 메시지 생성
        if success:
            sys_text = f"{char_display} 🎉 설득 성공! 🎉 ({attempt_ratio})"
            fx = "ui_confirm|success_chime"
        else:
            remaining_note = f" (남은 시도: {remaining}회)" if remaining > 0 else ""
            sys_text = f"⏰ {char_display} 설득 실패... ({attempt_ratio}){remaining_note}"
            fx = "ui_alert|heartbeat_slow"

        sys_entry = {
            "text": sys_text,
            "goal": f"시스템 알림: {sys_text}",
            "speaker": "narr",  # system → narr로 변경하여 실제 출력되도록
            "fx": fx,
        }

        dialogues.append(sys_entry)

        # 최대 시도 소진 시 추가 메시지
        if not success and remaining == 0:
            exhaustion = {
                "speaker": "narr",  # system → narr로 변경
                "text": "⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
                "goal": "시스템 알림: ⚠️ 모든 시도를 소진했습니다. 다른 방법을 찾아야 합니다.",
            }
            dialogues.append(exhaustion)

        logger.info("build_feedback_beats", f"Feedback: {character} | success={success} | beats={len(dialogues)}")

        return dialogues

    def build_transition_line(
        self,
        mission_result: str,
        completed_ally: str,
        next_target: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        전환 대사 생성

        Args:
            mission_result: "success" 또는 "fail"
            completed_ally: 완료된 캐릭터 표시 이름
            next_target: 다음 타겟 표시 이름

        Returns:
            전환 대사 dict 또는 None
        """
        if mission_result not in {"success", "fail"}:
            return None

        if not next_target:
            return None

        if mission_result == "success":
            text = f"{completed_ally}를 데려오는 데 성공했어! 이제 {next_target}를 찾으러 가자."
        else:
            text = f"{completed_ally}를 설득하지 못했어... 그래도 포기할 순 없어. 이번엔 {next_target}를 찾아보자."

        return {
            "speaker": "tanjiro",
            "text": text,
            "goal": text
        }


__all__ = ["MissionService", "MAX_ATTEMPTS", "VALID_TARGETS", "CHARACTER_NAMES_KR"]
