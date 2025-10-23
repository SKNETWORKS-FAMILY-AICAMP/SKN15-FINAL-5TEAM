#!/usr/bin/env python3
"""
FastAPI Server for KIME Chat Agent
- LangGraph 기반 멀티에이전트 워크플로우를 REST API 형태로 래핑
- 프론트엔드(React 등)에서 /api/chat 으로 요청을 보내면 여기서 처리함
"""

import os
import uuid
import json
from typing import Dict, Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ------------------------------------------------------------
# ✅ 환경변수 로드 (.env 파일에서 API 키 등 불러옴)
# ------------------------------------------------------------
load_dotenv(override=True)

# ------------------------------------------------------------
# ✅ LangGraph 관련 내부 모듈 로드
# ------------------------------------------------------------
from src.core.workflow import create_workflow             # 그래프 구성 생성기
from src.core.graph_state import create_initial_graph_state, GraphState  # 초기 상태 생성
from src.utils.scenario_loader import scenario_loader     # 시나리오(JSON) 로더

# ------------------------------------------------------------
# ✅ FastAPI 인스턴스 생성
# ------------------------------------------------------------
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="1.0.0"
)

# ------------------------------------------------------------
# ✅ CORS 설정 (프론트엔드에서 API 호출 가능하게 허용)
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173"
    ],  # 허용할 프론트엔드 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# ✅ 세션 저장소 (임시: 메모리 기반)
#    - 실제 서비스 환경에서는 Redis 등 외부 세션 스토어로 교체해야 함
# ------------------------------------------------------------
sessions: Dict[str, GraphState] = {}

# ------------------------------------------------------------
# ✅ Workflow 싱글톤 (LangGraph 파이프라인)
# ------------------------------------------------------------
workflow = None


# ------------------------------------------------------------
# ✅ 프론트엔드 시나리오 ID → 백엔드 시나리오 파일 매핑
# ------------------------------------------------------------
SCENARIO_MAPPING = {
    "train": "cutscene5_llm_driven",      # 무한열차 시나리오
    "ending": "cutscene5_llm_driven",     # 엔딩 이후 (동일 파일 사용)
    "infinity-castle": "cutscene5_akaza_encounter",  # 무한성 시나리오
    "tanjiro": "cutscene5_simple",        # 편의점 탄지로
    "counseling": "cutscene5_simple",     # 상담소
    "idol": "cutscene5_simple",           # 아이돌/밴드 버전
}

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
        backend_filename = SCENARIO_MAPPING.get(scenario_id, scenario_id)

        # 우선 scenario_loader(커스텀 로더) 사용
        data = scenario_loader.load_scenario(backend_filename)
        if data:
            return data

        # Fallback: 직접 파일에서 로드
        scenario_path = os.path.join("data", "scenarios", f"{backend_filename}.json")
        if os.path.exists(scenario_path):
            with open(scenario_path, "r", encoding="utf-8") as f:
                return json.load(f)

        print(f"⚠️ Scenario '{scenario_id}' (mapped to '{backend_filename}') not found")
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
    user_input: str   # 사용자의 입력 문장
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
    is_ended: bool = False       # 시나리오 종료 여부
    has_more: bool = False       # 더 생성할 대화가 남아있는지 여부
    system_message: Optional[str] = None  # 시스템 메시지 (fallback, 경고 등)


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
    return {
        "status": "running",
        "service": "KIME Chat API",
        "version": "1.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    메인 채팅 엔드포인트
    1. 세션 생성 or 복원
    2. 시나리오 로드
    3. LangGraph 실행
    4. 결과를 대화 형식으로 반환
    """
    try:
        # ------------------------------------------------------------
        # (1) 세션 생성 or 복원
        # ------------------------------------------------------------
        session_id = request.session_id or str(uuid.uuid4())

        if session_id not in sessions:
            print(f"🆕 Creating new session: {session_id}")

            backend_scenario_id = SCENARIO_MAPPING.get(request.scenario_id, request.scenario_id)
            scenario_data = load_scenario(request.scenario_id)
            if not scenario_data:
                raise HTTPException(status_code=404, detail=f"Scenario '{request.scenario_id}' not found")

            # 초기 GraphState 생성
            state = create_initial_graph_state(
                session_id=session_id,
                scenario_id=backend_scenario_id
            )

            # 시나리오 데이터 세팅
            state["scenario_data"] = scenario_data
            state["scenario_id"] = backend_scenario_id
            state["user_name"] = request.user_name or "여행자"

            # 첫 스테이지 결정
            stages = scenario_data.get("stages", [])
            if isinstance(stages, dict):
                initial_stage = list(stages.keys())[0] if stages else "intro"
            elif isinstance(stages, list) and len(stages) > 0:
                initial_stage = stages[0].get("tag") or stages[0].get("id") or "intro"
            else:
                initial_stage = "intro"
            state["current_stage"] = initial_stage

            # 세션 저장
            sessions[session_id] = state

        else:
            # 기존 세션 로드
            state = sessions[session_id]

        # ------------------------------------------------------------
        # (2) 유저 입력 저장
        # ------------------------------------------------------------
        state["user_input"] = request.user_input
        state["user_inputs"] = state.get("user_inputs", []) + [request.user_input]

        # 자동 입력이 아닌 경우에만 배치 카운터 리셋
        if not request.user_input.startswith("__AUTO_CONTINUE__"):
            state["dialogue_batch_index"] = 0
            state["dialogues_generated_count"] = 0

        # ------------------------------------------------------------
        # (3) LangGraph 실행
        # ------------------------------------------------------------
        print(f"🤖 Processing: session={session_id}, input='{request.user_input}'")
        workflow_instance = get_workflow()
        result_state = workflow_instance.invoke(state)

        # ------------------------------------------------------------
        # (4) 세션 상태 업데이트
        # ------------------------------------------------------------
        sessions[session_id] = result_state

        # ------------------------------------------------------------
        # (5) 대화 응답 구성
        # ------------------------------------------------------------
        agent_responses = result_state.get("output", {}).get("dialogues", [])
        dialogues = []
        for response in agent_responses:
            if isinstance(response, dict):
                dialogues.append(DialogueResponse(
                    speaker=response.get("speaker", "system"),
                    content=response.get("text") or response.get("content", ""),
                    emotion=response.get("emotion", "neutral")
                ))

        # ------------------------------------------------------------
        # (6) 시나리오 종료 판정
        # ------------------------------------------------------------
        is_ended = (
            result_state.get("final_ending") is not None
            or result_state.get("next_node") == "END"
            or result_state.get("current_stage", "").lower() in ["end", "ending", "end_hidden", "end_bad"]
        )

        # ------------------------------------------------------------
        # (7) 응답 객체 생성
        # ------------------------------------------------------------
        turn_count = result_state.get("turn_count", 0) + 1
        result_state["turn_count"] = turn_count

        has_more = result_state.get("has_more_dialogues", False)
        print(f"🔍 DEBUG: has_more={has_more}, batch_index={result_state.get('dialogue_batch_index')}")

        response = ChatResponse(
            session_id=session_id,
            turn_count=turn_count,
            dialogues=dialogues,
            current_stage=result_state.get("current_stage"),
            affinity_scores=result_state.get("affinity_scores"),
            is_ended=is_ended,
            has_more=has_more,
            system_message=result_state.get("error_message")
        )

        print(f"✅ Response sent: {len(dialogues)} dialogues, has_more: {has_more}")
        return response

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
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    return SessionInfoResponse(
        session_id=session_id,
        scenario_id=state.get("scenario_id", "unknown"),
        current_stage=state.get("current_stage"),
        turn_count=state.get("turn_count", 0),
        affinity_scores=state.get("affinity_scores", {})
    )


# ------------------------------------------------------------
# ✅ 세션 삭제 (테스트용)
# ------------------------------------------------------------
@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """세션 강제 삭제"""
    if session_id in sessions:
        del sessions[session_id]
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
        reload=True,   # 코드 변경 시 자동 리로드
        log_level="info"
    )
