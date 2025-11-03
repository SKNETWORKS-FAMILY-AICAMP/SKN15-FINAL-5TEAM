#!/usr/bin/env python3
"""
간이 CLI에서 KIME Chat 백엔드 워크플로우를 직접 테스트하기 위한 스크립트.
프론트엔드 없이 사용자 입력과 에이전트 응답을 터미널에서 확인할 수 있다.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# 환경 변수(.env) 로드 — API 서버와 동일한 방식을 사용
load_dotenv(override=True)

from api_server import (  # noqa: E402
    SESSION_MANAGER,
    get_workflow,
    load_scenario,
)
try:
    from api_server import db_manager  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - DB가 구성되지 않은 경우
    db_manager = None

from src.core.graph_state import create_initial_graph_state  # noqa: E402


DEFAULT_SCENARIO_ID = "cutscene5_llm_driven"


def determine_initial_stage(scenario_data: Dict[str, Any]) -> str:
    """시나리오 메타데이터를 기반으로 초기 스테이지를 결정한다."""
    metadata = scenario_data.get("metadata", {}) if isinstance(scenario_data, dict) else {}
    initial_stage = metadata.get("default_stage")
    if initial_stage:
        return initial_stage

    stages = scenario_data.get("stages", [])
    if isinstance(stages, dict):
        return next(iter(stages.keys()), "intro")
    if isinstance(stages, list) and stages:
        return stages[0].get("tag") or stages[0].get("id") or "intro"
    return "intro"


def persist_state(session_id: str, state: Dict[str, Any], use_session_manager: bool) -> None:
    """세션 상태를 SessionManager (DB 또는 메모리)에 저장한다."""
    if not use_session_manager or SESSION_MANAGER is None:
        return

    try:
        SESSION_MANAGER.save(session_id, state)
    except Exception as exc:  # pragma: no cover - 로컬 테스트 보호
        print(f"⚠️  세션 저장 실패: {exc}", file=sys.stderr)


def initialize_state(
    session_id: str,
    scenario_id: str,
    user_name: str,
    user_id: Optional[str],
    use_session_manager: bool,
) -> Tuple[Dict[str, Any], bool]:
    """
    API 서버와 최대한 동일한 로직으로 상태를 구성한다.

    Returns:
        (state, loaded_from_store)
    """
    loaded_from_store = False
    state: Dict[str, Any] = {}

    if use_session_manager and SESSION_MANAGER is not None:
        try:
            state = SESSION_MANAGER.load_or_create(session_id) or {}
        except Exception as exc:
            print(f"⚠️  세션 저장소에서 상태를 불러오지 못했습니다: {exc}", file=sys.stderr)
            state = {}

        if state and "messages" in state:
            loaded_from_store = True
            if user_name:
                state["user_name"] = user_name
            if user_id:
                state["user_id"] = user_id

            state.setdefault("user_inputs", [])
            state.setdefault("stage_dialogue_counts", {})
            state.setdefault("dialogues_generated_count", 0)
            state.setdefault("event_flags", [])
            state.setdefault("image_transition_history", [])
            return state, loaded_from_store

    scenario_data = load_scenario(scenario_id)
    if not scenario_data:
        raise RuntimeError(f"Scenario '{scenario_id}' not found.")

    resolved_id = scenario_data.get("scenario_id") or scenario_id
    state = create_initial_graph_state(session_id=session_id, scenario_id=resolved_id)
    state["session_id"] = session_id
    state["scenario_id"] = resolved_id
    state["scenario_data"] = scenario_data
    state["scenario"] = scenario_data
    state["user_name"] = user_name
    state["current_stage"] = determine_initial_stage(scenario_data)
    if user_id:
        state["user_id"] = user_id

    # 인증 사용자라면 장기 기억을 불러온다.
    if user_id and db_manager is not None:
        try:
            memory_context = db_manager.get_user_memory_context(user_id)
            if memory_context:
                state["user_memory_context"] = memory_context
                print("🧠  사용자 장기 기억을 로드했습니다.")
        except Exception as exc:  # pragma: no cover - DB 연결 실패 대비
            print(f"⚠️  사용자 기억 로드 실패: {exc}", file=sys.stderr)

    persist_state(session_id, state, use_session_manager)
    return state, loaded_from_store


def ensure_preinvoke_state(state: Dict[str, Any], user_input: str) -> None:
    """워크플로 호출 전 필요한 공용 필드를 맞춰 준다."""
    state["user_input"] = user_input
    state["user_inputs"] = state.get("user_inputs", []) + [user_input]

    if not user_input.startswith("__AUTO_CONTINUE__"):
        state["dialogue_batch_index"] = 0
        state["output"] = {}
        state["agent_responses"] = []

    state.setdefault("stage_dialogue_counts", {})
    state.setdefault("dialogues_generated_count", 0)
    state.setdefault("event_flags", [])
    state.setdefault("image_transition_history", [])


def extract_dialogues(result_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """에이전트가 생성한 대화 리스트를 가져온다."""
    output = result_state.get("output")
    if isinstance(output, dict):
        dialogues = output.get("dialogues")
        if isinstance(dialogues, list):
            return dialogues
    return []


def format_dialogue(entry: Any) -> str:
    """단일 대화 항목을 출력용 문자열로 변환."""
    if isinstance(entry, dict):
        speaker = entry.get("speaker") or entry.get("character") or "unknown"
        text = entry.get("content") or entry.get("text") or ""
        return f"{speaker}> {text}"
    return f"unknown> {entry}"


def run_cli(
    session_id: str,
    scenario_id: str,
    user_name: str,
    user_id: Optional[str],
    use_session_manager: bool,
) -> None:
    """인터랙티브 CLI 루프를 실행한다."""
    try:
        state, loaded_from_store = initialize_state(
            session_id,
            scenario_id,
            user_name,
            user_id,
            use_session_manager,
        )
    except RuntimeError as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        sys.exit(1)

    workflow = get_workflow()

    print("==============================================")
    print(" KIME Chat CLI (backend only)")
    print("==============================================")
    print(f"- 세션 ID : {session_id}")
    print(f"- 시나리오: {state.get('scenario_id')}")
    print(f"- 초기 스테이지: {state.get('current_stage')}")
    print("----------------------------------------------")
    if use_session_manager and SESSION_MANAGER is not None:
        status_label = "불러오기" if loaded_from_store else "신규 생성"
        store_kind = SESSION_MANAGER.__class__.__name__
        print(f"[세션 저장소] {store_kind} ({status_label})")
    else:
        print("[세션 저장소] 사용 안 함")
    print("----------------------------------------------")
    print("명령 안내:")
    print("  입력 → 에이전트 응답 보기")
    print("  :auto → '__AUTO_CONTINUE__' 입력")
    print("  :quit or Ctrl+C → 종료")
    print("----------------------------------------------")

    while True:
        try:
            raw_input_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not raw_input_text:
            continue

        if raw_input_text in {":quit", ":exit"}:
            print("종료합니다.")
            break

        if raw_input_text == ":auto":
            user_input = "__AUTO_CONTINUE__"
        else:
            user_input = raw_input_text

        previous_turn_count = int(state.get("turn_count", 0) or 0)
        state["session_id"] = session_id  # 세션 ID를 명시적으로 유지

        ensure_preinvoke_state(state, user_input)

        try:
            result_state = workflow.invoke(state)
        except Exception as exc:  # pragma: no cover - 디버깅용 보호
            print(f"[워크플로 오류] {exc}", file=sys.stderr)
            continue

        current_turn_count_raw = result_state.get("turn_count")
        try:
            current_turn_count = int(current_turn_count_raw)
        except (TypeError, ValueError):
            current_turn_count = previous_turn_count

        if current_turn_count <= previous_turn_count:
            current_turn_count = previous_turn_count + 1

        result_state["turn_count"] = current_turn_count

        state = result_state

        persist_state(session_id, state, use_session_manager)

        print("----------------------------------------------")
        stage = state.get("current_stage") or "UNKNOWN"
        stage_turn = state.get("stage_turn")
        stage_turn_str = f"{stage_turn}" if stage_turn is not None else "?"
        print(f"[턴 {current_turn_count}] Stage={stage} (stage_turn={stage_turn_str})")

        dialogues = extract_dialogues(state)
        if dialogues:
            for entry in dialogues:
                print(format_dialogue(entry))
        else:
            print("(대화가 생성되지 않았습니다)")

        system_msg = state.get("system_message")
        if system_msg:
            print(f"[시스템] {system_msg}")

        if state.get("has_more"):
            print("⚠️ has_more 플래그가 설정되었습니다.")

        if state.get("is_ended"):
            print("✅ 시나리오가 종료되었습니다.")
            break

    print("CLI 세션을 종료합니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KIME Chat 백엔드 전용 CLI")
    parser.add_argument(
        "--scenario",
        default=DEFAULT_SCENARIO_ID,
        help=f"사용할 시나리오 ID (기본: {DEFAULT_SCENARIO_ID})",
    )
    parser.add_argument(
        "--session",
        help="지정할 세션 ID (미지정 시 자동 생성)",
    )
    parser.add_argument(
        "--user-name",
        default="츠구코",
        help="유저 이름 (기본: 츠구코)",
    )
    parser.add_argument(
        "--user-id",
        help="데이터베이스에 저장된 사용자 ID (선택)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="세션을 SessionManager에 저장하지 않음",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session_id = args.session or str(uuid.uuid4())
    use_session_manager = not args.no_persist

    if use_session_manager and SESSION_MANAGER is None:
        print("⚠️  SessionManager가 활성화되어 있지 않습니다. 메모리 상태만 사용합니다.", file=sys.stderr)
        use_session_manager = False

    if args.user_id and db_manager is None:
        print("⚠️  데이터베이스 연결이 없어 사용자 기억을 로드할 수 없습니다.", file=sys.stderr)

    run_cli(
        session_id=session_id,
        scenario_id=args.scenario,
        user_name=args.user_name,
        user_id=args.user_id,
        use_session_manager=use_session_manager,
    )


if __name__ == "__main__":
    main()
