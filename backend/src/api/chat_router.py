"""
============================================================
💬 Chat Router — 메인 채팅 엔드포인트
============================================================
LangGraph 워크플로우를 실행하고 실시간 스트리밍으로 대화를 반환합니다.
"""
from __future__ import annotations

import json
import time
import uuid
import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.workflow import create_workflow
from src.core.graph_state import create_initial_graph_state
from src.auth.dependencies import require_auth

# ============================================================
# Router 및 전역 변수
# ============================================================
router = APIRouter(prefix="/api", tags=["chat"])

# 의존성 주입용 전역 변수
_session_manager = None
_db_manager = None
_workflow = None
_load_scenario_func = None


def set_dependencies(session_manager, db_manager, load_scenario_func):
    """
    의존성 주입 함수

    Args:
        session_manager: HybridSessionManager 인스턴스
        db_manager: DatabaseManager 인스턴스
        load_scenario_func: 시나리오 로드 함수
    """
    global _session_manager, _db_manager, _load_scenario_func
    _session_manager = session_manager
    _db_manager = db_manager
    _load_scenario_func = load_scenario_func


def get_workflow():
    """LangGraph 워크플로우 가져오기 (싱글톤)"""
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow


# ============================================================
# Pydantic Models
# ============================================================
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    scenario_id: Optional[str] = None
    user_input: str
    user_name: Optional[str] = "여행자"


class DialogueResponse(BaseModel):
    speaker: str
    text: str
    emotion: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    dialogues: list[DialogueResponse]
    current_stage: Optional[str] = None
    affinity_scores: Dict[str, int] = {}


# ============================================================
# 메인 Chat 엔드포인트
# ============================================================
@router.post("/chat")
async def chat(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth)
):
    """
    메인 채팅 엔드포인트 (🔐 로그인 필수)
    1. JWT 토큰 검증 (로그인하지 않으면 401 에러)
    2. 세션 생성 or 복원
    3. 시나리오 로드
    4. LangGraph 실행
    5. 실시간 스트리밍으로 결과 반환

    Args:
        request: HTTP 요청 객체
        current_user: 인증된 사용자 정보 (필수, JWT 토큰에서 추출)

    Returns:
        StreamingResponse: Server-Sent Events 스트림

    Raises:
        HTTPException 401: 인증되지 않은 사용자
    """
    try:
        request_start = time.perf_counter()
        data = await request.json()

        session_id = data.get("session_id")
        user_input = data.get("user_input", "")
        scenario_id = data.get("scenario_id")
        user_name = data.get("user_name") or "여행자"

        # 🔐 인증된 사용자 정보 추출 (필수)
        user_id = current_user.get('user_id')
        username = current_user.get('username', 'Unknown')
        print(f"🔐 Authenticated user: {username} (ID: {user_id})")

        # 📝 General Log: 인증 사용자
        try:
            _session_manager.save_log(
                log_level="info",
                log_message=f"Authenticated user: {username}",
                session_id=None,
                metadata={"user_id": user_id, "username": username}
            )
        except Exception as e:
            print(f"⚠️ Failed to save user auth log: {e}")

        print(f"📥 Request received: session_id={session_id}, input='{user_input}'")

        # 세션 생성 또는 복원
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"🆕 Creating new session: {session_id}")
            try:
                _session_manager.save_log(
                    log_level="info",
                    log_message="New session created",
                    session_id=session_id,
                    metadata={"user_id": user_id, "scenario_id": scenario_id}
                )
            except Exception as e:
                print(f"⚠️ Failed to save session creation log: {e}")
        else:
            print(f"🔁 Reusing session: {session_id}")
            try:
                _session_manager.save_log(
                    log_level="info",
                    log_message="Session reused",
                    session_id=session_id,
                    metadata={"user_id": user_id}
                )
            except Exception as e:
                print(f"⚠️ Failed to save session reuse log: {e}")

        state = _session_manager.load_or_create(session_id)
        is_new_session = "messages" not in state

        # 새 세션 초기화
        if is_new_session:
            if not scenario_id:
                raise HTTPException(
                    status_code=400, detail="scenario_id is required to start a session"
                )

            scenario_data = _load_scenario_func(scenario_id)
            if not scenario_data:
                raise HTTPException(
                    status_code=404, detail=f"Scenario '{scenario_id}' not found"
                )

            resolved_id = scenario_data.get("scenario_id") or scenario_id
            state = create_initial_graph_state(
                session_id=session_id, scenario_id=resolved_id
            )
            state["scenario_data"] = scenario_data
            state["scenario"] = scenario_data
            state["scenario_id"] = resolved_id
            state["user_name"] = user_name
            state["user_id"] = user_id
            state["db_manager"] = _db_manager  # 이미지 매핑용 DB 접근

            # 🧠 사용자 장기 기억 로드
            if user_id:
                try:
                    memory_context = _db_manager.get_user_memory_context(user_id)
                    if memory_context:
                        state["user_memory_context"] = memory_context

                        rel_count = len(memory_context.get("relationships", []) or [])
                        pref_count = len(memory_context.get("preferences", []) or [])
                        story_count = len(memory_context.get("story_progress", []) or [])
                        fact_count = len(memory_context.get("facts", []) or [])

                        print(f"🧠 User memories loaded for {username}:")
                        print(f"   - Relationships: {rel_count}")
                        print(f"   - Preferences: {pref_count}")
                        print(f"   - Story progress: {story_count}")
                        print(f"   - Facts: {fact_count}")

                        try:
                            _session_manager.save_log(
                                log_level="info",
                                log_message=f"User memories loaded: {rel_count + pref_count + story_count + fact_count} total",
                                session_id=session_id,
                                metadata={
                                    "user_id": user_id,
                                    "username": username,
                                    "relationships": rel_count,
                                    "preferences": pref_count,
                                    "story_progress": story_count,
                                    "facts": fact_count
                                }
                            )
                        except Exception as log_err:
                            print(f"⚠️ Failed to save memory load log: {log_err}")
                    else:
                        print(f"🧠 No memories found for user {user_id}")
                except Exception as e:
                    print(f"⚠️ Failed to load user memories: {e}")

            # Initial stage 설정
            metadata = scenario_data.get("metadata", {}) if isinstance(scenario_data, dict) else {}
            initial_stage = metadata.get("default_stage")
            if not initial_stage:
                stages = scenario_data.get("stages", [])
                if isinstance(stages, dict):
                    initial_stage = next(iter(stages.keys()), "intro")
                elif isinstance(stages, list) and stages:
                    initial_stage = stages[0].get("tag") or stages[0].get("id") or "intro"
                else:
                    initial_stage = "intro"
            state["current_stage"] = initial_stage
        else:
            print(f"🔄 Loading existing session: {session_id}")
            print(
                f"📊 Session state: stage={state.get('current_stage')}, stage_turn={state.get('stage_turn')}"
            )
            if user_name:
                state["user_name"] = user_name

        # 시나리오 데이터 확인
        if not state.get("scenario_data") and scenario_id:
            scenario_data = _load_scenario_func(scenario_id)
            if scenario_data:
                state["scenario_data"] = scenario_data
                state["scenario"] = scenario_data
                state.setdefault(
                    "scenario_id", scenario_data.get("scenario_id") or scenario_id
                )

        state["session_id"] = session_id
        state["user_input"] = user_input
        state["user_inputs"] = state.get("user_inputs", []) + [user_input]

        # 배치 모드 관리
        if not user_input.startswith("__AUTO_CONTINUE__"):
            state["dialogue_batch_index"] = 0

        # 필드 초기화
        state.setdefault("stage_dialogue_counts", {})
        state.setdefault("dialogues_generated_count", 0)
        state.setdefault("event_flags", [])
        state.setdefault("image_transition_history", [])

        print(f"🤖 Processing: session={session_id}, input='{user_input}'")

        # 백그라운드 처리를 위한 상태 저장
        state["_old_affinity"] = state.get("affinity_scores", {}).copy()
        state["_old_stage"] = state.get("current_stage")

        workflow_instance = get_workflow()
        workflow_start = time.perf_counter()

        # 실시간 스트리밍 응답 생성
        async def generate_stream():
            """
            LangGraph의 astream()을 사용하여 실시간 스트리밍
            """
            nonlocal state
            sent_dialogue_count = 0
            final_state = None

            try:
                # 1. 초기 메타데이터 전송
                init_meta = {
                    "type": "metadata",
                    "session_id": session_id,
                    "current_stage": state.get("current_stage"),
                }
                yield f"data: {json.dumps(init_meta, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)

                # 2. 실시간 스트리밍: workflow의 각 노드 실행
                async for event in workflow_instance.astream(state):
                    for node_name, node_state in event.items():
                        print(f"🌊 Stream event from node: {node_name}")

                        # Debug: Print keys in node_state
                        state_keys = list(node_state.keys()) if isinstance(node_state, dict) else []
                        print(f"🔑 Keys in node_state: {state_keys[:10]}...")

                        # Debug: Check agent_responses specifically
                        agent_resp = node_state.get("agent_responses") if isinstance(node_state, dict) else None
                        print(f"🐛 agent_responses type: {type(agent_resp)}, value: {agent_resp[:1] if isinstance(agent_resp, list) and agent_resp else agent_resp}")

                        final_state = node_state

                        # 새로운 대화 확인
                        current_responses = []

                        # agent_responses 우선
                        if isinstance(node_state.get("agent_responses"), list):
                            current_responses = node_state["agent_responses"]
                            print(f"🎯 Found {len(current_responses)} dialogues in agent_responses from {node_name}")

                        # output.dialogues 백업
                        elif isinstance(node_state.get("output"), dict):
                            dialogues = node_state["output"].get("dialogues", [])
                            if isinstance(dialogues, list):
                                current_responses = dialogues
                                print(f"🎯 Found {len(current_responses)} dialogues in output.dialogues from {node_name}")

                        # 새로 추가된 대화만 전송
                        if len(current_responses) > sent_dialogue_count:
                            new_dialogues = current_responses[sent_dialogue_count:]

                            for dialogue in new_dialogues:
                                dialogue_data = {
                                    "type": "dialogue",
                                    "index": sent_dialogue_count,
                                    "dialogue": dialogue
                                }
                                yield f"data: {json.dumps(dialogue_data, ensure_ascii=False)}\n\n"
                                sent_dialogue_count += 1
                                print(f"✅ Sent dialogue #{sent_dialogue_count}: {dialogue.get('text', '')[:50]}...")

                                await asyncio.sleep(0.1)

                        await asyncio.sleep(0.01)

                # 3. Workflow 완료 - 최종 상태 저장
                if final_state:
                    # turn_count 증가
                    turn_count = final_state.get("turn_count", 0) + 1
                    final_state["turn_count"] = turn_count

                    # user_id 보존
                    if "user_id" not in final_state or final_state.get("user_id") is None:
                        if user_id:
                            final_state["user_id"] = user_id

                    # 백그라운드 처리용 old 상태 복사
                    final_state["_old_affinity"] = state.get("_old_affinity", {})
                    final_state["_old_stage"] = state.get("_old_stage")

                    # 세션 저장
                    _session_manager.save(session_id, final_state)
                    print(f"💾 Session saved: {session_id}")

                    # 💜 친밀도 변화 DB 저장
                    old_affinity = final_state.get("_old_affinity", {})
                    new_affinity = final_state.get("affinity_scores", {})
                    turn_count = final_state.get("turn_count", 0)
                    current_user_id = final_state.get("user_id") or user_id

                    for character, new_score in new_affinity.items():
                        old_score = old_affinity.get(character, 0)
                        change = new_score - old_score

                        if change != 0:
                            try:
                                # 세션별 친밀도 기록 저장
                                _session_manager.save_affinity(
                                    session_id=session_id,
                                    turn_number=turn_count,
                                    character_name=character,
                                    affinity_score=new_score,
                                    change_amount=change
                                )
                                print(f"💜 Affinity saved: {character} {old_score} → {new_score} (change: {change:+d})")

                                # 글로벌 캐릭터 친밀도 업데이트 (최대 1000점)
                                if current_user_id:
                                    try:
                                        _db_manager.upsert_character_affinity(
                                            user_id=current_user_id,
                                            character_name=character,
                                            affinity_change=change
                                        )
                                        print(f"🌍 Global affinity updated: {character} ({change:+d})")
                                    except Exception as global_err:
                                        print(f"⚠️ Failed to update global affinity for {character}: {global_err}")
                            except Exception as e:
                                print(f"⚠️ Failed to save affinity for {character}: {e}")

                    # 4. 최종 메타데이터 전송
                    final_meta = {
                        "type": "done",
                        "total_dialogues": sent_dialogue_count,
                        "turn_count": final_state.get("turn_count", 0),
                        "current_stage": final_state.get("current_stage"),
                        "affinity_scores": final_state.get("affinity_scores", {}),
                        "is_ended": final_state.get("is_ended", False),
                        "current_image": final_state.get("current_image"),
                        "output": final_state.get("output", {}),
                    }
                    yield f"data: {json.dumps(final_meta, ensure_ascii=False)}\n\n"

            except Exception as e:
                print(f"❌ Streaming error: {e}")
                import traceback
                traceback.print_exc()

                error_data = {
                    "type": "error",
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router", "set_dependencies"]
