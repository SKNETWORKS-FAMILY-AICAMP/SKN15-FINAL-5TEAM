"""
Fallback LLM Module - Off-topic 응답 생성
"""

# ============================================================
# 🛟 폴백 LLM — 오프토픽 응답 생성
# ============================================================
from typing import Dict, Any, Optional


def generate_off_topic_response(state: Dict[str, Any], user_input: str) -> Optional[Dict[str, str]]:
    """
    Off-topic 발화에 대한 폴백 응답 생성

    Args:
        state: GraphState
        user_input: 사용자 입력

    Returns:
        {
            "text": "응답 텍스트",
            "speaker": "화자 이름"
        }
    """
    # 기본 폴백 응답
    fallback_responses = [
        "지금은 임무에 집중해야 해요. 이야기는 나중에 이어가요.",
        "죄송하지만, 지금은 현재 상황에 대해 이야기해주세요.",
        "흥미로운 질문이지만, 먼저 당장 급한 일을 처리하는 게 좋을 것 같아요."
    ]

    # 시나리오에서 캐릭터 정보 추출
    scenario = state.get("scenario") or state.get("scenario_data")
    character_name = "system"

    if isinstance(scenario, dict):
        metadata = scenario.get("metadata", {})
        character_name = metadata.get("name", "system")

    # 간단한 응답 선택 (입력 길이 기반)
    response_text = fallback_responses[len(user_input) % len(fallback_responses)]

    return {
        "text": response_text,
        "speaker": character_name
    }
