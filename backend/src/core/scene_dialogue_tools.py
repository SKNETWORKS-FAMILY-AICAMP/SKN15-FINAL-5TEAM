"""
SceneDialogueTools - 톤/대사/프롬프트 관리
- 캐릭터 tone_profile 로드
- beats + tone_profiles 기반 LLM 프롬프트 구성
"""

from pathlib import Path
import json
from typing import Dict, Any, List, Optional

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

def compose_llm_prompt(stage_tag: str, beats: List[Dict[str, Any]], tone_profiles: Dict[str, Any], speaker_pool: List[str]) -> str:
    """
    tone_profiles + beats + 관계 정보를 포함한 LLM 프롬프트
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

    # 처음 만남 경고 메시지 생성
    first_encounter_notes = []
    if first_encounter_pairs:
        first_encounter_notes.append("=" * 60)
        first_encounter_notes.append("🚨 처음 만남 주의사항 🚨")
        first_encounter_notes.append("=" * 60)
        for pair in sorted(first_encounter_pairs):
            first_encounter_notes.append(f"⚠️ {pair[0]}와 {pair[1]}는 이 장면에서 처음 만납니다!")
        first_encounter_notes.append("")
        first_encounter_notes.append("처음 만나는 캐릭터들은:")
        first_encounter_notes.append("- 서로의 이름을 모릅니다 (이름을 부르지 마세요!)")
        first_encounter_notes.append("- 처음 보는 반응을 보여야 합니다 (놀람, 경계, 호기심)")
        first_encounter_notes.append("- 재회 표현 금지 ('또 만났네', '오랜만이야' 등)")
        first_encounter_notes.append("=" * 60)

    rel_text = "\n".join(rel_desc)
    first_encounter_text = "\n".join(first_encounter_notes) if first_encounter_notes else ""

    # --- beats ---
    beat_lines = "\n".join(f"- {b.get('goal', '')}" for b in beats)

    prompt = f"""
    당신은 Demon Slayer: 무한열차 시나리오의 대사 작가입니다.

    [현재 스테이지]
    {stage_tag}

    [상황 요약]
    {beat_lines}

    [등장인물 및 말투]
    {tone_desc}

    [인물 관계 요약]
    {rel_text}

    {first_encounter_text}

    [중요 지침]
    - 대사는 각 인물의 말투(tone)에 맞춰 자연스럽게 확장합니다.
    - 관계 정보를 정확히 반영해야 합니다. 특히 "처음 만남"이 명시된 경우:
      * 서로의 이름을 모르는 상태입니다
      * 상대방을 처음 보는 반응(놀람, 경계, 호기심)을 보여야 합니다
      * "오랜만이야", "또 만났네" 같은 재회 표현을 절대 사용하지 마세요
      * 예: 아카자가 렌고쿠를 처음 본다면 "오… 염주인가. 강한 투기가 느껴진다." (이름 모름)
    - 'narr'는 내레이션으로, 전투와 감정의 흐름을 묘사합니다.
    - 출력은 JSON 형식:
      {{
        "dialogues": [{{"speaker": "...", "text": "..."}}]
      }}
    """
    return prompt.strip()
