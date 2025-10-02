import json
from router import run_router_agent

def test_router_agent():
    # 초기 state 정의
    state = {
        "session_id": "sess1",
        "game_mode": "story",
        "user_inputs": [],
        "agent_outputs": [],
        "game_state": {
            "scenario_id": "cutscene5_akaza",
            "scene_id": "scene5_cutscene_intro",
            "turn": 0,
            "total_remaining_turns": 8,
            "character_remaining_turns": {"inosuke": 3, "zenitsu": 3},
            "flags": [],
            "affinity": {"tanjiro": 500, "rengoku": 800}
        },
        "next_node": None
    }

    test_inputs = [
        "아카자가 나타났다! 공격하자!",
        "오늘 날씨 어때?",
        "이노스케와 젠이츠를 찾아보자.",
        "안녕 친구야!"
    ]

    for content in test_inputs:
        new_state = run_router_agent(state.copy(), content)
        # 최종 state 전체를 JSON 형태로 출력
        print(json.dumps(new_state, ensure_ascii=False, indent=2))
        print("-" * 80)

if __name__ == "__main__":
    test_router_agent()
