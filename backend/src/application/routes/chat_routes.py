"""
채팅 라우터
- LangGraph 기반 대화 흐름을 처리하는 엔드포인트 모음
- 세션 관리, 백그라운드 후처리, 스트리밍 응답을 담당
"""

# ============================================================
# 💬 채팅 라우터 — 랭그래프 대화 흐름 처리
# ============================================================
import uuid
import time
import json
import asyncio
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

# 4-layer 아키텍처 imports
from ..dependencies.auth_deps import require_auth
from ..dependencies.api_deps import (
    get_workflow,
    get_session_manager,
    get_scenario_loader,
    get_session_repository,
    get_memory_repository,
)
from src.core import create_initial_graph_state
from src.core.interfaces.repositories.session_repository import ISessionRepository
from src.core.interfaces.repositories.memory_repository import IMemoryRepository
from src.domain.services.evaluation.memory_extractor import extract_and_save_memories

# TODO: 이 모듈들은 Domain Service로 분리 필요
# - ChatSessionService: 세션 생성/로드
# - ChatWorkflowService: 워크플로우 실행
# - ChatImageService: 이미지 선택
# - ChatBackgroundService: 백그라운드 작업

# ============================================================
# 라우터 생성
# ============================================================
router = APIRouter()


# ============================================================
# 백그라운드 작업
# ============================================================
async def process_post_response_tasks(
    session_id: str,
    user_id: str,
    result_state: Dict,
    user_input: str,
    agent_responses: list,
    turn_count: int,
    current_user: Dict,
    session_repository: ISessionRepository,
    memory_repository: IMemoryRepository,
    session_manager
):
    """
    응답 반환 후 백그라운드에서 실행할 작업들

    Repository Pattern 기반으로 리팩터링됨
    """
    print(f"🔄 [Background] Starting post-response tasks for session {session_id}")

    try:
        # 1. 대사 저장
        try:
            session_repository.save_dialogues(
                session_id=session_id,
                turn_number=turn_count,
                dialogues=agent_responses,
                user_id=user_id,
                scenario_id=result_state.get("scenario_id")
            )
            print(f"💾 [Background] Dialogues saved: {len(agent_responses)} dialogues")
        except Exception as e:
            print(f"❌ [Background] Failed to save dialogues: {e}")

        # 2. 대화 요약 업데이트 (10턴마다)
        if turn_count % 10 == 0:
            try:
                # TODO: update_conversation_summary needs refactoring to use repositories
                # For now, skipping to avoid DatabaseManager dependency
                print("📝 [Background] Conversation summary update skipped (needs refactoring)")
            except Exception as e:
                print(f"❌ [Background] Failed to update conversation summary: {e}")

        # 3. 메모리 추출 (5턴마다)
        if turn_count % 5 == 0:
            try:
                conversation_summary = result_state.get("conversation_summary")
                if not conversation_summary:
                    session_state = session_manager.load_or_create(
                        session_id,
                        result_state.get("scenario_id", ""),
                        create_if_missing=False,
                    )
                    conversation_summary = (
                        (session_state or {}).get("conversation_summary") if session_state else None
                    )

                await extract_and_save_memories(
                    user_id=user_id,
                    session_id=session_id,
                    conversation_summary=conversation_summary or "",
                    memory_repository=memory_repository,
                )
                print(f"🧠 [Background] Memories extracted (turn {turn_count})")
            except Exception as e:
                print(f"❌ [Background] Failed to extract memories: {e}")

        # 4. 친밀도 추적
        try:
            old_affinity = result_state.get("_old_affinity", {})
            new_affinity = result_state.get("affinity_scores", {})

            if old_affinity != new_affinity:
                session_repository.track_affinity_change(
                    session_id=session_id,
                    user_id=user_id,
                    affinity_changes={
                        char: new_affinity.get(char, 0) - old_affinity.get(char, 0)
                        for char in set(list(old_affinity.keys()) + list(new_affinity.keys()))
                    }
                )
                print(f"❤️ [Background] Affinity tracked")
        except Exception as e:
            print(f"❌ [Background] Failed to track affinity: {e}")

        # 5. 스테이지 추적
        try:
            old_stage = result_state.get("_old_stage")
            new_stage = result_state.get("current_stage")

            if old_stage != new_stage:
                session_repository.track_stage_change(
                    session_id=session_id,
                    user_id=user_id,
                    old_stage=old_stage,
                    new_stage=new_stage
                )
                print(f"🎭 [Background] Stage tracked: {old_stage} -> {new_stage}")
        except Exception as e:
            print(f"❌ [Background] Failed to track stage: {e}")

        print(f"✅ [Background] Post-response tasks completed for session {session_id}")

    except Exception as e:
        print(f"❌ [Background] Unexpected error in post-response tasks: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# 세션 초기화 헬퍼
# ============================================================
def initialize_session_state(
    session_id: str,
    scenario_id: str,
    user_name: str,
    user_id: str,
    scenario_loader
) -> Dict:
    """
    새 세션 상태 초기화 (Repository Pattern 기반)
    """
    scenario_data = scenario_loader.load_scenario(scenario_id)
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

    # 사용자 장기 기억 로드
    if user_id:
        try:
            memory_repo = get_memory_repository()
            memory_context = memory_repo.get_user_memory_context(user_id)
            if memory_context:
                state["user_memory_context"] = memory_context
                rel_count = len(memory_context.get("relationships", []) or [])
                pref_count = len(memory_context.get("preferences", []) or [])
                story_count = len(memory_context.get("story_progress", []) or [])
                fact_count = len(memory_context.get("facts", []) or [])
                print(f"🧠 User memories loaded: {rel_count + pref_count + story_count + fact_count} total")
        except Exception as e:
            print(f"⚠️ Failed to load user memories: {e}")

    # 초기 스테이지 설정
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

    return state


# ============================================================
# 🧵 기본 채팅 엔드포인트
# ============================================================
@router.post("")
async def chat(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth),
    session_repository: ISessionRepository = Depends(get_session_repository),
    memory_repository: IMemoryRepository = Depends(get_memory_repository),
    workflow = Depends(get_workflow),
    session_manager = Depends(get_session_manager),
    scenario_loader = Depends(get_scenario_loader)
):
    """
    메인 채팅 엔드포인트 (🔐 로그인 필수)

    TODO: 이 함수를 Use Case 패턴으로 리팩토링
    - ProcessChatMessageUseCase(request) -> response
    """
    try:
        request_start = time.perf_counter()
        data = await request.json()

        session_id = data.get("session_id")
        user_input = data.get("user_input", "")
        scenario_id = data.get("scenario_id")
        user_name = data.get("user_name") or "여행자"
        user_id = current_user.get('user_id')

        print(f"🔐 Authenticated user: {current_user.get('username')} (ID: {user_id})")

        # 세션 ID 생성 또는 재사용
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"🆕 Creating new session: {session_id}")
        else:
            print(f"🔁 Reusing session: {session_id}")

        if not scenario_id:
            raise HTTPException(
                status_code=400, detail="scenario_id is required to start a session"
            )

        # 세션 로드 또는 생성
        state = session_manager.load_or_create(
            session_id=session_id,
            scenario_id=scenario_id,
            user_name=user_name,
            create_if_missing=True
        )
        is_new_session = "messages" not in state

        if is_new_session:
            state = initialize_session_state(
                session_id, scenario_id, user_name, user_id,
                scenario_loader
            )
        else:
            print(f"🔄 Loading existing session: {session_id}")
            if user_name:
                state["user_name"] = user_name

        # 시나리오 데이터 확인
        if not state.get("scenario_data") and scenario_id:
            scenario_data = scenario_loader.load_scenario(scenario_id)
            if scenario_data:
                state["scenario_data"] = scenario_data
                state["scenario"] = scenario_data
                state.setdefault(
                    "scenario_id", scenario_data.get("scenario_id") or scenario_id
                )

        # 상태 업데이트
        state["session_id"] = session_id
        state["user_input"] = user_input
        state["user_inputs"] = state.get("user_inputs", []) + [user_input]

        if not user_input.startswith("__AUTO_CONTINUE__"):
            state["dialogue_batch_index"] = 0

        state.setdefault("stage_dialogue_counts", {})
        state.setdefault("dialogues_generated_count", 0)
        state.setdefault("event_flags", [])
        state.setdefault("image_transition_history", [])

        print(f"🤖 Processing: session={session_id}, input='{user_input}'")

        # 변경 추적을 위한 이전 상태 저장
        state["_old_affinity"] = state.get("affinity_scores", {}).copy()
        state["_old_stage"] = state.get("current_stage")

        # 워크플로우 실행
        workflow_start = time.perf_counter()
        result_state = workflow.invoke(state)
        workflow_duration_ms = (time.perf_counter() - workflow_start) * 1000.0
        print(f"⏱️ Workflow execution time: {workflow_duration_ms:.2f} ms")

        # 턴 카운트 증가
        turn_count = result_state.get("turn_count", 0) + 1
        result_state["turn_count"] = turn_count

        if "user_id" not in result_state or result_state.get("user_id") is None:
            if user_id:
                result_state["user_id"] = user_id

        result_state["_old_affinity"] = state.get("_old_affinity", {})
        result_state["_old_stage"] = state.get("_old_stage")

        # 세션 저장
        session_manager.save(session_id, result_state)
        print(f"💾 Session updated: turn={turn_count}")

        # 백그라운드 작업 등록
        agent_responses = result_state.get("output", {}).get("dialogues", [])
        background_tasks.add_task(
            process_post_response_tasks,
            session_id=session_id,
            user_id=user_id,
            result_state=result_state.copy(),
            user_input=user_input,
            agent_responses=agent_responses,
            turn_count=turn_count,
            current_user=current_user,
            session_repository=session_repository,
            memory_repository=memory_repository,
            session_manager=session_manager
        )

        # 응답 준비
        has_more_flag = result_state.get("has_more")
        if has_more_flag is None:
            has_more_flag = result_state.get("has_more_dialogues", False)

        current_image = result_state.get("current_image")

        total_duration_ms = (time.perf_counter() - request_start) * 1000.0
        print(f"⏱️ Total chat handler time: {total_duration_ms:.2f} ms")

        return {
            "session_id": session_id,
            "turn_count": turn_count,
            "dialogues": agent_responses,
            "current_stage": result_state.get("current_stage"),
            "affinity_scores": result_state.get("affinity_scores", {}),
            "is_ended": result_state.get("is_ended", False),
            "has_more": has_more_flag,
            "current_image": current_image,
            "output": result_state.get("output", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 📡 스트리밍 채팅 엔드포인트
# ============================================================
@router.post("/stream")
async def chat_stream(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth),
    session_repository: ISessionRepository = Depends(get_session_repository),
    memory_repository: IMemoryRepository = Depends(get_memory_repository),
    workflow = Depends(get_workflow),
    session_manager = Depends(get_session_manager),
    scenario_loader = Depends(get_scenario_loader)
):
    """
    SSE 스트리밍 채팅 엔드포인트 (🔐 로그인 필수)

    TODO: chat() 함수와 중복 코드 제거 - 공통 로직을 Service로 분리
    """

    async def generate_events():
        try:
            data = await request.json()
            session_id = data.get("session_id")
            user_input = data.get("user_input", "")
            scenario_id = data.get("scenario_id")
            user_name = data.get("user_name") or "여행자"
            user_id = current_user.get('user_id')

            if not session_id:
                session_id = str(uuid.uuid4())

            # 세션 로드 또는 생성 (chat()과 동일)
            state = session_manager.load_or_create(
                session_id=session_id,
                scenario_id=scenario_id,
                user_name=user_name,
                create_if_missing=True
            )
            is_new_session = "messages" not in state

            if is_new_session:
                state = initialize_session_state(
                    session_id, scenario_id, user_name, user_id,
                    scenario_loader
                )

            state["session_id"] = session_id
            state["user_input"] = user_input

            # 워크플로우 실행
            result_state = workflow.invoke(state)
            turn_count = result_state.get("turn_count", 0) + 1
            result_state["turn_count"] = turn_count

            session_manager.save(session_id, result_state)

            agent_responses = result_state.get("output", {}).get("dialogues", [])

            # 메타데이터 전송
            metadata = {
                "session_id": session_id,
                "turn_count": turn_count,
                "current_stage": result_state.get("current_stage"),
                "affinity_scores": result_state.get("affinity_scores", {}),
                "is_ended": result_state.get("is_ended", False),
                "has_more": result_state.get("has_more", False),
                "current_image": result_state.get("current_image"),
            }
            yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

            # 대화 스트리밍
            for idx, dialogue in enumerate(agent_responses):
                if await request.is_disconnected():
                    break

                dialogue_data = {
                    "index": idx,
                    "total": len(agent_responses),
                    "dialogue": dialogue
                }
                yield f"event: dialogue\ndata: {json.dumps(dialogue_data)}\n\n"
                await asyncio.sleep(0.3)

            yield f"event: complete\ndata: {json.dumps({'completed': True})}\n\n"

            # 백그라운드 작업
            background_tasks.add_task(
                process_post_response_tasks,
                session_id=session_id,
                user_id=user_id,
                result_state=result_state.copy(),
                user_input=user_input,
                agent_responses=agent_responses,
                turn_count=turn_count,
                current_user=current_user,
                session_repository=session_repository,
                memory_repository=memory_repository,
                session_manager=session_manager
            )

        except Exception as e:
            print(f"❌ [SSE] Error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
