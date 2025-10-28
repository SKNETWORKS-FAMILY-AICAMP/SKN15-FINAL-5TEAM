"""
Intent Handler - 사용자 의도를 LLM으로 정확히 판별
"""
from typing import Any, Dict, Optional

from src.utils.llm_client import get_llm_client


def _build_system_prompt(stage_meta: Dict[str, Any]) -> str:
    lines = ["당신은 스토리 진행을 돕는 의도 판별 AI입니다."]
    description = stage_meta.get("description")
    if isinstance(description, str) and description.strip():
        lines.append(description.strip())
    lines.append("아래 선택지 중 하나로 분류하세요:")
    lines.append("반드시 JSON 형식(JSON object)으로 응답하세요.")

    options = stage_meta.get("options") or {}
    if isinstance(options, dict):
        for intent_key, intent_desc in options.items():
            if not isinstance(intent_key, str):
                continue
            if isinstance(intent_desc, str) and intent_desc.strip():
                lines.append(f"- {intent_key}: {intent_desc.strip()}")
            else:
                lines.append(f"- {intent_key}")
    return "\n".join(lines)


def detect_intent_with_llm(
    state: Dict[str, Any],
    user_input: str,
    stage_tag: Optional[str] = None,
) -> Optional[str]:
    """
    LLM 기반 의도 판별. 시나리오 메타데이터에 정의된 옵션을 사용한다.

    Args:
        state: 현재 대화 상태.
        user_input: 사용자의 입력 문자열.
        stage_tag: 의도를 판별하고자 하는 스테이지 태그(생략 시 현재 스테이지 사용).
    """
    scene = state.get("scene", {})
    current_stage = (
        stage_tag
        or state.get("current_stage")
        or scene.get("current_scene")
        or ""
    )
    current_stage = str(current_stage).upper()
    if not current_stage:
        return None

    scenario = state.get("scenario") or state.get("scenario_data") or {}
    metadata = scenario.get("metadata") if isinstance(scenario, dict) else {}
    intents_meta = metadata.get("intents") or {}
    if not isinstance(intents_meta, dict):
        return None

    # intents 메타는 대소문자 혼용될 수 있으므로 키 정규화
    normalized_meta = {str(k).upper(): v for k, v in intents_meta.items()}
    stage_meta = normalized_meta.get(current_stage)
    if not isinstance(stage_meta, dict):
        return None

    options = stage_meta.get("options") or {}
    if not isinstance(options, dict) or not options:
        return None

    system_prompt = _build_system_prompt(stage_meta)
    prompt_user_input = (user_input or "").strip()
    user_prompt = (
        f'사용자 입력: "{prompt_user_input}"\n'
        '응답 형식 (JSON): {"intent": "<옵션 키>"}'
    )

    try:
        client = get_llm_client()
        response = client.call_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=client.get_agent_setting("intent_handler", "temperature", 0.1),
            max_tokens=client.get_agent_setting("intent_handler", "max_tokens", None),
            agent="intent_handler",
        )
    except Exception as exc:
        print(f"[INTENT_HANDLER] LLM failed: {exc}")
        return None

    intent_raw = (response or {}).get("intent")
    if not isinstance(intent_raw, str):
        return None

    normalized = intent_raw.strip().lower()
    valid_intents = {str(key).lower(): str(key) for key in options.keys()}
    intent = valid_intents.get(normalized)
    if intent:
        print(f"[INTENT_HANDLER] LLM detected: {intent}")
    return intent


__all__ = ["detect_intent_with_llm"]
