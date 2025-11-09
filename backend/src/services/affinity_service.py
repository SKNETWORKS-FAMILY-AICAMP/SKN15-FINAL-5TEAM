"""
============================================================
💜 Affinity Service — 친밀도 점수 관리 서비스
============================================================
표준 친밀도 판정 규칙을 적용하여 캐릭터별 친밀도를 업데이트합니다.

친밀도 상승 규칙:
- 일반 상호작용: +2점
- 칭찬과 격려: +3점
- 긍정적/핵심 상호작용: +5점
- 전투 협력: +6점
- 결정적/공략적 상호작용: +8점
- 핵심 목표 달성: +10점

친밀도 하락 규칙:
- 비협조적/맥락 이탈 대화: -2점
- 무시 및 무관심: -3점
- 경멸 및 비난: -8점
- 이기적/비겁한 행동: -10점
- 신뢰 관계 파괴: -15점

제약사항:
- 한 컷신에서 캐릭터별 최대 획득 가능 점수: ±20점
- 조건 중복 시 합산
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.logger import log
from src.utils.config_loader import get_config_loader

# 친밀도 규칙 정의
AFFINITY_RULES = {
    # 상승 규칙
    "general_interaction": 2,  # 일반 상호작용
    "praise_encouragement": 3,  # 칭찬과 격려
    "positive_interaction": 5,  # 긍정적/핵심 상호작용
    "combat_cooperation": 6,  # 전투 협력
    "strategic_interaction": 8,  # 결정적/공략적 상호작용
    "key_objective_achieved": 10,  # 핵심 목표 달성

    # 하락 규칙
    "uncooperative_offtopic": -2,  # 비협조적/맥락 이탈 대화
    "indifference_neglect": -3,  # 무시 및 무관심
    "contempt_blame": -8,  # 경멸 및 비난
    "selfish_cowardly": -10,  # 이기적/비겁한 행동
    "trust_betrayal": -15,  # 신뢰 관계 파괴
}

# 컷신당 최대 친밀도 변화량
MAX_AFFINITY_PER_CUTSCENE = 20


class AffinityService:
    """
    친밀도 관리 서비스

    사용자의 선택과 대화를 분석하여 표준 규칙에 따라 친밀도를 업데이트합니다.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self._llm_client = llm_client or get_llm_client()

        # 프롬프트 로드
        config = get_config_loader()
        prompts = config.get_prompts()
        affinity_prompts = prompts.get("llm_prompts", {}).get("affinity", {})
        self._system_prompt = affinity_prompts.get("system", "")
        self._user_prompt_template = affinity_prompts.get("user", "")

        if not self._system_prompt or not self._user_prompt_template:
            log("affinity", "⚠️ Affinity prompts missing in configs/prompts.yaml, using fallback")
            self._use_llm = False
        else:
            self._use_llm = True

    def update_affinity(
        self,
        state: Dict[str, Any],
        user_input: str,
        dialogues: List[Dict[str, str]],
        participating_characters: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        친밀도 점수를 업데이트합니다.

        Args:
            state: 현재 게임 상태
            user_input: 사용자 입력
            dialogues: 생성된 대화 리스트 [{"speaker": "tanjiro", "text": "..."}, ...]
            participating_characters: 참여 캐릭터 리스트 (None이면 dialogues에서 추출)

        Returns:
            업데이트된 affinity_scores
        """
        # 참여 캐릭터 추출
        if participating_characters is None:
            participating_characters = self._extract_participating_characters(dialogues)

        if not participating_characters:
            log("affinity", "No participating characters found, skipping affinity update")
            return state.get("affinity_scores", {})

        # 현재 친밀도 점수
        current_affinity = state.get("affinity_scores", {}).copy()

        # 현재 스테이지 정보
        current_stage = state.get("current_stage", "unknown")
        scenario_context = self._build_scenario_context(state)

        # LLM을 사용하여 친밀도 변화 계산
        if self._use_llm:
            affinity_changes = self._classify_interaction_with_llm(
                user_input=user_input,
                dialogues=dialogues,
                participating_characters=participating_characters,
                scenario_context=scenario_context,
                current_stage=current_stage,
            )
        else:
            # Fallback: 온토픽이면 일반 상호작용으로 처리
            classification = state.get("classification", "")
            if classification == "on_topic":
                affinity_changes = {char: AFFINITY_RULES["general_interaction"] for char in participating_characters}
            else:
                affinity_changes = {}

        # 컷신당 최대치 제한 적용
        affinity_changes = self._enforce_cutscene_limit(state, affinity_changes, current_stage)

        # 친밀도 업데이트
        for character, change in affinity_changes.items():
            old_score = current_affinity.get(character, 0)  # 기존 점수 (없으면 0)
            current_affinity[character] = max(0, old_score + change)  # 최소값 0
            log("affinity", f"💜 {character}: {old_score} → {current_affinity[character]} (change: {change:+d})")

        return current_affinity

    def _extract_participating_characters(self, dialogues: List[Dict[str, str]]) -> List[str]:
        """대화에서 참여 캐릭터 추출"""
        characters = set()
        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "").lower()
            # narr, user 제외
            if speaker and speaker not in ("narr", "user", "narrator", "system"):
                characters.add(speaker)
        return list(characters)

    def _build_scenario_context(self, state: Dict[str, Any]) -> str:
        """시나리오 컨텍스트 구성"""
        scenario_data = state.get("scenario_data") or state.get("scenario") or {}
        scenario_id = state.get("scenario_id", "unknown")
        current_stage = state.get("current_stage", "unknown")

        # 스테이지 정보
        stage_info = ""
        if isinstance(scenario_data, dict):
            stages = scenario_data.get("stages", {})
            if current_stage in stages:
                stage_data = stages[current_stage]
                stage_type = stage_data.get("type", "unknown")
                stage_info = f"현재 스테이지: {current_stage} (타입: {stage_type})"

        # 최근 대화 히스토리
        message_history = state.get("message_history", [])
        recent_history = []
        for entry in message_history[-3:]:
            if isinstance(entry, dict):
                speaker = entry.get("speaker", "unknown")
                text = entry.get("text", "")
                if text:
                    recent_history.append(f"{speaker}: {text}")

        history_str = "\n".join(recent_history) if recent_history else "(대화 시작)"

        return f"""
시나리오: {scenario_id}
{stage_info}

최근 대화:
{history_str}
""".strip()

    def _classify_interaction_with_llm(
        self,
        user_input: str,
        dialogues: List[Dict[str, str]],
        participating_characters: List[str],
        scenario_context: str,
        current_stage: str,
    ) -> Dict[str, int]:
        """
        LLM을 사용하여 상호작용을 분류하고 친밀도 변화량을 계산합니다.

        Returns:
            {character_id: affinity_change, ...}
        """
        # 대화 텍스트 구성
        dialogue_text = "\n".join([
            f"{d.get('speaker', 'unknown')}: {d.get('text', '')}"
            for d in dialogues
        ])

        # 사용자 프롬프트 구성
        user_prompt = self._user_prompt_template.format(
            scenario_context=scenario_context,
            current_stage=current_stage,
            user_input=user_input,
            dialogues=dialogue_text,
            participating_characters=", ".join(participating_characters),
        )

        try:
            # LLM 호출
            response = self._llm_client.call_json(
                system_prompt=self._system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # 일관성 있는 판정을 위해 낮은 온도
                max_tokens=300,
                agent="affinity",
            )

            # 응답 파싱
            affinity_changes = {}

            if isinstance(response, dict) and "affinity_changes" in response:
                changes = response["affinity_changes"]
                if isinstance(changes, dict):
                    for char, change in changes.items():
                        try:
                            affinity_changes[char.lower()] = int(change)
                        except (ValueError, TypeError):
                            log("affinity", f"⚠️ Invalid affinity change for {char}: {change}")

            # 판정 이유 로깅
            reasoning = response.get("reasoning", "")
            if reasoning:
                log("affinity", f"💭 LLM reasoning: {reasoning[:100]}...")

            log("affinity", f"✅ Affinity changes calculated: {affinity_changes}")
            return affinity_changes

        except Exception as exc:
            log("affinity", f"❌ LLM classification failed: {exc}")
            # Fallback: 일반 상호작용으로 처리
            return {char: AFFINITY_RULES["general_interaction"] for char in participating_characters}

    def _enforce_cutscene_limit(
        self,
        state: Dict[str, Any],
        affinity_changes: Dict[str, int],
        current_stage: str,
    ) -> Dict[str, int]:
        """
        컷신당 최대 친밀도 변화량 제한 적용

        한 컷신에서 캐릭터별 최대 ±20점까지만 획득 가능
        """
        # 스테이지별 친밀도 누적량 추적
        stage_affinity_tracking = state.setdefault("_stage_affinity_tracking", {})

        # 현재 스테이지의 누적량
        stage_accumulated = stage_affinity_tracking.setdefault(current_stage, {})

        # 제한 적용
        limited_changes = {}
        for character, change in affinity_changes.items():
            accumulated = stage_accumulated.get(character, 0)

            # 상승 제한 (최대 +20)
            if change > 0:
                max_allowed = MAX_AFFINITY_PER_CUTSCENE - accumulated
                if max_allowed <= 0:
                    limited_change = 0
                    log("affinity", f"⚠️ {character} reached max affinity gain for stage {current_stage} (+{accumulated}/+{MAX_AFFINITY_PER_CUTSCENE})")
                else:
                    limited_change = min(change, max_allowed)
                    if limited_change < change:
                        log("affinity", f"⚠️ {character} affinity gain limited: {change} → {limited_change} (accumulated: {accumulated}/+{MAX_AFFINITY_PER_CUTSCENE})")
            # 하락 제한 (최대 -20)
            elif change < 0:
                min_allowed = -MAX_AFFINITY_PER_CUTSCENE - accumulated
                if min_allowed >= 0:
                    limited_change = 0
                    log("affinity", f"⚠️ {character} reached max affinity loss for stage {current_stage} ({accumulated}/-{MAX_AFFINITY_PER_CUTSCENE})")
                else:
                    limited_change = max(change, min_allowed)
                    if limited_change > change:
                        log("affinity", f"⚠️ {character} affinity loss limited: {change} → {limited_change} (accumulated: {accumulated}/-{MAX_AFFINITY_PER_CUTSCENE})")
            else:
                limited_change = 0

            # 누적량 업데이트
            if limited_change != 0:
                stage_accumulated[character] = accumulated + limited_change
                limited_changes[character] = limited_change

        return limited_changes


# 싱글톤 인스턴스
_affinity_service: Optional[AffinityService] = None


def get_affinity_service() -> AffinityService:
    """AffinityService 싱글톤 인스턴스"""
    global _affinity_service
    if _affinity_service is None:
        _affinity_service = AffinityService()
    return _affinity_service


__all__ = ["AffinityService", "get_affinity_service", "AFFINITY_RULES", "MAX_AFFINITY_PER_CUTSCENE"]
