# interactive_router_test.py

import json
from router import run_router_agent

def interactive_router():
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

    print("Interactive Router Test")
    print("Type your message (or 'exit' to quit):")
    while True:
        content = input(">>> ").strip()
        if content.lower() in ("exit", "quit"):
            break

        # 라우터 실행
        new_state = run_router_agent(state.copy(), content)
        payload = new_state["agent_outputs"][-1]["payload"]

        # 결과 출력
        print(json.dumps({
            "input": content,
            "classification": payload["classification"],
            "keywords": payload["keywords"],
            "next_node": new_state["next_node"]
        }, ensure_ascii=False, indent=2))
        print("-" * 60)

if __name__ == "__main__":
    interactive_router()
