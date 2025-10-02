# main.py (상세 흐름 출력 버전)

import json
import os
import sys
import traceback
from typing import Dict, Any

# --- 환경 설정 및 외부 라이브러리 임포트 ---
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from openai import OpenAI

# --- 각 모듈에서 필요한 컴포넌트 임포트 ---
from final_RG_test import (
    GraphState, router_agent, guardrail_node, kasugai_crows_node,
    route_from_next_node, character_agent_node, wait_for_user_input_node
)
from parent import ParentAgent, ScenesRepo, scenes_data_flow
from children import MockChildren, OpenAIChildren, ChildrenBase

## [출력 추가] ## 딕셔너리를 예쁘게 출력하기 위한 헬퍼 함수
def pretty_print(title: str, data: Dict[str, Any]):
    """JSON 형식으로 보기 좋게 출력하는 함수"""
    print(f"\n{title}")
    print("--------------------------------------------------")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("--------------------------------------------------")

# --- 환경 설정 및 컴포넌트 인스턴스 생성 ---
load_dotenv()
USE_MOCK_CHILDREN = False # True: MockChildren 사용, False: OpenAIChildren 사용

client = None
if not USE_MOCK_CHILDREN:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: raise ValueError("OPENAI_API_KEY가 없습니다.")
    client = OpenAI(api_key=api_key)

children_agent: ChildrenBase
if USE_MOCK_CHILDREN:
    print("[시스템 설정] MockChildren을 사용합니다. (LLM 호출 없음)")
    children_agent = MockChildren()
else:
    print(f"[시스템 설정] OpenAIChildren을 사용합니다. (모델: gpt-4o)")
    children_agent = OpenAIChildren(client=client, model="gpt-4o")

scenes_repo = ScenesRepo(scenes_data_flow)
parent_agent_instance = ParentAgent(scenes=scenes_repo, llm=children_agent)

# --- 어댑터 역할을 할 parent_agent_node 구현 ---
def real_parent_agent_node(state: GraphState) -> dict:
    ## [출력 추가] ## 3단계: Parent Agent 노드 실행 시작 알림
    print("\n\n\n[STEP 3] 🟢 PARENT AGENT 노드 (어댑터) 실행 🟢")
    
    # === 단계 1: GraphState -> GameState, ContextEnvelope 변환 ===
    current_scene_id = state.get("current_node", "scene5_fork")
    game_state_input = {
        "session_id": state["session_id"], "scene": {"current_scene": current_scene_id},
        "turn": state["master_turn_count"], "total_turns_used": state["master_turn_count"],
        "affinity": state.get("affinity", {}), "flags": state.get("flags", []),
        "last_user_msg": state["user_history"][-1], "scene_history": state.get("scene_history", [])
    }
    user_msg_raw = state["user_history"][-1]
    context_envelope_input = {
        "session_id": state["session_id"], "turn": state["master_turn_count"],
        "user_msg_raw": user_msg_raw,
        "recent_messages": [{"role": "user", "content": msg} for msg in state["user_history"]],
        "router_choice_hint": {},
        "guardrail": {"allowed": True, "sanitized_user_msg": user_msg_raw}
    }
    ## [출력 추가] ## ParentAgent에 들어갈 입력 데이터를 눈으로 확인
    pretty_print("... [ParentAgent 입력]으로 변환된 GameState:", game_state_input)
    pretty_print("... [ParentAgent 입력]으로 변환된 ContextEnvelope:", context_envelope_input)

    # === 단계 2: ParentAgent.step() 실행 -> 내부적으로 ChildrenAgent 호출 ===
    print("\n>>> 이제 ParentAgent.step()을 호출합니다. (내부에서 ChildrenAgent 호출됨) <<<")
    parent_result = parent_agent_instance.step(game_state_input, context_envelope_input)
    
    ## [출력 추가] ## ParentAgent가 반환한 결과 데이터를 눈으로 확인
    pretty_print("... [ParentAgent 출력] 반환된 결과:", parent_result)

    new_game_state = parent_result["state"]
    render_output = parent_result["render"]

    # === 단계 3: 결과 -> GraphState 업데이트 ===
    new_agent_outputs = state.get("agent_outputs", [])
    if render_output.get("narration"):
        new_agent_outputs.append({"speaker": "narration", "text": render_output["narration"]})
    if render_output.get("lines"):
        new_agent_outputs.extend(render_output["lines"])

    updates = {
        "agent_outputs": new_agent_outputs,
        "master_turn_count": new_game_state.get("turn", state["master_turn_count"]),
        "affinity": new_game_state.get("affinity", state["affinity"]),
        "flags": new_game_state.get("flags", []),
        "current_node": new_game_state.get("scene", {}).get("current_scene", state["current_node"])
    }
    
    ## [출력 추가] ## 최종적으로 GraphState에 반영될 업데이트 내용을 눈으로 확인
    pretty_print("... [GraphState]에 반영될 최종 업데이트:", updates)
    print("🟢 PARENT AGENT 노드 실행 완료 🟢")
    return updates

# --- 그래프 설정 및 통합 ---
workflow = StateGraph(GraphState)
workflow.add_node("router_agent", router_agent)
workflow.add_node("guardrail_node", guardrail_node)
workflow.add_node("kasugai_crows_node", kasugai_crows_node)
workflow.add_node("character_agent", character_agent_node)
workflow.add_node("wait_for_user_input", wait_for_user_input_node)
workflow.add_node("parent_agent", real_parent_agent_node) # 실제 구현으로 교체
workflow.set_entry_point("router_agent")
workflow.add_conditional_edges("router_agent", route_from_next_node, {"guardrail_node": "guardrail_node"})
workflow.add_conditional_edges(
    "guardrail_node", route_from_next_node,
    {"kasugai_crows_node": "kasugai_crows_node", "parent_agent": "parent_agent", "character_agent": "character_agent"}
)
workflow.add_edge("kasugai_crows_node", "wait_for_user_input")
workflow.add_edge("character_agent", "wait_for_user_input")
workflow.add_edge("parent_agent", "wait_for_user_input")
workflow.add_edge("wait_for_user_input", END)
app = workflow.compile()

# --- 실행 (대화형 루프) ---
if __name__ == "__main__":
    print("\n통합 에이전트 테스트를 시작합니다. (상세 흐름 출력 모드)")
    print("(종료하려면 '종료', 'exit', 'quit' 중 하나를 입력하세요)")

    current_state = GraphState(
        session_id="test_session_123", current_node="scene5_fork", game_mode="story",
        user_history=[
                "user는 렌고쿠의 제자이다. 무한 열차가 멈추고,", 
                "렌고쿠: 나는 나의 책무를 다할 것이다! 여기 있는 그 누구도 죽게 내버려두지 않겠다!",
                "(강렬한 기운과 함께 상현 3 아카자가 나타난다)",
                "아카자: 훌륭한 투기다... 그 상처에도 불구하고 대단한 정신력이야. 오니가 되어라, 쿄쥬로.",
                "탄지로: 렌고쿠 씨! 저 녀석은 상현의 오니야!"],
        agent_outputs=[], master_turn_count=0, sub_turn_count=0, turn_limit=100,
        is_voting_active=False, affinity={}, vote_options=[], user_votes={},
        scene_image_url="", next_node="", classification="", severity="",
        flags=[], scene_history=[]
    )

    while True:
        user_message = input("\n[나의 입력] > ")
        if user_message.lower() in ["종료", "exit", "quit"]:
            print("테스트를 종료합니다."); break

        ## [출력 추가] ## 턴 시작 시점의 전체 상태 확인
        pretty_print("=========== 턴 시작: 현재 GraphState ===========", current_state)
        
        current_state["user_history"].append(user_message)
        
        try:
            ## [출력 추가] ## LangGraph 실행 시작 알림
            print("\n\n>>> LangGraph 실행 시작: app.invoke() 호출 <<<")
            final_state = app.invoke(current_state)
            
            ## [출력 추가] ## 턴 종료 시점의 전체 상태 확인
            pretty_print("=========== 턴 종료: 최종 GraphState ===========", final_state)
            
            current_state = final_state
            
            if final_state.get('agent_outputs'):
                print("\n\n============== 최종 사용자 출력 ==============")
                outputs_to_show = final_state['agent_outputs']
                for msg in outputs_to_show:
                    speaker = msg.get("speaker", "Unknown")
                    text = msg.get("text", "")
                    print(f"  [{speaker}] {text}")
                print("============================================")
                current_state["agent_outputs"] = []

        except Exception as e:
            print(f"그래프 실행 중 오류 발생: {e}")
            traceback.print_exc()