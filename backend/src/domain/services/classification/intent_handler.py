"""
Intent Handler - 사용자 의도를 LLM으로 정확히 판별
cutscene5_llm_driven 시나리오 전용
"""
# ============================================================
# ============================================================
from src.infrastructure.shared.dependency_container import get_llm_provider as get_llm_client

def detect_intent_with_llm(state: dict, user_input: str) -> str | None:
    """LLM 기반 의도 판별 (스테이지별)"""
    # ✅ 스테이지 키 안전하게 읽기
    scene = state.get("scene", {})
    current_stage = (state.get("current_stage") or scene.get("current_scene") or "").upper()
    scenario_id = state.get("scenario_id", "")

    if scenario_id != "cutscene5_llm_driven":
        return None

    try:
        llm_client = get_llm_client()

        if current_stage == "INTRO":
            system_prompt = """당신은 귀멸의 칼날 게임의 의도 판별 AI입니다.
사용자 입력을 다음 중 하나로 분류하세요:

1. choose_allies_path: 동료를 모으러 가거나 도움을 요청하는 의도
   예: "동료 모으자", "젠이츠/이노스케 데려오자", "도움 받자", "규합하자"
2. choose_reckless_path: 지금 당장 싸우겠다는 의도
   예: "바로 싸울게", "돌진", "지금 막을게", "함께 싸운다"

JSON으로만 응답: {"intent":"choose_allies_path"} 또는 {"intent":"choose_reckless_path"}"""
        # 기존 분기 유지
        elif current_stage == "ROUTE_CHOICE":
            system_prompt = """당신은 귀멸의 칼날 게임의 의도 판별 AI입니다.
사용자 입력을 분석하여 다음 중 하나의 의도로 분류하세요:

1. choose_allies_path: 동료를 찾으러 가거나 도움을 요청하는 의도
2. choose_reckless_path: 직접 렌고쿠와 함께 싸우겠다는 의도

JSON 형식: {"intent": "choose_allies_path" | "choose_reckless_path"}"""
        elif current_stage == "INTERVENE":
            system_prompt = """당신은 귀멸의 칼날 게임의 의도 판별 AI입니다.
사용자 입력을 분석하여 다음 중 하나로 분류하세요:
- intervene_attack
- intervene_noise
- intervene_ignore
JSON 형식: {"intent":"intervene_attack" | "intervene_noise" | "intervene_ignore"}"""
        else:
            return None

        user_prompt = f'사용자 입력: "{(user_input or "").strip()}"\n의도를 분류하세요.'

        resp = llm_client.call_json(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1)
        intent = (resp or {}).get("intent")

        # ✅ 정규화 (오타/대소문자 방지)
        norm = {
            "choose_allies_path": "choose_allies_path",
            "choose_reckless_path": "choose_reckless_path",
            "intervene_attack": "intervene_attack",
            "intervene_noise": "intervene_noise",
            "intervene_ignore": "intervene_ignore",
        }
        intent = norm.get((intent or "").strip().lower())
        print(f"[INTENT_HANDLER] LLM detected: {intent}")
        return intent
    except Exception as e:
        print(f"[INTENT_HANDLER] LLM failed: {e}")
        return None