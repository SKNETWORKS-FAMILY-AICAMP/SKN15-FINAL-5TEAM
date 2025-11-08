"""
============================================================
🎨 Prompt Builder — LLM 프롬프트 구성 로직 분리
============================================================
각 에이전트의 프롬프트 구성 로직을 전략 3에 따라 분리합니다.
state 객체를 받아서 최종 프롬프트 문자열을 반환합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.utils.config_loader import get_config_loader
from src.config.constants import INTRO_STAGE_TAGS

_PROMPTS = get_config_loader().get_prompts()


# ============================================================
# 🗣️ Dialogue Prompt Builder (ChildrenAgent)
# ============================================================
class DialoguePromptBuilder:
    """
    ChildrenAgent에서 사용하는 대사 생성 프롬프트 빌더
    dialogue_tools.compose_llm_prompt()의 로직을 여기로 이동
    """

    @staticmethod
    def build(
        stage_tag: str,
        beats: List[Dict[str, Any]],
        tone_profiles: Dict[str, Any],
        speaker_pool: List[str],
        context_summary: Optional[str] = None,
        stage_turn: int = 0,
        stage_type: str = "",
        stage_objective: Optional[str] = None,
        intent_options: Optional[Dict[str, Any]] = None,
        latest_user_input: Optional[str] = None,
        recent_dialogues: Optional[List[str]] = None,
        conversation_summary: Optional[str] = None,
    ) -> str:
        """
        대사 생성을 위한 LLM 프롬프트 구성
        (scene_dialogue_tools.compose_llm_prompt()에서 이동)

        Args:
            stage_tag: 현재 스테이지 태그
            beats: 시나리오 beat 목록
            tone_profiles: 캐릭터 톤 프로필
            speaker_pool: 등장 가능한 캐릭터 목록
            context_summary: 최근 맥락 요약
            stage_turn: 현재 스테이지 턴 수
            stage_type: 스테이지 타입
            stage_objective: 스테이지 목표
            intent_options: Intent 옵션 (자유 의사결정)
            latest_user_input: 최근 사용자 입력
            recent_dialogues: 최근 대화 기록
            conversation_summary: 장기 대화 요약

        Returns:
            구성된 프롬프트 문자열
        """
        # --- tone 요약 ---
        tone_desc = "\n".join(
            f"- {name}: {tone.get('tone', {}).get('mid', {}).get('style', '중립적 어투')}"
            for name, tone in tone_profiles.items()
        )

        # --- 관계 요약 (🚀 Simplified: 중요한 관계만 출력) ---
        rel_desc = []
        first_encounter_pairs: Set[tuple] = set()  # 중복 제거용

        for name, tone in tone_profiles.items():
            rels = tone.get("relationships", {})
            for target, info in rels.items():
                description = info.get('description', '')
                # 🚀 관계 설명이 짧으면 출력 (verbose한 설명은 생략)
                if len(description) < 50:
                    rel_type = info.get('type', '')
                    rel_desc.append(f"- {name}↔{target} ({rel_type}): {description}")

                # "처음", "첫", "조우" 등의 키워드로 처음 만남 감지
                if any(keyword in description for keyword in ["처음", "첫", "조우", "첫 만남", "first"]):
                    pair = tuple(sorted([name, target]))
                    first_encounter_pairs.add(pair)

        # 🚀 처음 만남 경고 메시지 간소화 (decorative 요소 제거)
        first_encounter_notes = []
        if first_encounter_pairs:
            first_encounter_notes.append("🚨 처음 만남 주의:")
            for pair in sorted(first_encounter_pairs):
                first_encounter_notes.append(f"⚠️ {pair[0]}와 {pair[1]}는 처음 만남 (이름 모름, 경계/호기심)")

        rel_text = "\n".join(rel_desc) if rel_desc else "(관계 정보 없음)"
        first_encounter_text = "\n".join(first_encounter_notes) if first_encounter_notes else ""

        # --- beats ---
        beat_lines = "\n".join(f"- {b.get('goal', '')}" for b in beats)

        objective_block = ""
        if stage_objective:
            objective_block = f"""
    [미션 목표]
    {stage_objective}
    """

        intent_block = ""
        if intent_options:
            option_lines = "\n".join(
                f"- {key}: {value}" for key, value in intent_options.items()
            )
            intent_block = f"""
    [선택지]
    {option_lines}
    """

        # 🚀 인트로 스테이지 감지 (간소화)
        intro_stage_aliases = {tag.upper() for tag in INTRO_STAGE_TAGS}
        is_intro = stage_tag.upper() in intro_stage_aliases
        has_narr_beat = any(
            b.get("speaker", "").lower() == "narr"
            for b in beats
        )
        intro_narr_reminder = ""
        if is_intro and has_narr_beat:
            intro_narr_reminder = "\n⭐ 인트로: narr로 시작 필수\n"

        summary_block = ""
        if context_summary:
            summary_block = f"""
    [이전 턴 요약]
    {context_summary}
    """

        # 🧠 장기기억 블록 (🚀 Simplified)
        long_term_memory_block = ""
        if conversation_summary:
            # 🚀 길이 제한: 긴 요약은 잘라서 사용 (token 절약)
            summary_truncated = conversation_summary[:200] + "..." if len(conversation_summary) > 200 else conversation_summary
            long_term_memory_block = f"""
    [장기기억]
    {summary_truncated}
    """

        user_input_block = ""
        if latest_user_input:
            user_input_block = f"""
    [사용자 입력]
    {latest_user_input}
    """

        recent_dialogues_block = ""
        if recent_dialogues:
            # 🚀 최근 대화도 길이 제한 (너무 길면 최근 3개만)
            recent_limited = recent_dialogues[-3:] if len(recent_dialogues) > 3 else recent_dialogues
            recent_dialogues_block = f"""
    [최근 대화]
    {"; ".join(recent_limited)}
    """

        prompt = f"""
    당신은 Demon Slayer: 무한열차 시나리오의 대사 작가입니다.
    🛑 절대 [상황 요약]의 goal 문장이나 따옴표 안 대사를 그대로 복사하거나 서술하지 마세요.
    🛑 goal을 참조해서 캐릭터 대사를 2~3줄 정도 생성하세요.
    🛑 이름, 대사 모두 한국어로 작성하세요.
    🛑 goal은 "상황 요약"일 뿐, 실제 출력 문장이 아닙니다. goal과 동일한 문장, "~라고 말한다" 같은 설명체는 금지입니다.

    ⚠️ 핵심 규칙: 아래 [상황 요약]의 내용만 사용하세요. 다른 장면이나 상황을 창작하지 마세요.

    [현재 스테이지]
    {stage_tag}

    {user_input_block}

    {recent_dialogues_block}

    [상황 요약]
    {beat_lines}

    [등장인물 및 말투]
    {tone_desc}

    [인물 관계 요약]
    {rel_text}

    [스테이지 타입]
    {stage_type or "scene"}

    [현재 턴]
    {stage_turn}

    {objective_block}
    {intent_block}

    {summary_block}

    {long_term_memory_block}

    {first_encounter_text}
    {intro_narr_reminder}

    [중요 지침]

    1. 대사 생성 규칙:
    - ✅ 위 [상황 요약]의 각 beat를 순서대로 처리하되, **goal 텍스트를 그대로 복사·설명하지 말고** 화자 입으로 재구성하세요.
    - ✅ goal은 상황 요약일 뿐입니다. 화자는 자신의 감정, 관찰, 결심을 2~3문장 분량의 생생한 대사로 표현하세요.
    - ✅ narr가 아닌 화자는 순수한 대사만 말합니다. "~라고 말한다", 행동 묘사, 지시문은 출력하지 마세요.
    - 📝 narr만 장면/감각/효과음을 묘사할 수 있으며, 이때도 goal을 복사하지 말고 새롭게 묘사하세요.
    - ❌ [상황 요약]에 없는 장소·시간·인물·사건을 추가하지 마세요.
    - 예시:
        * goal: "렌고쿠가 다가온다" → 대사: "괜찮나? 불길이 삼킬 뻔했군!"
        * goal: "탄지로가 코를 킁킁거린다. '이 냄새… 젠이츠는 뒤쪽 칸에, 이노스케는 앞쪽 기관실 쪽이에요.'"
          → 대사: "이 냄새… 젠이츠는 뒤쪽, 이노스케는 앞쪽이에요. 틀림없어요!"
    ⚙️ [{{{{user}}}} 관련 beat 처리 규칙]
    - goal에 "{{{{user}}}}말에 대답한다" 또는 "{{{{user}}}}가 ~라고 말했다"가 있으면, 이는 **유저의 직전 발화에 답변하라**는 지시입니다.
    - goal 문장 자체나 "{{{{user}}}}" 문자열을 출력하지 말고, 캐릭터가 유저에게 자연스럽게 답하는 대사를 만드세요.
    - 예시: goal "{{{{user}}}}말에 대답한다" → "그렇죠, 지금은 동료를 모으는 게 먼저예요!"
    - ⚠️ "{{{{user}}}}"는 시스템이 유저 이름으로 치환하니 절대 그대로 출력하지 마세요.


    2. 처음 만남 규칙:
    - 관계 정보를 정확히 반영하세요.
    - "처음 만남"인 경우 이름을 모르며, 놀람·경계·호기심으로 반응해야 합니다.
    - "오랜만이야", "또 만났네" 같은 재회 표현 금지.
    - 예시: 아카자가 렌고쿠를 처음 본다면 → "오… 염주인가. 강한 투기가 느껴진다."

    3. narr(내레이션):
    - narr는 장면 묘사·감각·효과음을 담당하며, 캐릭터 대사는 하지 않습니다.
    - 인트로 스테이지에서는 narr가 반드시 첫 번째로 등장해야 합니다.
    - narr는 생략하지 말고, beat에 포함되어 있다면 반드시 생성하세요.

    4. 장면 전진 규칙:
    - [이전 턴 요약]과 사용자 입력을 먼저 읽고, 그 흐름을 자연스럽게 이어가세요.
    - 이미 언급된 문장을 반복하지 말고, 새로운 감정·행동·정보로 장면을 전진시키세요.
    - stage_turn이 0이면 장면을 소개하고, 그 이상이면 기존 전개를 기반으로 긴장감과 감정을 발전시키세요.
    - 스테이지 타입과 목표(예: mission objective, intent 선택지)에 맞춰 플레이어가 다음 행동을 하도록 자연스럽게 유도하세요.
    - 선택지를 제시해야 하는 장면이라면, beats 내용을 바탕으로 플레이어가 답하거나 결정을 내릴 수 있게 질문이나 촉구로 마무리하세요.

    5. 출력 형식 (JSON):
      {{{{
        "dialogues": [{{{{"speaker": "...", "text": "..."}}}}]]
      }}}}
    """
        return prompt.strip()


# ============================================================
# 🧭 Router Prompt Builder (RouterAgent)
# ============================================================
class RouterPromptBuilder:
    """
    RouterAgent에서 사용하는 topic classification 프롬프트 빌더
    """

    @staticmethod
    def build_topic_classification(
        user_input: str,
        scenario_id: str,
        current_stage: str,
        recent_history: str,
    ) -> str:
        """
        Topic classification을 위한 프롬프트 구성

        Args:
            user_input: 사용자 입력
            scenario_id: 시나리오 ID
            current_stage: 현재 스테이지
            recent_history: 최근 대화 기록

        Returns:
            구성된 프롬프트 문자열
        """
        router_prompts = _PROMPTS.get("llm_prompts", {}).get("router", {})
        template = router_prompts.get("topic_classifier_user", "")

        if not template:
            # Fallback
            return f"""사용자 입력: {user_input}
시나리오: {scenario_id}
현재 스테이지: {current_stage}
최근 대화: {recent_history}

이 입력이 시나리오와 관련된 on_topic인지, 무관한 off_topic인지 판별하세요."""

        return template.format(
            text=user_input,
            scenario_id=scenario_id,
            current_stage=current_stage,
            recent_history=recent_history or "(최근 대화 없음)"
        )


# ============================================================
# ✅ Dialogue Validation Prompt Builder (DialogueAgent)
# ============================================================
class DialogueValidationPromptBuilder:
    """
    DialogueAgent에서 사용하는 대사 검증 프롬프트 빌더
    """

    @staticmethod
    def build_validation(
        speaker: str,
        content: str,
        emotion: str,
        affinity_level: str,
        character_info: Dict[str, Any],
        current_scene: str,
        mood: str,
        recent_context: str,
    ) -> str:
        """
        대사 검증을 위한 프롬프트 구성

        Args:
            speaker: 화자
            content: 대사 내용
            emotion: 감정
            affinity_level: 친밀도 레벨
            character_info: 캐릭터 정보
            current_scene: 현재 씬
            mood: 분위기
            recent_context: 최근 대화 맥락

        Returns:
            구성된 프롬프트 문자열
        """
        return f"""캐릭터: {speaker}
캐릭터 성격: {character_info.get('personality', '알 수 없음')}
친밀도 레벨: {affinity_level}
현재 씬: {current_scene}
씬 분위기: {mood}

대사: "{content}"
감정: {emotion}

최근 대화 맥락:
{recent_context}

위 대사를 평가하세요. JSON 형식으로 응답:
{{
  "scores": {{
    "character_consistency": 점수,
    "context_relevance": 점수,
    "emotional_appropriateness": 점수,
    "game_rule_compliance": 점수
  }},
  "total_score": 전체점수,
  "passed": true/false,
  "issues": ["문제점1", "문제점2", ...],
  "suggestions": "개선 제안"
}}"""

    @staticmethod
    def build_correction(
        speaker: str,
        original_content: str,
        emotion: str,
        character_info: Dict[str, Any],
        current_scene: str,
        issues: List[str],
        suggestions: str,
    ) -> str:
        """
        대사 수정을 위한 프롬프트 구성

        Args:
            speaker: 화자
            original_content: 원본 대사
            emotion: 감정
            character_info: 캐릭터 정보
            current_scene: 현재 씬
            issues: 문제점 목록
            suggestions: 개선 제안

        Returns:
            구성된 프롬프트 문자열
        """
        issues_block = "\n".join(f"- {issue}" for issue in issues) if issues else "- 자연스럽게 다듬어 주세요."

        return f"""원본 대사: "{original_content}"
캐릭터: {speaker}
캐릭터 성격: {character_info.get('personality', '')}
감정: {emotion}
씬: {current_scene}

문제점:
{issues_block}

개선 제안: {suggestions}

수정된 대사만 출력하세요 (따옴표 없이):"""


# ============================================================
# 🎯 LLM Beats Prompt Builder (ChildrenAgent - LLM Beats)
# ============================================================
class LLMBeatsPromptBuilder:
    """
    ChildrenAgent의 LLM Beats 생성 프롬프트 빌더
    """

    @staticmethod
    def build(
        previous_stage_summary: str,
        stage_context: str,
        recent_history: List[str],
        latest_user_input: str,
        speaker_pool: List[str],
    ) -> str:
        """
        LLM이 beats를 즉흥 생성하기 위한 프롬프트 구성

        Args:
            previous_stage_summary: 이전 스테이지 요약
            stage_context: 현재 스테이지 맥락
            recent_history: 최근 대화 기록
            latest_user_input: 최근 사용자 입력
            speaker_pool: 등장 가능한 캐릭터

        Returns:
            구성된 프롬프트 문자열
        """
        llm_beats_prompts = _PROMPTS.get("llm_prompts", {}).get("llm_beats", {})
        user_template = llm_beats_prompts.get("user", "")

        if not user_template:
            # Fallback
            return f"""이전 장면: {previous_stage_summary}
현재 상황: {stage_context}
최근 대화: {" | ".join(recent_history[-4:])}
사용자 입력: {latest_user_input}
등장 캐릭터: {", ".join(speaker_pool)}

위 정보를 바탕으로 다음 장면의 beats를 생성하세요."""

        recent_history_str = "\n".join(recent_history[-4:]) if recent_history else "(없음)"

        return user_template.format(
            previous_stage_summary=previous_stage_summary,
            stage_context=stage_context,
            recent_history=recent_history_str,
            latest_user_input=latest_user_input if latest_user_input else "(없음)",
            speaker_pool=", ".join(speaker_pool),
        )


__all__ = [
    "DialoguePromptBuilder",
    "RouterPromptBuilder",
    "DialogueValidationPromptBuilder",
    "LLMBeatsPromptBuilder",
]
