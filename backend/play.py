#!/usr/bin/env python3
"""
KIME Chat Agent - 인터랙티브 플레이
OpenAI 지원, 안정적인 게임 루프와 예외 처리 포함
개선: 시나리오 분기 상태 표시 및 시인성 향상
"""

import uuid
import os
import json
import pathlib
from dotenv import load_dotenv, find_dotenv
from langchain_core.messages import HumanMessage
from src.core.workflow import create_workflow
from src.core.graph_state import GraphState
from src.utils.scenario_loader import scenario_loader
from typing import Tuple
from src.utils.affinity import _ensure_affinity_state  # reuse syncing helper

# Minimal characters repo helpers (data-driven) — avoids hardcoding
from glob import glob

CHAR_DIR = os.path.join(os.path.dirname(__file__), "data", "characters")

# 후에 웹 붙이면 교체
def _read_or_make_persistent_uuid(path: str) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                s = f.read().strip()
                if s:
                    return s
        uid = str(uuid.uuid4())
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(uid)
        return uid
    except Exception:
        return str(uuid.uuid4())


def _list_characters() -> list[str]:
    try:
        base = os.path.join(os.path.dirname(__file__), "data", "characters", "*.json")
        files = glob(base)
        ids = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cid = (data.get("id") or pathlib.Path(fp).stem).strip().lower()
                if cid:
                    ids.append(cid)
            except Exception:
                continue
        return ids
    except Exception:
        return []


def _default_affinity_of(char_id: str) -> int:
    try:
        fp = os.path.join(os.path.dirname(__file__), "data", "characters", f"{char_id}.json")
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("default_affinity") or (data.get("profile") or {}).get("default_affinity") or 0)
    except Exception:
        pass
    return 0

REQUIRED_SCENARIO_KEYS = ["scenario_id", "title", "stages"]

def validate_scenario_schema(data: dict) -> Tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "JSON 루트가 dict가 아닙니다."
    missing = [k for k in REQUIRED_SCENARIO_KEYS if k not in data]
    if missing:
        return False, f"필수 필드 누락: {', '.join(missing)}"
    stages = data.get("stages")
    if not stages or (not isinstance(stages, (list, dict))):
        return False, "stages가 비어있거나 잘못된 형식입니다"
    return True, ""

def safe_load_scenario(scenario_id: str):
    """
    시나리오를 안전하게 로드하고 스키마를 검증합니다.
    1) scenario_loader.load_scenario(scenario_id)
    2) scenario_loader.load_scenario(f\"{scenario_id}.json\")
    3) 직접 파일 열기
    순으로 시도합니다.
    """
    candidates = [scenario_id, f"{scenario_id}.json"]
    for cand in candidates:
        try:
            data = scenario_loader.load_scenario(cand)
            if data:
                ok, reason = validate_scenario_schema(data)
                if not ok:
                    print(f"❌ 시나리오 검증 실패({cand}): {reason}")
                    return None
                return data
        except Exception as e:
            # 조용히 다음 후보 시도
            pass

    # 마지막으로 로컬 파일 경로 직접 시도
    for cand in candidates:
        if os.path.exists(cand):
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ok, reason = validate_scenario_schema(data)
                if not ok:
                    print(f"❌ 시나리오 검증 실패({cand}): {reason}")
                    return None
                return data
            except Exception as e:
                print(f"❌ 로컬 파일 로드 실패({cand}): {e}")

    print(f"❌ 시나리오 로드 실패: '{scenario_id}' (id 또는 '{scenario_id}.json' 파일을 찾을 수 없음)")
    return None


def print_scenario_status(state: GraphState):
    """
    현재 시나리오 상태를 JSON 형식으로 표시
    """
    display_stage = (
        (state.get("temp_data") or {}).get("display_stage")
        if isinstance(state.get("temp_data"), dict)
        else None
    )
    current_stage = display_stage or state.get("current_stage", "unknown")
    scenario_id = state.get("scenario_id", "unknown")
    turn_count = state.get("turn_count", 0)
    affinity_scores = state.get("affinity_scores", {})
    # Hide characters marked not visible (e.g., akaza)
    hidden = set()
    try:
        # try dynamic flags from characters_repo if available
        from src.utils.characters_repo import affinity_visible
        hidden = {cid for cid, _ in affinity_scores.items() if not affinity_visible(cid)}
    except Exception:
        pass
    stage_history = state.get("stage_history", [])

    # 시나리오 상태 정보
    status_info = {
        "scenario": scenario_id,
        "current_stage": current_stage,
        "turn": turn_count,
        "stage_path": " → ".join(stage_history[-5:]) if stage_history else current_stage,
        "affinity": affinity_scores
    }

    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║                    📊 시나리오 상태                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"  🎬 시나리오: {status_info['scenario']}")
    print(f"  📍 현재 스테이지: {status_info['current_stage']}")
    print(f"  🔀 진행 경로: {status_info['stage_path']}")
    print(f"  🔢 턴 수: {status_info['turn']}")
    if affinity_scores:
        print(f"  💖 친밀도:")
        for char, score in affinity_scores.items():
            if char in hidden:
                continue
            bar = "█" * (score // 100) + "░" * (10 - score // 100)
            print(f"     - {char}: {bar} {score}/1000")
    print("─" * 62)


def print_separator(turn_num: int):
    """
    턴 구분선 출력
    """
    print("\n" + "═" * 62)
    print(f"                         턴 {turn_num}")
    print("═" * 62 + "\n")


def load_config(config_path: str = "config.json") -> dict:
    """
    cutscene5_llm_driven 설정 파일 로드
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  설정 파일 '{config_path}'을 찾을 수 없습니다. 기본 설정을 사용합니다.")
        return {
            "game": {"default_scenario": "cutscene5_llm_driven"},
            "scenarios": [],
            # show_scenario_status : 현재 씬/턴/남은시간/친밀도 출력할건지? 
            # 문제1 여기 실제 연결 안되어있음
            "display": {"show_scenario_status": True, "show_turn_separator": True}
        }

def select_scenario(config: dict) -> str:
    """
    사용자가 시나리오를 선택하도록 함
    """
    scenarios = config.get("scenarios", [])

    if not scenarios:
        print("⚠️  사용 가능한 시나리오가 없습니다. 기본 시나리오를 사용합니다.")
        return config["game"]["default_scenario"]

    print("\n" + "=" * 62)
    print("              🎮 시나리오 선택")
    print("=" * 62)
    
    # 인덱스를 1부터 시작 enumerate(iterable, start)
    for idx, scenario in enumerate(scenarios, 1):
        print(f"\n{idx}. {scenario['name']}")
        print(f"   📝 {scenario['description']}")
        print(f"   🎯 난이도: {scenario['difficulty']}")

    print("\n" + "=" * 62)

    while True:
        choice = input(f"\n시나리오를 선택하세요 (1-{len(scenarios)}) [Enter: 기본]: ").strip()

        if not choice:
            default_id = config["game"]["default_scenario"]
            print(f"✅ 기본 시나리오 '{default_id}'를 선택했습니다.")
            return default_id

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(scenarios):
                selected = scenarios[idx]["id"]
                print(f"✅ '{scenarios[idx]['name']}'를 선택했습니다.")
                # ex) cutscene5_llm_driven return
                return selected
            else:
                print(f"❌ 1부터 {len(scenarios)} 사이의 숫자를 입력하세요.")
        except ValueError:
            print("❌ 숫자를 입력하세요.")

def main():
    """
    KIME-CHAT-AGENT의 메인 실행 함수.
    OpenAI 환경을 지원하며, 안정적인 게임 루프와 예외 처리를 포함합니다.
    """
    # .env 파일에서 환경 변수 로드 (OPENAI_API_KEY)
    # 현재 스크립트의 디렉토리에서 .env 파일 찾기
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # dotenv_path = os.path.join(script_dir, '.env')
    load_dotenv(find_dotenv(), override=True)
    print(os.getenv("OPENAI_API_KEY"))

    # API Key 확인 (보안상 출력하지 않음)
    if not os.getenv("OPENAI_API_KEY"):
        print("🚨 오류: OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print(".env 파일에 'OPENAI_API_KEY=your_key' 형식으로 키를 추가해주세요.")
        return

    # 1. 설정 파일 로드
    config = load_config()

    # 2. 시나리오 선택 : 1~5
    scenario_id = select_scenario(config)

    # 3. 시나리오 데이터 로드 (안전 로더 사용), return bool 
    scenario_data = safe_load_scenario(scenario_id)
    if not scenario_data:
        print("🚫 프로그램을 종료합니다. 시나리오 파일을 확인해주세요.")
        return

    # 검증 통과했으므로 안전하게 접근 가능
    print(f"\n✅  시나리오 로드 완료: {scenario_data.get('title', scenario_id)}")
    # 2. 워크플로우 컴파일
    app = create_workflow()
    session_id = str(uuid.uuid4())
    print("==============================================")
    print(" KIME 대화형 에이전트에 오신 것을 환영합니다! (OpenAI ver.)")
    print(f" 새로운 세션이 시작되었습니다: {session_id[:8]}...")
    print("==============================================")
    print("게임을 종료하려면 'exit' 또는 'quit'을 입력하세요.\n")

    # 🔥 사용자 이름 입력
    user_name = input("👤 당신의 이름을 입력하세요: ").strip()
    if not user_name:
        user_name = "여행자"  # 기본 이름
    print(f"✅ '{user_name}'님, 환영합니다!\n")

    # 3. 초기 상태 정의 (Fresh 정책)
    initial_state: GraphState = {
        "messages": [],
        "next_node": "router",
        "session_id": session_id,
        "current_node_name": "INITIAL",
        "current_scene_id": "intro",
        "turn_count": 0,
        "is_timeout": False,
        "user_input": "시작",
        "user_inputs": [],
        "available_choices": [],
        "agent_responses": [],
        "active_character": "system",
        "user_name": user_name,  # 사용자 이름 저장
        # Fresh: 시작 시 캐릭터 기본 친밀도로 초기화
        "affinity_scores": {},
        "is_persuasion_successful": None,
        "mission_result": None,
        "system_flags": [],
        "final_ending": None,
        "scenario_id": scenario_data.get("scenario_id", scenario_id),
        "scenario_data": scenario_data,  # 🔥 로드된 시나리오 데이터
        "current_stage": "INTRO",  # 🔥 시작 스테이지 설정 (cutscene5_llm_driven.json 기준)
        "stage_history": [],
        "stage_turn": 0,  # 🔥 스테이지 내 턴 카운트 초기화
        "stage_states": {},
        "meta": {
            "session_id": session_id,
            "timestamp": "",
            # "version": "4.0",  # Blueprint 4
            "processed_by": None
        },
        "message_history": [],
        "routing_result": None,
        "output": {
            "dialogues": [],
            "images": [],
            "system_messages": []
        },
        "temp_data": {},
        "error_message": None,
        "tool_outputs": None,
        "runtime": {},  # 🔥 Agent 간 컨텍스트 전달용
    }

    # Fresh 정책: user_id/campaign_id, 기본 친밀도, runs_history
    # 웹 연결 시, 여러 시나리오 세션 생성, 세션마다 친밀도 정보 다르게 적용, 유지하기 위함
    user_id = os.getenv("JWT_SUB")
    if not user_id:
        # persist under local .persist directory
        persist_file = os.path.join(os.path.dirname(__file__), ".persist", "user_uuid.txt")
        user_id = _read_or_make_persistent_uuid(persist_file)

    campaign_id = scenario_data.get("scenario_id") or scenario_id

    # 기본 친밀도 로드 (데이터 주도)
    chars = _list_characters()
    # Exclude characters with affinity_applicable == False from initialization
    try:
        from src.utils.characters_repo import affinity_applicable
        defaults = {cid: _default_affinity_of(cid) for cid in chars if affinity_applicable(cid)}
    except Exception:
        defaults = {cid: _default_affinity_of(cid) for cid in chars}
    # 동기화된 dict 객체로 유지
    initial_state["affinity"] = defaults
    initial_state["affinity_scores"] = initial_state["affinity"]
    _ensure_affinity_state(initial_state)

    # 영속 컨테이너(간단): 이번 런의 기록만 유지
    initial_state.setdefault("runs_history", [])
    initial_state.setdefault("profile", {
        "user_id": user_id,
        "campaign_id": campaign_id,
        "policy": "fresh",
        "last_save": None,
    })

    # 3. 첫 대사는 사용자 입력 후 출력 (자동 실행 제거)
    print("\n" + "=" * 62)
    print("                    🎬 이야기가 시작됩니다...")
    print("=" * 62 + "\n")
    print("첫 입력을 기다립니다...")

    # 4. 안정적인 메인 게임 루프
    turn_num = 0
    while True:
        try:
            # 턴 구분선 출력
            turn_num += 1
            print_separator(turn_num)

            # 4. 워크플로우 실행 및 결과 스트리밍
            events = app.stream(initial_state, {"recursion_limit": 100})
            final_state = None

            print("\n--- [시스템 처리중...] ---")
            for event in events:
                if "messages" in event:
                    # 'messages' 이벤트는 LangChain 내부 이벤트이므로, 사용자에게 직접 표시하지 않음
                    pass
                else:
                    # 다른 모든 노드의 출력을 명확하게 표시 (디버깅에 유용)
                    node_name = list(event.keys())[0]
                    node_output = event[node_name]
                    # print(f"Node '{node_name}':") # 상세 디버깅 시 주석 해제
                    # print(f"  - Output: {node_output}")

                # 마지막 이벤트의 상태를 저장
                if event:
                    final_state = event.get(list(event.keys())[-1])

            # 5. 최종 결과 출력 및 상태 업데이트
            if final_state:
                # 🔥 agent_responses가 있으면 출력
                if final_state.get("agent_responses"):
                    # 🔥 방안 B: 모든 응답 출력 (다중 대화)
                    print("\n" + "=" * 60)

                    # turn/scene 진행이 사용자 입력 타이밍과 정확히 맞도록 보정
                    # (workflow 실행에 사용된 initial_state의 turn_count를 그대로 반영)
                    final_state["turn_count"] = initial_state.get(
                        "turn_count",
                        final_state.get("turn_count", 0)
                    )

                    for i, response in enumerate(final_state["agent_responses"]):
                        speaker = response.get("speaker", "나레이션")
                        text = response.get("text", "")

                        # 캐릭터별 대사 출력
                        print(f"\n[{speaker}]: {text}")

                    print("\n" + "=" * 60)

                    # 시나리오 상태 출력 (대사 출력 후)
                    print_scenario_status(final_state)

                    # 🔥 게임 종료 확인 (final_ending이 설정되었거나 next_node가 END인 경우)
                    if final_state.get("final_ending") or final_state.get("next_node") == "END":
                        print("\n🎬 게임이 종료되었습니다.")
                        print("이용해주셔서 감사합니다!\n")
                        break

                    # 유저 입력 프롬프트 표시
                    current_stage = final_state.get("current_stage", "")
                    if current_stage and current_stage.upper() in ["ROUTE_CHOICE", "INTERVENE", "RECRUIT"]:
                        user_prompt = "선택하세요"
                    else:
                        user_prompt = "입력하세요"
                    print(f"\n💡 {user_prompt}")

                # 🔥 상태 업데이트
                initial_state = final_state
                initial_state["agent_responses"] = []

                # Fresh 정책: 런 종료 시 최종 친밀도 기록 (세션 중 덮어쓰지 않음)
                if final_state.get("final_ending") or final_state.get("next_node") == "END":
                    try:
                        rec = {
                            "user_id": initial_state.get("profile", {}).get("user_id"),
                            "campaign_id": initial_state.get("profile", {}).get("campaign_id"),
                            "affinity": dict(initial_state.get("affinity_scores", {})),
                        }
                        initial_state.setdefault("runs_history", []).append(rec)
                    except Exception:
                        pass

            # 6. 사용자 입력 처리
            user_input = input("\n[당신]: ").strip()

            if user_input.lower() in ["exit", "quit", "종료", "나가기"]:
                print("게임을 종료합니다. 이용해주셔서 감사합니다.")
                break

            if not user_input:
                print("입력이 비어있습니다. 다시 입력해주세요.")
                continue

            # 다음 턴을 위해 사용자 입력을 상태에 추가
            initial_state["user_input"] = user_input
            initial_state["messages"] = [HumanMessage(content=user_input)]

            # 🔥 턴 카운트 증가 (workflow 실행 전에!)
            initial_state["turn_count"] = initial_state.get("turn_count", 0) + 1
            initial_state["stage_turn"] = initial_state.get("stage_turn", 0) + 1


        except KeyboardInterrupt:
            print("\n\n게임을 강제 종료합니다.")
            break

        except Exception as e:
            print(f"\n🚨 치명적인 오류가 발생했습니다: {e}")

            # 에러 상세 정보 (디버그용)
            import traceback
            traceback.print_exc()

            print("\n오류가 발생하여 게임을 종료합니다.")
            break

if __name__ == "__main__":
    main()
