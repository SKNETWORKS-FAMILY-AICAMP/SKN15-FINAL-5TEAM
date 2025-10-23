
from typing import Dict, List, Any, Optional

def _replace_placeholders(text: str, user_name: str = "여행자") -> str:
    """플레이스홀더 치환: {character_id}, {{user}} 등을 실제 이름으로 변환"""
    if not text:
        return text

    character_names = {
        "rengoku": "렌고쿠",
        "tanjiro": "탄지로",
        "akaza": "아카자",
        "zenitsu": "젠이츠",
        "inosuke": "이노스케",
        "nezuko": "네즈코",
        "user": user_name
    }

    for char_id, char_name in character_names.items():
        text = text.replace(f"{{{char_id}}}", char_name)
    text = text.replace("{{user}}", user_name)

    return text

def generate_dialogues_from_context_llm(ctx: Dict, *, user_name: str = "여행자") -> List[Dict]:
    """
    LLM 기반 대화 생성 (cutscene5_llm_driven.json 전용)
    - Parent Agent가 준비한 beats_i18n을 활용하여 자연스러운 대화 생성
    """
    characters = ctx.get("characters") or []
    if not characters:
        print("[CHILDREN_LLM] No characters provided")
        return []

    utterances: List[Dict[str, str]] = []

    for char_info in characters:
        char_id = char_info.get("id")
        if not char_id:
            continue

        motivation = char_info.get("motivation", "")
        context = char_info.get("context", "")
        order = char_info.get("order", 999)

        dialogue_text = motivation or context

        if dialogue_text and len(dialogue_text) > 3:
            dialogue_text = _replace_placeholders(dialogue_text, user_name)

            # speaker 변환
            if char_id == "_env":
                speaker = "나레이션"
            elif char_id == "system":
                speaker = "시스템"
            else:
                speaker = char_id

            utterances.append({
                "speaker": speaker,
                "text": dialogue_text,
                "order": order
            })

    utterances.sort(key=lambda u: u.get("order", 999))

    for u in utterances:
        u.pop("order", None)

    if utterances:
        print(f"[CHILDREN_LLM] ✅ Generated {len(utterances)} dialogues: {[u['speaker'] for u in utterances]}")
    else:
        print(f"[CHILDREN_LLM] ⚠️ No dialogues generated")

    return utterances

def children_entry(state: Dict) -> Dict:
    runtime = state.get("runtime") or {}
    ctx = runtime.get("children_context")

    if not ctx:
        print("[CHILDREN_LLM] No context provided, skipping")
        return state

    user_name = state.get("user_name", "여행자")
    lines = generate_dialogues_from_context_llm(ctx, user_name=user_name)

    state.setdefault("agent_responses", []).extend(lines)
    runtime.pop("children_context", None)
    state["runtime"] = runtime

    print(f"[CHILDREN_LLM] Added {len(lines)} responses to state")
    return state

def run_children_agent(state: Dict) -> Dict:
    return children_entry(state)
