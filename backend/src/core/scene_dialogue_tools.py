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

    # --- 관계 요약 ---
    rel_desc = []
    for name, tone in tone_profiles.items():
        rels = tone.get("relationships", {})
        for target, info in rels.items():
            rel_desc.append(f"- {name} ↔ {target}: {info.get('description', '')}")
    rel_text = "\n".join(rel_desc)

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

    [지침]
    - 대사는 각 인물의 말투(tone)에 맞춰 자연스럽게 확장합니다. 2~3줄 출력합니다.
    - 관계 정보를 반영해, 감정의 결을 유지합니다.
    - 'narr'는 내레이션으로, 전투와 감정의 흐름을 묘사합니다.
    - 출력은 JSON 형식:
      {{
        "dialogues": [{{"speaker": "...", "text": "..."}}]
      }}
    """
    return prompt.strip()
