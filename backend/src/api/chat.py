"""
Chat Router
대화 시스템 엔드포인트 (LangGraph 워크플로우 실행)
"""

import os
import uuid
import json
import time
import asyncio
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

from src.auth.dependencies import require_auth
from src.core.workflow import create_workflow
from src.core.graph_state import create_initial_graph_state
from src.utils.scenario_loader import scenario_loader
from src.tools.image_manager import ImageManager
from src.core.scenes_repo import ScenesRepo
from src.infrastructure.database.db_manager import DatabaseManager
from src.api.dependencies import get_db_manager, get_workflow, get_session_manager

# ============================================================
# Router 생성
# ============================================================
router = APIRouter()


# ============================================================
# Helper Functions
# ============================================================

def load_scenario(scenario_id: str) -> Optional[Dict]:
    """Frontend ID로 요청받은 시나리오를 JSON으로 로드"""
    try:
        if not scenario_id:
            return None

        candidates = []
        if scenario_id.endswith(".json"):
            candidates.append(scenario_id)
        else:
            candidates.extend([scenario_id, f"{scenario_id}.json"])

        for candidate in candidates:
            data = scenario_loader.load_scenario(candidate)
            if data:
                return data

        repo = ScenesRepo()
        for candidate in candidates:
            result = repo.load(candidate.replace(".json", ""))
            if result:
                return result

        print(f"⚠️ Scenario '{scenario_id}' not found")
        return None
    except Exception as e:
        print(f"❌ Error loading scenario '{scenario_id}': {e}")
        return None


async def process_post_response_tasks(
    session_id: str,
    user_id: str,
    result_state: Dict[str, Any],
    user_input: str,
    agent_responses: List[Dict],
    turn_count: int,
    current_user: Dict,
    db_manager: DatabaseManager,
    session_manager
):
    """
    응답 반환 후 백그라운드에서 실행할 작업들

    ⚡ 성능 최적화: 사용자 응답에 영향을 주지 않는 작업들을 백그라운드에서 처리
    - 대화 요약 생성
    - 메모리 추출
    - 친밀도 추적
    - 스테이지 추적
    - Dialogues 저장
    """
    print(f"🔄 [Background] Starting post-response tasks for session {session_id}")

    try:
        # 1. Dialogues 저장
        from src.utils.conversation_summarizer import update_conversation_summary

        try:
            db_manager.save_dialogues(
                session_id=session_id,
                user_id=user_id,
                scenario_id=result_state.get("scenario_id"),
                dialogues=agent_responses,
                turn_count=turn_count
            )
            print(f"💾 [Background] Dialogues saved: {len(agent_responses)} dialogues")
        except Exception as e:
            print(f"❌ [Background] Failed to save dialogues: {e}")

        # 2. 대화 요약 업데이트 (10턴마다)
        if turn_count % 10 == 0:
            try:
                await update_conversation_summary(
                    session_id=session_id,
                    user_id=user_id,
                    db_manager=db_manager,
                    session_manager=session_manager
                )
                print(f"📝 [Background] Conversation summary updated (turn {turn_count})")
            except Exception as e:
                print(f"❌ [Background] Failed to update conversation summary: {e}")

        # 3. 메모리 추출 (5턴마다)
        if turn_count % 5 == 0:
            try:
                from src.utils.memory_extractor import extract_and_save_memories
                await extract_and_save_memories(
                    session_id=session_id,
                    user_id=user_id,
                    db_manager=db_manager,
                    session_manager=session_manager
                )
                print(f"🧠 [Background] Memories extracted (turn {turn_count})")
            except Exception as e:
                print(f"❌ [Background] Failed to extract memories: {e}")

        # 4. 친밀도 추적
        try:
            old_affinity = result_state.get("_old_affinity", {})
            new_affinity = result_state.get("affinity_scores", {})

            if old_affinity != new_affinity:
                db_manager.track_affinity_change(
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
                db_manager.track_stage_change(
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
# Chat Endpoint
# ============================================================

@router.post("")
async def chat(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(require_auth),
    db_manager: DatabaseManager = Depends(get_db_manager),
    workflow = Depends(get_workflow),
    session_manager = Depends(get_session_manager)
):
    """
    메인 채팅 엔드포인트 (🔐 로그인 필수)
    1. JWT 토큰 검증 (로그인하지 않으면 401 에러)
    2. 세션 생성 or 복원
    3. 시나리오 로드
    4. LangGraph 실행
    5. 결과를 반환

    Args:
        request: HTTP 요청 객체
        current_user: 인증된 사용자 정보 (필수, JWT 토큰에서 추출)

    Returns:
        StreamingResponse: 에이전트 응답 (SSE)

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
            session_manager.save_log(
                log_level="info",
                log_message=f"Authenticated user: {username}",
                session_id=None,  # 아직 session_id 없음
                metadata={"user_id": user_id, "username": username}
            )
        except Exception as e:
            print(f"⚠️ Failed to save user auth log: {e}")

        print(f"📥 Request received: session_id={session_id}, input='{user_input}'")

        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"🆕 Creating new session: {session_id}")
            # 📝 General Log: 새 세션 생성
            try:
                session_manager.save_log(
                    log_level="info",
                    log_message="New session created",
                    session_id=session_id,
                    metadata={"user_id": user_id, "scenario_id": scenario_id}
                )
            except Exception as e:
                print(f"⚠️ Failed to save session creation log: {e}")
        else:
            print(f"🔁 Reusing session: {session_id}")
            # 📝 General Log: 세션 재사용
            try:
                session_manager.save_log(
                    log_level="info",
                    log_message="Session reused",
                    session_id=session_id,
                    metadata={"user_id": user_id}
                )
            except Exception as e:
                print(f"⚠️ Failed to save session reuse log: {e}")

        state = session_manager.load_or_create(session_id)
        is_new_session = "messages" not in state

        if is_new_session:
            if not scenario_id:
                raise HTTPException(
                    status_code=400, detail="scenario_id is required to start a session"
                )

            scenario_data = load_scenario(scenario_id)
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
            state["user_id"] = user_id  # ✅ 추가: 사용자 ID 저장

            # 🧠 사용자 장기 기억 로드 (인증된 사용자만)
            if user_id:
                try:
                    memory_context = db_manager.get_user_memory_context(user_id)
                    if memory_context:
                        state["user_memory_context"] = memory_context

                        # 로드된 기억 개수 출력
                        rel_count = len(memory_context.get("relationships", []) or [])
                        pref_count = len(memory_context.get("preferences", []) or [])
                        story_count = len(memory_context.get("story_progress", []) or [])
                        fact_count = len(memory_context.get("facts", []) or [])

                        print(f"🧠 User memories loaded for {current_user.get('username')}:")
                        print(f"   - Relationships: {rel_count}")
                        print(f"   - Preferences: {pref_count}")
                        print(f"   - Story progress: {story_count}")
                        print(f"   - Facts: {fact_count}")

                        # 📝 General Log: 메모리 로딩 성공
                        try:
                            session_manager.save_log(
                                log_level="info",
                                log_message=f"User memories loaded: {rel_count + pref_count + story_count + fact_count} total",
                                session_id=session_id,
                                metadata={
                                    "user_id": user_id,
                                    "username": current_user.get('username'),
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

                        # 📝 General Log: 메모리 없음
                        try:
                            session_manager.save_log(
                                log_level="info",
                                log_message="No user memories found",
                                session_id=session_id,
                                metadata={"user_id": user_id}
                            )
                        except Exception as log_err:
                            print(f"⚠️ Failed to save no-memory log: {log_err}")
                except Exception as e:
                    print(f"⚠️ Failed to load user memories: {e}")

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

        if not state.get("scenario_data") and scenario_id:
            scenario_data = load_scenario(scenario_id)
            if scenario_data:
                state["scenario_data"] = scenario_data
                state["scenario"] = scenario_data
                state.setdefault(
                    "scenario_id", scenario_data.get("scenario_id") or scenario_id
                )

        state["session_id"] = session_id
        state["user_input"] = user_input
        state["user_inputs"] = state.get("user_inputs", []) + [user_input]

        # 🔥 배치 모드 관리: 새 사용자 입력 시 배치 인덱스만 리셋
        # dialogues_generated_count는 세션 전체에 걸쳐 누적 유지
        if not user_input.startswith("__AUTO_CONTINUE__"):
            state["dialogue_batch_index"] = 0
            # state["dialogues_generated_count"]는 리셋하지 않음 (누적)

        # 스테이지별 대화 카운터 및 이미지 관련 필드 초기화
        state.setdefault("stage_dialogue_counts", {})
        state.setdefault("dialogues_generated_count", 0)
        state.setdefault("event_flags", [])
        state.setdefault("image_transition_history", [])

        print(f"🤖 Processing: session={session_id}, input='{user_input}'")

        # ⚡ 백그라운드 처리를 위해 workflow 실행 전 상태 저장
        state["_old_affinity"] = state.get("affinity_scores", {}).copy()
        state["_old_stage"] = state.get("current_stage")

        workflow_start = time.perf_counter()

        try:
            result_state = workflow.invoke(state)
        except Exception as e:
            # 🚨 Workflow 실행 실패 에러 로깅
            try:
                session_manager.save_error_log(
                    error_type="workflow_execution_failed",
                    error_message=str(e),
                    session_id=session_id,
                    metadata={
                        "stage": state.get("current_stage"),
                        "turn_count": state.get("turn_count"),
                        "user_input": user_input[:100] if user_input else None
                    }
                )
            except:
                pass  # 에러 로깅 실패해도 원래 에러는 발생시켜야 함
            raise

        workflow_end = time.perf_counter()
        workflow_duration_ms = (workflow_end - workflow_start) * 1000.0

        # 📊 Performance Metric 저장: Workflow 실행 시간
        try:
            session_manager.save_performance_metric(
                metric_name="workflow_execution_time",
                metric_value=workflow_duration_ms,
                session_id=session_id,
                metadata={
                    "stage": result_state.get("current_stage"),
                    "turn_count": result_state.get("turn_count")
                }
            )
        except Exception as e:
            print(f"⚠️ Failed to save performance metric: {e}")

        print(f"⏱️ Workflow execution time: {workflow_duration_ms:.2f} ms")

        # ⚡ turn_count 증가 (백그라운드 작업에서 사용)
        turn_count = result_state.get("turn_count", 0) + 1
        result_state["turn_count"] = turn_count

        # ✅ user_id 보존: 워크플로우가 반환한 state에 user_id가 없으면 복원
        if "user_id" not in result_state or result_state.get("user_id") is None:
            if user_id:
                result_state["user_id"] = user_id
                print(f"🔧 Restored user_id to result_state: {user_id}")

        # ⚡ 백그라운드 처리를 위해 old 상태 복사 (result_state에도 추가)
        result_state["_old_affinity"] = state.get("_old_affinity", {})
        result_state["_old_stage"] = state.get("_old_stage")

        # 📊 세션 저장 성능 측정 (응답에 필수)
        session_save_start = time.perf_counter()
        session_manager.save(session_id, result_state)
        session_save_duration_ms = (time.perf_counter() - session_save_start) * 1000.0

        # 📊 Performance Metric 저장: 세션 저장 시간
        try:
            session_manager.save_performance_metric(
                metric_name="session_save_time",
                metric_value=session_save_duration_ms,
                session_id=session_id,
                metadata={
                    "stage": result_state.get("current_stage"),
                    "turn_count": turn_count
                }
            )
        except Exception as e:
            print(f"⚠️ Failed to save performance metric: {e}")

        print(
            f"💾 Session updated: stage={result_state.get('current_stage')}, stage_turn={result_state.get('stage_turn')}"
        )

        # ⚡ 백그라운드 작업 등록 (응답 후 실행)
        # 무거운 작업들(요약, 메모리, 친밀도, 스테이지, dialogues)을 백그라운드에서 처리
        agent_responses = result_state.get("output", {}).get("dialogues", [])
        background_tasks.add_task(
            process_post_response_tasks,
            session_id=session_id,
            user_id=user_id,
            result_state=result_state.copy(),  # state 복사로 thread safety 확보
            user_input=user_input,
            agent_responses=agent_responses,
            turn_count=turn_count,
            current_user=current_user,
            db_manager=db_manager,
            session_manager=session_manager
        )

        print(f"🚀 Background tasks registered for post-response processing")

        # ⚡ 응답 데이터 준비 (이미지 선택은 응답에 필요하므로 여기서 처리)
        agent_responses = result_state.get("output", {}).get("dialogues", [])
        has_more_flag = result_state.get("has_more")
        if has_more_flag is None:
            has_more_flag = result_state.get("has_more_dialogues", False)
        result_state["has_more"] = has_more_flag

        print(
            f"✅ Response sent: {len(agent_responses)} dialogues, has_more: {has_more_flag}"
        )
        if agent_responses:
            for idx, dialogue in enumerate(agent_responses):
                if isinstance(dialogue, dict):
                    speaker = dialogue.get("speaker") or dialogue.get("character") or "unknown"
                    content = dialogue.get("content") or dialogue.get("text") or ""
                else:
                    speaker = "unknown"
                    content = str(dialogue)
                print(f"🧠 LLM Output[{idx}] ({speaker}): {content}")

        # ImageManager를 사용하여 각 대화별로 이미지 결정 (응답에 필요하므로 여기서 처리)
        current_image = result_state.get("current_image")  # 이전 이미지
        scenario_id_for_image = result_state.get("scenario_id", scenario_id)
        print(f"🔍 ImageManager debug: scenario_id={scenario_id_for_image}")

        scenario_reference = (
            result_state.get("scenario")
            or result_state.get("scenario_data")
            or state.get("scenario")
            or state.get("scenario_data")
            or {}
        )
        images_meta: Dict[str, Any] = {}
        if isinstance(scenario_reference, dict):
            images_meta = (scenario_reference.get("metadata") or {}).get("images") or {}

        mapping_pattern = images_meta.get("mapping_pattern")
        llm_metadata_config = images_meta.get("llm_metadata")

        if scenario_id_for_image:
            base_dir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))

            def resolve_path(path_value: Optional[str]) -> Optional[str]:
                if not path_value:
                    return None
                if os.path.isabs(path_value):
                    return path_value
                candidate_backend = os.path.abspath(os.path.join(base_dir, path_value))
                if os.path.exists(candidate_backend):
                    return candidate_backend
                return os.path.abspath(os.path.join(project_root, path_value))

            if mapping_pattern and "{scenario_id" in mapping_pattern:
                formatted = mapping_pattern.format(scenario_id=scenario_id_for_image)
                image_config_candidate = formatted
            elif mapping_pattern:
                image_config_candidate = mapping_pattern
            else:
                image_config_candidate = os.path.join(
                    "data", "image_mappings", f"{scenario_id_for_image}_cutscenes.json"
                )

            image_config_path = resolve_path(image_config_candidate)
            abs_path = image_config_path or image_config_candidate
            print(f"🔍 Checking image config path: {abs_path}")
            print(f"🔍 File exists: {os.path.exists(image_config_path or '')}")

            if scenario_id_for_image not in globals().get("image_managers", {}):
                if image_config_path and os.path.exists(image_config_path):
                    if "image_managers" not in globals():
                        globals()["image_managers"] = {}

                    metadata_path = resolve_path(llm_metadata_config)
                    use_llm = bool(metadata_path)

                    globals()["image_managers"][scenario_id_for_image] = ImageManager(
                        config_path=image_config_path,
                        debug=True,
                        use_llm=use_llm,
                        llm_metadata_path=metadata_path,
                    )
                    status_label = "enabled" if use_llm else "disabled"
                    print(
                        f"📸 ImageManager loaded for scenario: {scenario_id_for_image} (LLM {status_label})"
                    )
                else:
                    print(f"⚠️ Image config not found at: {abs_path}")

            # ImageManager가 있으면 각 대화별로 이미지 분석
            image_manager = (
                globals().get("image_managers", {}).get(scenario_id_for_image)
            )
            print(f"🔍 DEBUG: scenario_id_for_image={scenario_id_for_image}")
            print(
                f"🔍 DEBUG: image_managers keys={list(globals().get('image_managers', {}).keys())}"
            )
            print(f"🔍 DEBUG: image_manager={image_manager}")
            if image_manager:
                # 전체 대화 목록을 가져옴 (result_state의 output.dialogues)
                all_dialogues = result_state.get("output", {}).get("dialogues", [])

                # 🚀 배치 처리: 전체 대화를 한 번에 분석 (LLM 1회 호출)
                previous_image = current_image

                # 첫 대화이고 이전 이미지가 없으면 인트로 이미지(1번)로 시작
                if len(all_dialogues) > 0 and current_image is None:
                    all_dialogues[0]["image_index"] = "1"
                    previous_image = "1"
                    current_image = "1"
                    print(f"🖼️ [Dialogue 0] Initial image set to: 1 (intro)")

                # 배치로 모든 대화의 이미지 선택 (1회 LLM 호출)
                selected_images = image_manager.select_images_batch(result_state)

                if selected_images:
                    for i, new_image in enumerate(selected_images):
                        # 첫 대화는 이미 처리했으므로 스킵
                        if i == 0 and all_dialogues[i].get("image_index"):
                            previous_image = all_dialogues[i]["image_index"]
                            continue

                        if new_image is not None and new_image != previous_image:
                            # 이미지가 변경되면 해당 대화에 image_index 추가
                            all_dialogues[i]["image_index"] = new_image
                            previous_image = new_image
                            current_image = new_image
                            print(f"🖼️ [Dialogue {i}] Image changed to: {new_image}")

                # 최종 current_image를 세션에 저장
                result_state["current_image"] = current_image
                print(f"✅ Final image state: {current_image}")
            else:
                print(f"⚠️ No ImageManager found for scenario: {scenario_id_for_image}")

        # 프론트엔드 호환성을 위해 dialogues를 루트 레벨로 이동
        total_duration_ms = (time.perf_counter() - request_start) * 1000.0
        print(f"⏱️ Total chat handler time: {total_duration_ms:.2f} ms")

        # 🌊 Streaming Response 구현 (부분 스트리밍)
        async def generate_stream():
            """SSE 형식으로 응답을 점진적으로 전송"""
            try:
                # 1. 메타데이터 먼저 전송
                meta_data = {
                    "type": "metadata",
                    "session_id": session_id,
                    "turn_count": result_state.get("turn_count", 0),
                    "current_stage": result_state.get("current_stage"),
                    "affinity_scores": result_state.get("affinity_scores", {}),
                    "is_ended": result_state.get("is_ended", False),
                    "has_more": has_more_flag,
                    "current_image": current_image,
                }
                yield f"data: {json.dumps(meta_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)  # 이벤트 루프 양보

                # 2. 각 dialogue를 개별적으로 전송
                for idx, dialogue in enumerate(agent_responses):
                    dialogue_data = {
                        "type": "dialogue",
                        "index": idx,
                        "dialogue": dialogue
                    }
                    yield f"data: {json.dumps(dialogue_data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.8)  # 타이핑 효과 (0.8초 간격)

                # 3. 완료 신호 전송
                done_data = {
                    "type": "done",
                    "total_dialogues": len(agent_responses),
                    "output": result_state.get("output", {}),
                }
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
                "Connection": "keep-alive",
            }
        )

    # ------------------------------------------------------------
    # 예외 처리
    # ------------------------------------------------------------
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
