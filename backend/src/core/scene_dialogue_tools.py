"""
SceneDialogueTools - 톤/대사/프롬프트 관리
- 캐릭터 tone_profile 로드
- beats + tone_profiles 기반 LLM 프롬프트 구성
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config.constants import INTRO_STAGE_TAGS
from src.utils.config_loader import get_config_loader

# 프롬프트 템플릿 로드
_CONFIG_LOADER = get_config_loader()
_PROMPTS = _CONFIG_LOADER.get_prompts()
_SCENE_DIALOGUE_PROMPTS = _PROMPTS.get("llm_prompts", {}).get("scene_dialogue", {})

def load_tone_profiles(
    character_refs: Dict[str, str],
    scenario_key: Optional[str] = None,
) -> Dict[str, Any]:
    """캐릭터 tone_profile + 시나리오별 확장 tone 정보 로드"""
    profiles = {}
    base_dir = Path(__file__).resolve().parents[3]

    for name, rel_path in character_refs.items():
        path = Path(rel_path)
        if not path.is_absolute():
            path = base_dir / path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            # tone 또는 tone_profile 추출
            tone = (
                data.get("tone_profile")
                or data.get("tone")
                or data.get("characters", {}).get(name, {}).get("tone")
            )

            # 🔥 추가: 시나리오별 tone/roles/relationships 병합
            scenario_specific_map = data.get("scenario_specific", {})
            scenario_specific = {}
            if isinstance(scenario_specific_map, dict):
                if scenario_key and scenario_key in scenario_specific_map:
                    scenario_specific = scenario_specific_map.get(scenario_key, {})
                elif "mugen_train" in scenario_specific_map:
                    scenario_specific = scenario_specific_map.get("mugen_train", {})
                elif "default" in scenario_specific_map:
                    scenario_specific = scenario_specific_map.get("default", {})
                elif scenario_specific_map:
                    # Fallback to the first available scenario block.
                    first_key = next(iter(scenario_specific_map))
                    scenario_specific = scenario_specific_map.get(first_key, {})
            merged_profile = {
                "tone": tone,
                "roles": scenario_specific.get("roles", {}),
                "relationships": scenario_specific.get("relationships", {})
            }

            profiles[name] = merged_profile
        except Exception as e:
            profiles[name] = {}
    return profiles

def compose_llm_prompt(
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
    stage_context: Optional[str] = None,
    world_context: Optional[str] = None,
    conversation_summary: Optional[str] = None,  # 🧠 장기기억 요약
    previous_scene_summary: Optional[str] = None,  # 🔗 이전 장면 요약
    previous_emotional_tone: Optional[str] = None,  # 🔗 이전 감정 톤
    previous_spatial_context: Optional[str] = None,  # 🔗 공간 연속성
    previous_character_states: Optional[str] = None,  # 🔗 캐릭터 상태
    transition_hint: Optional[str] = None,  # 🔗 전환 힌트
    previous_user_input: Optional[str] = None,  # 🔗 이전 유저 입력
) -> str:
    """
    tone_profiles + beats + 관계 정보 + 세계관 정보를 포함한 LLM 프롬프트
    """
    # --- tone 요약 ---
    tone_desc = "\n".join(
        f"- {name}: {tone.get('tone', {}).get('mid', {}).get('style', '중립적 어투')}"
        for name, tone in tone_profiles.items()
    )

    # --- 관계 요약 (처음 만남 여부 강조) ---
    rel_desc = []
    first_encounter_pairs = set()  # 중복 제거용

    for name, tone in tone_profiles.items():
        rels = tone.get("relationships", {})
        for target, info in rels.items():
            description = info.get('description', '')
            rel_type = info.get('type', '')
            rel_desc.append(f"- {name} ↔ {target} ({rel_type}): {description}")

            # "처음", "첫", "조우" 등의 키워드로 처음 만남 감지
            if any(keyword in description for keyword in ["처음", "첫", "조우", "첫 만남", "first"]):
                # 양방향 관계이므로 정렬하여 중복 제거
                pair = tuple(sorted([name, target]))
                first_encounter_pairs.add(pair)

    # 처음 만남 경고 메시지 생성 (템플릿 기반)
    first_encounter_notes = []
    if first_encounter_pairs:
        header = _SCENE_DIALOGUE_PROMPTS.get("first_encounter_header", "")
        footer = _SCENE_DIALOGUE_PROMPTS.get("first_encounter_footer", "")

        first_encounter_notes.append(header)
        for pair in sorted(first_encounter_pairs):
            first_encounter_notes.append(f"⚠️ {pair[0]}와 {pair[1]}는 이 장면에서 처음 만납니다!")
        first_encounter_notes.append(footer)

    rel_text = "\n".join(rel_desc)
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

    # 인트로 스테이지 감지 및 첫 narr 체크 (템플릿 기반)
    intro_stage_aliases = {tag.upper() for tag in INTRO_STAGE_TAGS}
    is_intro = stage_tag.upper() in intro_stage_aliases
    has_narr_beat = any(
        b.get("speaker", "").lower() == "narr"
        for b in beats
    )
    intro_narr_reminder = ""
    if is_intro and has_narr_beat:
        intro_narr_reminder = _SCENE_DIALOGUE_PROMPTS.get("intro_narr_reminder", "")

    summary_block = ""
    if context_summary:
        summary_block = f"""
    [이전 턴 요약]
    {context_summary}
    """

    # 🧠 장기기억 블록 추가
    long_term_memory_block = ""
    if conversation_summary:
        long_term_memory_block = f"""
    [장기기억 - 이전 대화 요약]
    {conversation_summary}

    ⚠️ 위의 장기기억 요약은 오래된 대화의 핵심 내용입니다.
    이 정보를 참고하여 캐릭터 관계, 중요한 사건, 친밀도 변화 등을 이해하세요.
    """

    user_input_block = ""
    if latest_user_input:
        user_input_block = f"""
    [사용자 입력]
    {latest_user_input}
    """

    recent_dialogues_block = ""
    if recent_dialogues:
        recent_dialogues_block = f"""
    [최근 대화]
    {"; ".join(recent_dialogues)}
    """

    # 세계관 설정 블록 (템플릿 기반)
    world_context_block = ""
    if world_context:
        template = _SCENE_DIALOGUE_PROMPTS.get("world_context_block", "")
        world_context_block = template.format(world_context=world_context)

    # 장면 설정 블록 (템플릿 기반)
    scene_context_block = ""
    if stage_context:
        template = _SCENE_DIALOGUE_PROMPTS.get("scene_context_block", "")
        scene_context_block = template.format(stage_context=stage_context)

    # 🔗 서사 연속성 블록 (이전 장면 정보)
    continuity_block = ""
    if any([previous_scene_summary, previous_emotional_tone, previous_spatial_context, previous_character_states, transition_hint, previous_user_input]):
        continuity_parts = []
        continuity_parts.append("=" * 60)
        continuity_parts.append("🚨 **서사 연속성 정보** 🚨")
        continuity_parts.append("이것은 '새로운 장면'이 아니라 '이전 장면의 연속'입니다!")
        continuity_parts.append("Stage가 바뀌었다고 해서 시간이 리셋되는 것이 아닙니다!")
        continuity_parts.append("=" * 60)

        if previous_scene_summary:
            continuity_parts.append(f"\n📖 [이전 장면 요약]: {previous_scene_summary}")

        if previous_user_input:
            continuity_parts.append(f"💬 [이전 유저 발화]: \"{previous_user_input}\"")
            continuity_parts.append("   ⚠️ 이 발화는 이전 장면에서 유저가 한 질문/요청입니다!")
            continuity_parts.append("   ⚠️ 첫 대사에서 이 발화의 의도/맥락을 자연스럽게 연결하세요!")

        if previous_emotional_tone:
            continuity_parts.append(f"😶 [이전 감정 톤]: {previous_emotional_tone}")

        if previous_spatial_context:
            continuity_parts.append(f"📍 [공간 연속성]: {previous_spatial_context}")

        if previous_character_states:
            continuity_parts.append(f"👥 [캐릭터 상태]: {previous_character_states}")

        if transition_hint:
            continuity_parts.append(f"➡️ [전환 힌트]: {transition_hint}")

        continuity_parts.append("\n" + "=" * 60)
        continuity_parts.append("💥 절대 규칙:")
        continuity_parts.append("1. 첫 narr는 반드시 [이전 장면 요약]의 마지막 상황을 언급하세요")
        if previous_user_input:
            continuity_parts.append(f"2. [이전 유저 발화]가 있다면, 그 맥락을 첫 1~2개 대사에서 처리하세요")
            continuity_parts.append("3. [이전 감정 톤]을 유지하거나 점진적으로 변화시키세요")
            continuity_parts.append("4. 이미 등장한 캐릭터를 다시 소개하지 마세요")
            continuity_parts.append("5. 시간 연결어를 사용하세요: '그때', '그 순간', '말을 마치자', '잠시 후'")
        else:
            continuity_parts.append("2. [이전 감정 톤]을 유지하거나 점진적으로 변화시키세요")
            continuity_parts.append("3. 이미 등장한 캐릭터를 다시 소개하지 마세요")
            continuity_parts.append("4. 시간 연결어를 사용하세요: '그때', '그 순간', '말을 마치자', '잠시 후'")
        continuity_parts.append("=" * 60)

        continuity_block = "\n" + "\n".join(continuity_parts) + "\n"

    # 템플릿 기반 프롬프트 조립
    header = _SCENE_DIALOGUE_PROMPTS.get("header", "")
    instructions = _SCENE_DIALOGUE_PROMPTS.get("instructions", "")

    prompt = f"""
    {header}

    [현재 스테이지]
    {stage_tag}

    {world_context_block}

    {scene_context_block}

    {continuity_block}

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

    {instructions}
    """
    return prompt.strip()
