"""
사용자 장기 기억 관리 라우터
- 메모리 생성·조회·수정·삭제 기능 제공
- 벡터 유사도로 메모리를 검색
- 세션별 저장된 기억을 조회
"""

# ============================================================
# ============================================================
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional

try:
    from backend.api.schemas.api_models import (
        MemoryCreateRequest,
        MemoryUpdateRequest,
        MemoryResponse,
        MemorySearchRequest,
        MessageResponse,
    )
except ModuleNotFoundError:
    from api.schemas.api_models import (
        MemoryCreateRequest,
        MemoryUpdateRequest,
        MemoryResponse,
        MemorySearchRequest,
        MessageResponse,
    )

try:
    from backend.api.dependencies.api_deps import get_db_manager
except ModuleNotFoundError:
    from api.dependencies.api_deps import get_db_manager

try:
    from backend.api.dependencies.auth_deps import require_auth
except ModuleNotFoundError:
    try:
        from api.dependencies.auth_deps import require_auth
    except ModuleNotFoundError:
        from src.auth.dependencies import require_auth

try:
    from backend.src.infrastructure.database.db_manager import DatabaseManager
except ModuleNotFoundError:
    from src.infrastructure.database.db_manager import DatabaseManager

try:
    from backend.src.utils.conversation_summarizer import generate_embedding
except ModuleNotFoundError:
    from src.utils.conversation_summarizer import generate_embedding

router = APIRouter()


@router.get("", response_model=List[Dict])
async def get_user_memories(
    memory_type: Optional[str] = Query(
        None,
        description="기억 타입 필터 (character_preference, user_fact, game_progress, etc.)"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="반환할 최대 개수"),
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    사용자의 장기 기억 목록 조회

    Args:
        memory_type: 기억 타입 필터 (선택)
        limit: 반환할 최대 개수 (기본 50)

    Returns:
        메모리 목록
    """
    try:
        memories = db.get_user_memories(
            user_id=user["user_id"],
            memory_type=memory_type,
            limit=limit
        )
        return memories if memories else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")


@router.get("/{memory_key}", response_model=Dict)
async def get_memory_by_key(
    memory_key: str,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    특정 키로 기억 조회

    Args:
        memory_key: 기억 키 (예: "favorite_character")

    Returns:
        메모리 객체 또는 404
    """
    try:
        memory = db.get_memory_by_key(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return memory
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memory: {str(e)}")


@router.post("", response_model=Dict)
async def create_memory(
    memory_data: Dict,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    새로운 기억 생성

    Args:
        memory_data: {
            "memory_key": str (required),
            "memory_value": str (required),
            "memory_type": str (optional, default: "fact"),
            "importance": float (optional, 0.0-1.0),
            "tags": List[str] (optional),
            "context": Dict (optional),
            "confidence": float (optional, 0.0-1.0)
        }

    Returns:
        {"success": bool, "memory_id": int}
    """
    try:
        # 필수 필드 검증
        if "memory_key" not in memory_data or "memory_value" not in memory_data:
            raise HTTPException(status_code=400, detail="memory_key and memory_value are required")

        # 입력 텍스트 기반 임베딩 생성 (존재하는 경우)
        embedding = None
        if memory_data.get("memory_value"):
            embedding = generate_embedding(memory_data["memory_value"])

        # upsert 형태로 메모리 저장
        memory_id = db.create_or_update_memory(
            user_id=user["user_id"],
            memory_key=memory_data["memory_key"],
            memory_value=memory_data["memory_value"],
            memory_type=memory_data.get("memory_type", "fact"),
            importance=memory_data.get("importance", 0.5),
            tags=memory_data.get("tags"),
            context=memory_data.get("context"),
            confidence=memory_data.get("confidence"),
            embedding=embedding
        )

        if not memory_id:
            raise HTTPException(status_code=500, detail="Failed to create memory")

        return {"success": True, "memory_id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@router.put("/{memory_key}", response_model=Dict)
async def update_memory(
    memory_key: str,
    memory_data: Dict,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    기존 기억 업데이트

    Args:
        memory_key: 업데이트할 기억 키
        memory_data: {
            "memory_value": str (required),
            "memory_type": str (optional),
            "importance": float (optional),
            "tags": List[str] (optional),
            "context": Dict (optional),
            "confidence": float (optional)
        }

    Returns:
        {"success": bool, "memory_id": int}
    """
    try:
        # 기존 메모리 조회
        existing_memory = db.get_memory_by_key(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not existing_memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # 필수 업데이트 필드 확인
        if "memory_value" not in memory_data:
            raise HTTPException(status_code=400, detail="memory_value is required")

        embedding = None
        if memory_data.get("memory_value"):
            embedding = generate_embedding(memory_data["memory_value"])

        memory_id = db.create_or_update_memory(
            user_id=user["user_id"],
            memory_key=memory_key,
            memory_value=memory_data["memory_value"],
            memory_type=memory_data.get("memory_type", existing_memory.get("memory_type", "fact")),
            importance=memory_data.get("importance", existing_memory.get("importance", 0.5)),
            tags=memory_data.get("tags", existing_memory.get("tags")),
            context=memory_data.get("context", existing_memory.get("context")),
            confidence=memory_data.get("confidence", existing_memory.get("confidence")),
            embedding=embedding
        )

        if not memory_id:
            raise HTTPException(status_code=500, detail="Failed to update memory")

        return {"success": True, "memory_id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update memory: {str(e)}")


@router.delete("/{memory_key}", response_model=MessageResponse)
async def delete_memory(
    memory_key: str,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    기억 삭제 (소프트 삭제)

    Args:
        memory_key: 삭제할 기억 키

    Returns:
        성공 메시지
    """
    try:
        success = db.delete_memory(
            user_id=user["user_id"],
            memory_key=memory_key
        )

        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {"message": "Memory deleted successfully", "status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@router.post("/search", response_model=List[Dict])
async def search_memories_by_similarity(
    search_data: Dict,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    의미 기반 기억 검색 (Vector Similarity Search)

    Args:
        search_data: {
            "query": str (required) - 검색 쿼리,
            "limit": int (optional, default: 5) - 반환할 최대 개수,
            "min_importance": float (optional, default: 0.0) - 최소 중요도
        }

    Returns:
        유사도순으로 정렬된 메모리 목록
    """
    try:
        if "query" not in search_data:
            raise HTTPException(status_code=400, detail="query is required")

        # 쿼리 문장 임베딩 생성
        query_embedding = generate_embedding(search_data["query"])

        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        # 벡터 유사도 검색 실행
        memories = db.search_memories_by_similarity(
            user_id=user["user_id"],
            query_embedding=query_embedding,
            limit=search_data.get("limit", 5),
            min_importance=search_data.get("min_importance", 0.0)
        )

        return memories if memories else []

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.get("/session/{session_id}", response_model=List[Dict])
async def get_memories_by_session(
    session_id: str,
    user: Dict = Depends(require_auth),
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    특정 세션에서 생성된 기억 조회

    Args:
        session_id: 세션 ID

    Returns:
        해당 세션에서 생성된 메모리 목록
    """
    try:
        memories = db.get_user_memories(
            user_id=user["user_id"],
            limit=100  # Higher limit for session-specific queries
        )

        session_memories = [
            m for m in memories
            if m.get("source_session_id") == session_id
        ]

        return session_memories

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session memories: {str(e)}")
