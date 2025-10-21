#!/usr/bin/env python3
"""
FastAPI Server for KIME Chat Agent
Wraps LangGraph workflow and exposes REST API for frontend integration
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

# Load environment variables
load_dotenv(override = True)

# Import existing LangGraph components
from src.core.workflow import create_workflow
from src.core.graph_state import create_initial_graph_state, GraphState
from src.utils.scenario_loader import scenario_loader

# Initialize FastAPI app
app = FastAPI(
    title="KIME Chat API",
    description="Backend API for KIME Chat Agent using LangGraph",
    version="1.0.0"
)

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (TODO: Replace with Redis for production)
sessions: Dict[str, GraphState] = {}

# Workflow singleton
workflow = None

# Scenario ID mapping (frontend ID -> backend filename)
SCENARIO_MAPPING = {
    "train": "cutscene5_llm_driven",  # 무한열차 시나리오
    "ending": "cutscene5_llm_driven",  # 엔딩 이후 (동일 파일 사용, 다른 스테이지)
    "infinity-castle": "cutscene5_akaza_encounter",  # 무한성 시나리오
    "tanjiro": "cutscene5_simple",  # 편의점 탄지로
    "counseling": "cutscene5_simple",  # 상담소
    "idol": "cutscene5_simple",  # 아이돌/밴드
}


def get_workflow():
    """Get or create workflow singleton"""
    global workflow
    if workflow is None:
        workflow = create_workflow()
    return workflow


def load_scenario(scenario_id: str) -> Optional[Dict]:
    """Load scenario data from JSON with frontend-to-backend mapping"""
    try:
        # Map frontend scenario ID to backend filename
        backend_filename = SCENARIO_MAPPING.get(scenario_id, scenario_id)

        # Try loading with scenario_loader
        data = scenario_loader.load_scenario(backend_filename)
        if data:
            return data

        # Fallback: try loading from file directly
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
# Request/Response Models
# ============================================================

class ChatRequest(BaseModel):
    """Chat request from frontend"""
    session_id: Optional[str] = None
    scenario_id: str  # e.g., "train", "ending", "infinity-castle"
    user_input: str
    user_name: Optional[str] = "여행자"


class DialogueResponse(BaseModel):
    """Single dialogue response"""
    speaker: str
    content: str
    emotion: Optional[str] = "neutral"


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    session_id: str
    turn_count: int
    dialogues: List[DialogueResponse]
    current_stage: Optional[str] = None
    affinity_scores: Optional[Dict[str, int]] = None
    is_ended: bool = False
    has_more: bool = False  # 더 생성할 대화가 있는지 여부 (배치 모드)
    system_message: Optional[str] = None


class SessionInfoResponse(BaseModel):
    """Session information response"""
    session_id: str
    scenario_id: str
    current_stage: Optional[str]
    turn_count: int
    affinity_scores: Dict[str, int]


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "KIME Chat API",
        "version": "1.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint

    - Creates new session if session_id is not provided
    - Loads scenario if not already loaded
    - Invokes LangGraph workflow
    - Returns dialogue responses
    """
    try:
        # 1. Session management
        session_id = request.session_id or str(uuid.uuid4())

        if session_id not in sessions:
            # Create new session
            print(f"🆕 Creating new session: {session_id}")

            # Load scenario (with frontend-to-backend mapping)
            backend_scenario_id = SCENARIO_MAPPING.get(request.scenario_id, request.scenario_id)
            scenario_data = load_scenario(request.scenario_id)
            if not scenario_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Scenario '{request.scenario_id}' not found"
                )

            # Initialize state with BACKEND scenario_id (not frontend ID!)
            state = create_initial_graph_state(
                session_id=session_id,
                scenario_id=backend_scenario_id  # 🔥 Use backend ID for logic
            )

            # Set scenario data
            state["scenario_data"] = scenario_data
            state["scenario_id"] = backend_scenario_id  # 🔥 Use backend ID (e.g., "cutscene5_llm_driven")
            state["user_name"] = request.user_name or "여행자"

            # Determine initial stage from scenario
            stages = scenario_data.get("stages", [])
            if isinstance(stages, dict):
                # Dict format: use first key or "intro"
                initial_stage = list(stages.keys())[0] if stages else "intro"
            elif isinstance(stages, list) and len(stages) > 0:
                # List format: use first stage's tag
                initial_stage = stages[0].get("tag") or stages[0].get("id") or "intro"
            else:
                initial_stage = "intro"

            state["current_stage"] = initial_stage

            sessions[session_id] = state
        else:
            # Use existing session
            state = sessions[session_id]

        # 2. Update user input
        state["user_input"] = request.user_input
        state["user_inputs"] = state.get("user_inputs", []) + [request.user_input]

        # 배치 모드 리셋: 사용자가 새 메시지를 보낸 경우 배치 카운터 리셋
        # (자동 요청이 아닌 경우에만 리셋)
        if not request.user_input.startswith("__AUTO_CONTINUE__"):
            state["dialogue_batch_index"] = 0
            state["dialogues_generated_count"] = 0

        # 3. Invoke workflow
        print(f"🤖 Processing: session={session_id}, input='{request.user_input}'")
        workflow_instance = get_workflow()
        result_state = workflow_instance.invoke(state)

        # 4. Update session with result
        sessions[session_id] = result_state

        # 5. Extract dialogues from output.dialogues (배치 모드 지원)
        # dialogue_agent가 state["output"]["dialogues"]에 저장함
        agent_responses = result_state.get("output", {}).get("dialogues", [])
        dialogues = []

        for response in agent_responses:
            if isinstance(response, dict):
                dialogues.append(DialogueResponse(
                    speaker=response.get("speaker", "system"),
                    content=response.get("text") or response.get("content", ""),
                    emotion=response.get("emotion", "neutral")
                ))

        # 6. Check if ended
        is_ended = (
            result_state.get("final_ending") is not None
            or result_state.get("next_node") == "END"
            or result_state.get("current_stage", "").lower() in ["end", "ending", "end_hidden", "end_bad"]
        )

        # 7. Prepare response
        turn_count = result_state.get("turn_count", 0) + 1
        result_state["turn_count"] = turn_count

        # 배치 모드: has_more 플래그 확인
        has_more = result_state.get("has_more_dialogues", False)
        print(f"🔍 DEBUG: has_more_dialogues={result_state.get('has_more_dialogues')}, batch_index={result_state.get('dialogue_batch_index')}, count={result_state.get('dialogues_generated_count')}")

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

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """Get session information"""
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


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/scenarios")
async def list_scenarios():
    """List available scenarios"""
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
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment")

    print("🚀 Starting KIME Chat API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
