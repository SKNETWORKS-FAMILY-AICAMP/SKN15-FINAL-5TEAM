from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.utils.llm_client import get_llm_client
from src.tools.scene_tools import get_stage_atmosphere
from src.utils.config_loader import get_config_loader

from .logger import log

_BASE_DIR = Path(__file__).resolve().parents[3]
_CANDIDATE_CHAR_DIRS = [
    _BASE_DIR / "data" / "character_data",
    _BASE_DIR / "data" / "characters",
]
_CHAR_DB_PATH = _BASE_DIR / "data" / "characters_db.json"
_PROMPTS = get_config_loader().get_prompts()
_FALLBACK_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("fallback") or {})
_OFF_TOPIC_BASE_TEMPLATE = (_FALLBACK_PROMPTS.get("off_topic_base") or "").strip()
_URGENT_OFF_TOPIC_BASE_TEMPLATE = (_FALLBACK_PROMPTS.get("urgent_off_topic_base") or "").strip()
if not _OFF_TOPIC_BASE_TEMPLATE:
    raise ValueError("Fallback off_topic_base prompt missing in configs/prompts.yaml (llm_prompts.fallback.off_topic_base).")
if not _URGENT_OFF_TOPIC_BASE_TEMPLATE:
    raise ValueError("Fallback urgent_off_topic_base prompt missing in configs/prompts.yaml (llm_prompts.fallback.urgent_off_topic_base).")


def _load_character_profile(character: str) -> Optional[Dict[str, Any]]:
    key = character.lower()

    for char_dir in _CANDIDATE_CHAR_DIRS:
        file_path = char_dir / f"{key}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - file parsing defensive
                log("fallback_llm", f"Failed to read {file_path}: {exc}")
                continue

            if isinstance(data, dict) and "characters" in data:
                inner = data.get("characters") or {}
                if isinstance(inner, dict):
                    profile = inner.get(key)
                    if isinstance(profile, dict):
                        return profile
            if isinstance(data, dict):
                return data

    if _CHAR_DB_PATH.exists():
        try:
            db = json.loads(_CHAR_DB_PATH.read_text(encoding="utf-8"))
            if isinstance(db, dict):
                profile = db.get(key)
                if isinstance(profile, dict):
                    return profile
        except Exception as exc:  # pragma: no cover
            log("fallback_llm", f"Failed to read character_db.json: {exc}")

    return None


def _coalesce(values: Iterable[Optional[str]]) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_style(profile: Dict[str, Any]) -> Dict[str, str]:
    tone_section = profile.get("tone")
    if isinstance(tone_section, dict):
        if all(isinstance(v, (str, list)) for v in tone_section.values()):
            tone_description = "; ".join(
                str(v) for v in tone_section.values() if v
            )
        else:
            described: list[str] = []
            for key, info in tone_section.items():
                if isinstance(info, dict) and info.get("style"):
                    described.append(f"{key}: {info['style']}")
            tone_description = "; ".join(described)
    else:
        tone_description = _coalesce(
            (
                profile.get("tone_description"),
                profile.get("personality"),
                profile.get("description"),
            )
        )

    speech_pattern = _coalesce(
        (
            profile.get("speech_pattern"),
            ", ".join(profile.get("speech_patterns", []))
            if isinstance(profile.get("speech_patterns"), list)
            else None,
            tone_description,
        )
    )

    mannerisms = _coalesce(
        (
            profile.get("mannerisms"),
            profile.get("mannerism"),
            profile.get("mannerisms_summary"),
        )
    )

    if not tone_description:
        tone_description = speech_pattern or "따뜻하고 결연한 말투"

    if not speech_pattern:
        speech_pattern = profile.get("personality", "정중하고 단호한 어투")

    if not mannerisms:
        mannerisms = "진심을 담아 상대를 격려함"

    return {
        "tone": tone_description,
        "speech_pattern": speech_pattern,
        "mannerisms": mannerisms,
    }


def generate_off_topic_response(
    state: Dict[str, Any],
    user_input: str,
) -> Optional[Dict[str, Any]]:
    scene = state.get("scene") or {}
    speaker_pool = scene.get("speaker_pool") or []

    scenario = state.get("scenario") or state.get("scenario_data") or {}
    metadata = scenario.get("metadata") if isinstance(scenario, dict) else {}
    fallback_meta = metadata.get("fallback") or {}
    tone_meta = metadata.get("tone") or {}

    exclude_speakers = {
        str(name).lower()
        for name in (fallback_meta.get("exclude_speakers") or [])
        if isinstance(name, str)
    }
    exclude_speakers.update({"akaza", "narr"})  # 안전 장치

    fallback_speakers = [
        str(name) for name in (fallback_meta.get("fallback_speakers") or []) if isinstance(name, str)
    ] or ["tanjiro"]

    candidates = [
        sp for sp in speaker_pool
        if isinstance(sp, str) and sp.lower() not in exclude_speakers
    ] or fallback_speakers
    character = random.choice(candidates)

    log("fallback_llm", f"Selected speaker for off-topic: {character} (pool: {speaker_pool})")

    # scenario_specific 정보 추출
    scenario_key = tone_meta.get("scenario_key")

    profile = _load_character_profile(character)
    if not profile:
        log("fallback_llm", f"⚠️ Failed to load profile for {character} - using system message")
        text = "지금은 임무에 집중해야 해요. 나중에 이야기해요!"
        return {
            "speaker": character,
            "text": text,
            "from_fallback_llm": False,
        }

    name = _coalesce((profile.get("name"), character.capitalize()))
    style = _extract_style(profile)

    # scenario_specific tone/relationships 로드
    relationships = {}
    if scenario_key and "scenario_specific" in profile:
        scenario_data = profile.get("scenario_specific", {}).get(scenario_key, {})
        if scenario_data:
            relationships = scenario_data.get("relationships", {})

    relationships_section = ""
    if relationships:
        rel_desc = []
        for target, info in relationships.items():
            desc = info.get('description', '')
            if desc:
                rel_desc.append(f"{target}: {desc}")
        if rel_desc:
            relationships_section = f"Relationships: {'; '.join(rel_desc[:3])}"  # 최대 3개

    system_prompt = _OFF_TOPIC_BASE_TEMPLATE.format(
        name=name,
        tone=style['tone'],
        speech_pattern=style['speech_pattern'],
        mannerisms=style['mannerisms'],
        relationships_section=relationships_section,
    )
    stage = state.get("current_stage") or (scene.get("current_stage") or "")
    mission_hint = state.get("mission_hint") or ""

    user_prompt = (
        "사용자가 시나리오와 무관한 이야기를 했습니다.\n"
        f"현재 스테이지: {stage or '알 수 없음'}\n"
        f"사용자 입력: \"{user_input}\"\n"
        f"미션 힌트: {mission_hint}\n"
        "캐릭터의 말투와 현재 관계성을 반영하여 부드럽게 주의를 돌려주세요."
    )

    try:
        client = get_llm_client()
        temperature = client.get_agent_setting("fallback", "temperature", 0.8)
        max_tokens = client.get_agent_setting("fallback", "max_tokens", 80)
        response_text = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            agent="fallback",
        )
        text = response_text.strip()
        if not text:
            raise ValueError("Empty fallback response")
        log("fallback_llm", f"Generated tone-based fallback for {character}")
        return {
            "speaker": character,
            "text": text,
            "from_fallback_llm": True,
        }
    except Exception as exc:  # pragma: no cover - firewall for API issues
        log("fallback_llm", f"LLM fallback failed: {exc}")
        return {
            "speaker": character,
            "text": "지금은 전투에 집중하자. 이야기는 나중에 이어가요.",
            "from_fallback_llm": False,
        }


def _recent_dialogue_turns(state: Dict[str, Any], limit: int = 3) -> List[str]:
    history: List[str] = []
    output_dialogues = (state.get("output") or {}).get("dialogues") or []
    if isinstance(output_dialogues, list):
        history.extend(
            f"{item.get('speaker', 'unknown')}: {item.get('text', '')}"
            for item in output_dialogues
            if isinstance(item, dict)
        )

    agent_responses = state.get("agent_responses") or []
    if isinstance(agent_responses, list):
        history.extend(
            f"{item.get('speaker', 'unknown')}: {item.get('text', '')}"
            for item in agent_responses
            if isinstance(item, dict)
        )

    message_history = state.get("message_history") or []
    if isinstance(message_history, list):
        for entry in message_history:
            if isinstance(entry, dict):
                speaker = entry.get("speaker") or entry.get("role")
                content = entry.get("text") or entry.get("content")
                if speaker and content:
                    history.append(f"{speaker}: {content}")

    trimmed = history[-limit:]
    return trimmed


def generate_stage_fallback(
    state: Dict[str, Any],
    stage: Dict[str, Any],
    user_input: str,
) -> Optional[Dict[str, Any]]:
    scene = state.get("scene") or {}
    speaker_pool = stage.get("speaker_pool") or scene.get("speaker_pool") or []
    if not speaker_pool:
        speaker_pool = ["tanjiro", "rengoku"]

    scenario = state.get("scenario") or state.get("scenario_data") or {}
    metadata = scenario.get("metadata") if isinstance(scenario, dict) else {}
    fallback_meta = metadata.get("fallback") or {}
    tone_meta = metadata.get("tone") or {}

    exclude_speakers = {
        str(name).lower()
        for name in (fallback_meta.get("exclude_speakers") or [])
        if isinstance(name, str)
    }
    exclude_speakers.update({"akaza", "narr"})

    candidates = [
        sp for sp in speaker_pool
        if isinstance(sp, str) and sp.lower() not in exclude_speakers
    ]
    if not candidates:
        candidates = [str(name) for name in (fallback_meta.get("fallback_speakers") or ["tanjiro"])]
    character = random.choice(candidates)

    scenario_key = tone_meta.get("scenario_key")

    profile = _load_character_profile(character)
    if not profile:
        return {
            "speaker": character,
            "text": "지금은 임무에 집중해야 해요. 서둘러 주세요!",
            "from_fallback_llm": False,
        }

    name = _coalesce((profile.get("name"), character.capitalize()))
    style = _extract_style(profile)

    # scenario_specific tone/relationships 로드
    relationships = {}
    if scenario_key and "scenario_specific" in profile:
        scenario_data = profile.get("scenario_specific", {}).get(scenario_key, {})
        if scenario_data:
            relationships = scenario_data.get("relationships", {})

    # atmosphere를 정규화된 문자열로 가져오기
    atmosphere = get_stage_atmosphere(stage) or get_stage_atmosphere(scene) or "unknown"
    stage_tag = stage.get("tag") or stage.get("id") or (state.get("current_stage") or "unknown")

    # atmosphere를 사람이 읽기 좋은 형태로 변환
    atmosphere_display = {
        "urgent": "긴급/자동전이",
        "tense": "긴장/전투",
        "calm": "차분함",
        "normal": "일반/자유발화"
    }.get(atmosphere, atmosphere)

    # 관계성 정보 추가
    relationships_section = ""
    if relationships:
        rel_desc = []
        for target, info in relationships.items():
            desc = info.get('description', '')
            if desc:
                rel_desc.append(f"{target}: {desc}")
        if rel_desc:
            relationships_section = f"캐릭터 관계: {'; '.join(rel_desc[:3])}"

    system_prompt = _URGENT_OFF_TOPIC_BASE_TEMPLATE.format(
        atmosphere_display=atmosphere_display,
        participants=", ".join(candidates),
        stage_tag=stage_tag,
        name=name,
        tone=style['tone'],
        speech_pattern=style['speech_pattern'],
        mannerisms=style['mannerisms'],
        relationships_section=relationships_section,
    )

    recent_turns = "\n".join(_recent_dialogue_turns(state, limit=3)) or "대화 기록 없음"

    user_prompt = (
        f"최근 대화:\n{recent_turns}\n\n"
        f"사용자 발화: \"{user_input}\"\n"
        "캐릭터로서 자연스럽게 반응하고, 상황으로 복귀하도록 유도해."
    )

    try:
        client = get_llm_client()
        urgent_temperature = client.get_agent_setting(
            "fallback",
            "urgent_temperature",
            client.get_agent_setting("fallback", "temperature", 0.75),
        )
        urgent_max_tokens = client.get_agent_setting(
            "fallback",
            "urgent_max_tokens",
            client.get_agent_setting("fallback", "max_tokens", 90),
        )
        response_text = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=urgent_temperature,
            max_tokens=urgent_max_tokens,
            agent="fallback",
        )
        text = response_text.strip()
        if not text:
            raise ValueError("Empty fallback response")
        log("fallback_llm", f"Generated urgent fallback for {character}")
        return {
            "speaker": character,
            "text": text,
            "from_fallback_llm": True,
        }
    except Exception as exc:  # pragma: no cover
        log("fallback_llm", f"Urgent LLM fallback failed: {exc}")
        return {
            "speaker": character,
            "text": "지금은 시간을 낭비할 수 없어. 곧장 임무로 돌아가자!",
            "from_fallback_llm": False,
        }


__all__ = ["generate_off_topic_response", "generate_stage_fallback"]
