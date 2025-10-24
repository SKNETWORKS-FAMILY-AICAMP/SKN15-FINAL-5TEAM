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

    # INTRO 스테이지 감지 및 첫 narr 체크
    is_intro = "INTRO" in stage_tag.upper()
    has_narr_beat = any(
        b.get("speaker", "").lower() == "narr"
        for b in beats
    )
    intro_narr_reminder = ""
    if is_intro and has_narr_beat:
        intro_narr_reminder = """
    ⭐ INTRO 스테이지 필수 요구사항:
    - 반드시 narr(내레이션)으로 시작해야 합니다
    - 첫 번째 dialogue는 무조건 speaker: "narr"이어야 합니다
    - narr는 장면의 배경, 분위기, 환경을 생생하게 묘사합니다
    """

    prompt = f"""
    당신은 Demon Slayer: 무한열차 시나리오의 대사 작가입니다.
    🛑 절대 [상황 요약]의 goal 문장이나 따옴표 안 대사를 그대로 복사하거나 서술하지 마세요.
    🛑 goal을 참조해서 캐릭터 대사를 2~3줄 정도 생성하세요.
    🛑  이름, 대사 모두 한국어로 작성하세요. 
    🛑 goal은 “상황 요약”일 뿐, 실제 출력 문장이 아닙니다. goal과 동일한 문장, "~라고 말한다" 같은 설명체는 금지입니다.

    ⚠️ 핵심 규칙: 아래 [상황 요약]의 내용만 사용하세요. 다른 장면이나 상황을 창작하지 마세요.

    [현재 스테이지]
    {stage_tag}

    [상황 요약] ← 이것만 사용!
    {beat_lines}

    [등장인물 및 말투]
    {tone_desc}

    [인물 관계 요약]
    {rel_text}

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
    ⚙️ [{{user}} 관련 beat 처리 규칙]
    - goal에 "{{user}}말에 대답한다" 또는 "{{user}}가 ~라고 말했다"가 있으면, 이는 **유저의 직전 발화에 답변하라**는 지시입니다.
    - goal 문장 자체나 "{{user}}" 문자열을 출력하지 말고, 캐릭터가 유저에게 자연스럽게 답하는 대사를 만드세요.
    - 예시: goal "{{user}}말에 대답한다" → "그렇죠, 지금은 동료를 모으는 게 먼저예요!"
    - ⚠️ "{{user}}"는 시스템이 유저 이름으로 치환하니 절대 그대로 출력하지 마세요.


    2. 처음 만남 규칙:
    - 관계 정보를 정확히 반영하세요.
    - "처음 만남"인 경우 이름을 모르며, 놀람·경계·호기심으로 반응해야 합니다.
    - “오랜만이야”, “또 만났네” 같은 재회 표현 금지.
    - 예시: 아카자가 렌고쿠를 처음 본다면 → "오… 염주인가. 강한 투기가 느껴진다."

    3. narr(내레이션):
    - narr는 장면 묘사·감각·효과음을 담당하며, 캐릭터 대사는 하지 않습니다.
    - INTRO에서는 narr가 반드시 첫 번째로 등장해야 합니다.
    - narr는 생략하지 말고, beat에 포함되어 있다면 반드시 생성하세요.

    4. 출력 형식 (JSON):
      {{
        "dialogues": [{{"speaker": "...", "text": "..."}}]
      }}
    """
    return prompt.strip()
