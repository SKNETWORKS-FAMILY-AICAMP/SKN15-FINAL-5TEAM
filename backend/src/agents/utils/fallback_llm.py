from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.utils.llm_client import get_llm_client

from .logger import log

_BASE_DIR = Path(__file__).resolve().parents[3]
_CANDIDATE_CHAR_DIRS = [
    _BASE_DIR / "data" / "character_data",
    _BASE_DIR / "data" / "characters",
]
_CHAR_DB_PATH = _BASE_DIR / "data" / "characters_db.json"


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
    fallback_speakers = ["tanjiro", "rengoku", "inosuke", "zenitsu"]
    candidates = [sp for sp in speaker_pool if isinstance(sp, str)] or fallback_speakers
    character = random.choice(candidates)

    profile = _load_character_profile(character)
    if not profile:
        text = "지금은 임무에 집중해야 해요. 나중에 이야기해요!"
        return {
            "speaker": character,
            "text": text,
            "from_fallback_llm": False,
        }

    name = _coalesce((profile.get("name"), character.capitalize()))
    style = _extract_style(profile)

    system_prompt = (
        f"You are {name}, a character from Demon Slayer. "
        "Respond in Korean, in 1-2 concise sentences. "
        "Stay fully in character, gently guiding the player back to the current mission."
    )

    system_prompt += (
        f"\nTone guidance: {style['tone']}"
        f"\nSpeech style: {style['speech_pattern']}"
        f"\nMannerisms: {style['mannerisms']}"
    )

    stage = state.get("current_stage") or (scene.get("current_stage") or "")
    mission_hint = state.get("mission_hint") or ""

    user_prompt = (
        "사용자가 시나리오와 무관한 이야기를 했습니다.\n"
        f"현재 스테이지: {stage or '알 수 없음'}\n"
        f"사용자 입력: \"{user_input}\"\n"
        f"미션 힌트: {mission_hint}\n"
        "캐릭터의 말투로 부드럽게 주의를 돌려주세요."
    )

    try:
        client = get_llm_client()
        response_text = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=80,
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
    candidates = [sp for sp in speaker_pool if isinstance(sp, str)]
    if not candidates:
        candidates = ["tanjiro"]
    character = random.choice(candidates)

    profile = _load_character_profile(character)
    if not profile:
        return {
            "speaker": character,
            "text": "지금은 임무에 집중해야 해요. 서둘러 주세요!",
            "from_fallback_llm": False,
        }

    name = _coalesce((profile.get("name"), character.capitalize()))
    style = _extract_style(profile)

    atmosphere = stage.get("atmosphere") or scene.get("atmosphere") or "unknown"
    stage_tag = stage.get("tag") or stage.get("id") or (state.get("current_stage") or "unknown")

    system_prompt = (
        "너는 현재 시나리오 속 캐릭터야.\n"
        "사용자가 스토리와 관련 없는 말을 했지만, 직접 화를 내지 않고,\n"
        "상황에 맞는 말투로 다시 스토리로 유도해야 해.\n"
        f"현재 분위기: {atmosphere}\n"
        f"참여 캐릭터: {', '.join(candidates)}\n"
        f"현재 스테이지: {stage_tag}\n"
        "tone과 감정은 각 캐릭터 json 데이터의 tone_profile을 참고.\n"
        "한 명의 캐릭터가 자연스럽게 1-2문장으로 반응해.\n"
        "시스템 톤(경고 메시지, 문구)은 사용하지 마.\n"
    )

    system_prompt += (
        f"\n배역: {name}"
        f"\n말투 가이드: {style['tone']}"
        f"\n말하는 스타일: {style['speech_pattern']}"
        f"\n버릇/행동: {style['mannerisms']}"
    )

    recent_turns = "\n".join(_recent_dialogue_turns(state, limit=3)) or "대화 기록 없음"

    user_prompt = (
        f"최근 대화:\n{recent_turns}\n\n"
        f"사용자 발화: \"{user_input}\"\n"
        "캐릭터로서 자연스럽게 반응하고, 상황으로 복귀하도록 유도해."
    )

    try:
        client = get_llm_client()
        response_text = client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=90,
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
