#!/usr/bin/env python3
"""
FastAPI Server for KIME Chat Agent
- LangGraph 기반 멀티에이전트 워크플로우를 REST API 형태로 래핑
- 프론트엔드(React 등)에서 /api/chat 으로 요청을 보내면 여기서 처리함
"""

import os
import uuid
import json
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# ------------------------------------------------------------
# ✅ 환경변수 로드 (.env 파일에서 API 키 등 불러옴)
# ------------------------------------------------------------
load_dotenv(override=True)

# ------------------------------------------------------------
# ✅ LangGraph 관련 내부 모듈 로드
# ------------------------------------------------------------
from src.core.workflow import create_workflow  # 그래프 구성 생성기
from src.core.graph_state import (
    create_initial_graph_state,
    GraphState,
)  # 초기 상태 생성
from src.utils.scenario_loader import scenario_loader  # 시나리오(JSON) 로더
from src.tools.image_manager import ImageManager  # 이미지 매니저
from src.core.scenes_repo import ScenesRepo

# ------------------------------------------------------------
# ✅ FastAPI 인스턴스 생성
# ------------------------------------------------------------
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="1.0.0",
)

# ------------------------------------------------------------
# ✅ CORS 설정 (프론트엔드에서 API 호출 가능하게 허용)
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ],  # 허용할 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# ✅ 세션 저장소 (임시: 메모리 기반)
#    - 실제 서비스 환경에서는 Redis 등 외부 세션 스토어로 교체해야 함
# ------------------------------------------------------------
class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def load_or_create(self, session_id: str) -> Dict[str, Any]:
        state = self._sessions.get(session_id)
        if state is None:
            state = {}
            self._sessions[session_id] = state
        return state

    def save(self, session_id: str, state: Dict[str, Any]) -> None:
        self._sessions[session_id] = state

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions


SESSION_MANAGER = SessionManager()

# ------------------------------------------------------------
# ✅ Workflow 싱글톤 (LangGraph 파이프라인)
# ------------------------------------------------------------
workflow = None


# ------------------------------------------------------------
# ✅ LangGraph 워크플로우 가져오기 (싱글톤)
# ------------------------------------------------------------
def get_workflow():
    global workflow
    if workflow is None:
        workflow = create_workflow()
    return workflow


# ------------------------------------------------------------
# ✅ 시나리오 로더 (파일 or 캐시)
# ------------------------------------------------------------
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


# ============================================================
# 🧩 Request / Response 데이터 모델 정의
# ============================================================


class ChatRequest(BaseModel):
    """프론트엔드 → 백엔드 요청 구조"""

    session_id: Optional[str] = None
    scenario_id: str  # 예: "train", "ending", ...
    user_input: str  # 사용자의 입력 문장
    user_name: Optional[str] = "츠구코"  # 유저 이름 (없으면 기본값)


class DialogueResponse(BaseModel):
    """단일 대화 응답"""

    speaker: str
    content: str
    emotion: Optional[str] = "neutral"


class ChatResponse(BaseModel):
    """백엔드 → 프론트엔드 응답 구조"""

    session_id: str
    turn_count: int
    dialogues: List[DialogueResponse]
    current_stage: Optional[str] = None
    affinity_scores: Optional[Dict[str, int]] = None
    is_ended: bool = False  # 시나리오 종료 여부
    has_more: bool = False  # 더 생성할 대화가 남아있는지 여부
    system_message: Optional[str] = None  # 시스템 메시지 (fallback, 경고 등)
    current_image: Optional[str] = None  # 현재 표시할 이미지 파일명


class SessionInfoResponse(BaseModel):
    """세션 상태 조회 응답"""

    session_id: str
    scenario_id: str
    current_stage: Optional[str]
    turn_count: int
    affinity_scores: Dict[str, int]


# ============================================================
# 🧠 API 엔드포인트 구현부
# ============================================================


@app.get("/")
async def root():
    """서버 상태 확인용"""
    return {"status": "running", "service": "KIME Chat API", "version": "1.0.0"}


@app.post("/api/chat")
async def chat(request: Request):
    """
    메인 채팅 엔드포인트
    1. 세션 생성 or 복원
    2. 시나리오 로드
    3. LangGraph 실행
    4. 결과를 반환
    """
    try:
        request_start = time.perf_counter()
        data = await request.json()

        session_id = data.get("session_id")
        user_input = data.get("user_input", "")
        scenario_id = data.get("scenario_id")
        user_name = data.get("user_name") or "여행자"

        print(f"📥 Request received: session_id={session_id}, input='{user_input}'")

        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"🆕 Creating new session: {session_id}")
        else:
            print(f"🔁 Reusing session: {session_id}")

        state = SESSION_MANAGER.load_or_create(session_id)
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

            # 🧹 새 유저 입력 시 이전 output 클리어 (이미 전송됨)
            state["output"] = {}
            state["agent_responses"] = []

        # 스테이지별 대화 카운터 및 이미지 관련 필드 초기화
        state.setdefault("stage_dialogue_counts", {})
        state.setdefault("dialogues_generated_count", 0)
        state.setdefault("event_flags", [])
        state.setdefault("image_transition_history", [])

        print(f"🤖 Processing: session={session_id}, input='{user_input}'")
        workflow_instance = get_workflow()
        workflow_start = time.perf_counter()
        result_state = workflow_instance.invoke(state)
        workflow_end = time.perf_counter()
        workflow_duration_ms = (workflow_end - workflow_start) * 1000.0
        print(f"⏱️ Workflow execution time: {workflow_duration_ms:.2f} ms")

        turn_count = result_state.get("turn_count", 0) + 1
        result_state["turn_count"] = turn_count
        SESSION_MANAGER.save(session_id, result_state)

        print(
            f"💾 Session updated: stage={result_state.get('current_stage')}, stage_turn={result_state.get('stage_turn')}"
        )

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

        # ImageManager를 사용하여 각 대화별로 이미지 결정
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
            project_root = os.path.abspath(os.path.join(base_dir, ".."))

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

                # 각 대화마다 이미지를 분석하여 image_index 할당
                previous_image = current_image

                # 첫 대화이고 이전 이미지가 없으면 인트로 이미지(1번)로 시작
                if len(all_dialogues) > 0 and current_image is None:
                    all_dialogues[0]["image_index"] = "1"
                    previous_image = "1"
                    current_image = "1"
                    print(f"🖼️ [Dialogue 0] Initial image set to: 1 (intro)")

                for i, dialogue in enumerate(all_dialogues):
                    # 첫 대화는 이미 처리했으므로 스킵
                    if i == 0 and dialogue.get("image_index"):
                        continue

                    # 해당 대화 인덱스까지의 컨텍스트로 이미지 선택
                    new_image = image_manager.get_image_for_dialogue_at_index(
                        result_state, i
                    )

                    if new_image is not None and new_image != previous_image:
                        # 이미지가 변경되면 해당 대화에 image_index 추가
                        dialogue["image_index"] = new_image
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

        return JSONResponse(
            {
                "session_id": session_id,
                "dialogues": agent_responses,  # 루트 레벨에 dialogues
                "turn_count": result_state.get("turn_count", 0),
                "current_stage": result_state.get("current_stage"),
                "affinity_scores": result_state.get("affinity_scores", {}),
                "is_ended": result_state.get("is_ended", False),
                "has_more": has_more_flag,
                "current_image": current_image,  # 현재 이미지 파일명
                "output": result_state.get("output", {}),  # 하위 호환성을 위해 유지
            }
        )

    # ------------------------------------------------------------
    # (8) 예외 처리
    # ------------------------------------------------------------
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------
# ✅ 세션 상태 조회 (디버깅용)
# ------------------------------------------------------------
@app.get("/api/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """특정 세션의 현재 상태(스테이지, 친밀도 등) 반환"""
    state = SESSION_MANAGER.get(session_id)
    if not state or "messages" not in state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfoResponse(
        session_id=session_id,
        scenario_id=state.get("scenario_id", "unknown"),
        current_stage=state.get("current_stage"),
        turn_count=state.get("turn_count", 0),
        affinity_scores=state.get("affinity_scores", {}),
    )


# ------------------------------------------------------------
# ✅ 세션 삭제 (테스트용)
# ------------------------------------------------------------
@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """세션 강제 삭제"""
    if SESSION_MANAGER.exists(session_id):
        SESSION_MANAGER.delete(session_id)
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ------------------------------------------------------------
# ✅ 사용 가능한 시나리오 목록 조회 (프론트 시나리오 선택용)
# ------------------------------------------------------------
@app.get("/api/scenarios")
async def list_scenarios():
    """data/scenarios 폴더의 JSON 파일 목록 반환"""
    try:
        scenarios_dir = os.path.join("data", "scenarios")
        if not os.path.exists(scenarios_dir):
            return {"scenarios": []}

        scenarios = []
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".json"):
                scenario_id = filename.replace(".json", "")
                scenarios.append({"id": scenario_id})
        return {"scenarios": scenarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🚀 메인 실행부
# ============================================================
if __name__ == "__main__":
    import uvicorn

    # OpenAI 키 체크
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment")

    print("🚀 Starting KIME Chat API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")

    # FastAPI 실행
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 코드 변경 시 자동 리로드
        log_level="info",
    )
