import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
import openai

# 1) .env 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2) 룰 파일 로드
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
with open(os.path.join(CONFIG_DIR, "routing_rules.json"), "r", encoding="utf-8") as f:
    ROUTING_RULES = json.load(f)

def run_router_agent(state: Dict[str, Any], content: str) -> Dict[str, Any]:
    # 1) 기록 초기화
    state.setdefault("user_inputs", []).append(content)
    state.setdefault("agent_outputs", [])

    # 2) OpenAI 분류 프롬프트 구성
    prompt = (
        f"Game mode: {state.get('game_mode')}\n"
        f"Routing rules: {ROUTING_RULES.get(state.get('game_mode'), {})}\n"
        f"Classify the following user input as 'on_topic' or 'off_topic'.\n"
        f"User input: \"{content}\"\n"
        "Answer format JSON:\n"
        "{ \"classification\": <on_topic|off_topic>, \"keywords\": [ ... ] }\n"
    )
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":"You are a router agent."},
            {"role":"user","content":prompt}
        ],
        temperature=0
    )
    result = json.loads(response.choices[0].message.content)

    # 3) 분류 결과 적용
    classification = result["classification"]
    matched = result.get("keywords", [])
    next_node = "guardrail" if classification=="on_topic" else "guardrail"

    # 4) 기록
    state["agent_outputs"].append({
        "agent": "router_agent",
        "session_id": state["session_id"],
        "eventType": "stateSync",
        "payload": {
            "classification": classification,
            "content": content,
            "keywords": matched
        }
    })
    state["next_node"] = next_node
    return state
