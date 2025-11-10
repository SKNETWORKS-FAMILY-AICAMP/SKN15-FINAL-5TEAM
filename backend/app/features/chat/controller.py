"""
Chat Feature - Controller
HTTP/WS 입출력, 인증, DTO 검증
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .schemas import ChatRequest, ChatResponse, ChatMessage
from .usecase import ChatUseCase
from app.core.db.session import get_db
from app.core.logging import get_controller_logger, print_layer_debug
from app.core.errors import AppException

logger = get_controller_logger("Chat")

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================================
# 의존성 주입
# ============================================================

def get_chat_usecase(db: AsyncSession = Depends(get_db)) -> ChatUseCase:
    """
    ChatUseCase 의존성

    Controller는 UseCase만 알면 됨
    UseCase 내부에서 Repository와 Agent 관리
    """
    return ChatUseCase(db)


# ============================================================
# 엔드포인트
# ============================================================

@router.post("", response_model=ChatResponse)
async def create_chat(
    request: ChatRequest,
    usecase: ChatUseCase = Depends(get_chat_usecase),
    # current_user: Dict = Depends(get_current_user)  # TODO: 인증 추가
) -> ChatResponse:
    """
    [Layer 1] Controller
    책임: HTTP 입출력, 인증, DTO 검증, UseCase 호출
    금지: 비즈니스 로직, DB 직접 접근

    채팅 메시지 전송 및 응답

    Args:
        request: ChatRequest (Pydantic이 자동 검증)
        usecase: ChatUseCase (의존성 주입)
        current_user: 인증된 사용자 (JWT)

    Returns:
        ChatResponse

    Raises:
        HTTPException 400: 잘못된 요청
        HTTPException 401: 인증 실패
        HTTPException 500: 서버 에러
    """
    print_layer_debug(
        "CONTROLLER", "Chat", "create_chat",
        "Request received",
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        user_input_len=len(request.user_input)
    )
    logger.info(
        "create_chat",
        "Request received",
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        user_input_length=len(request.user_input)
    )

    try:
        # ============================================================
        # 1. 인증 (TODO: 실제 인증 구현)
        # ============================================================
        # user_id = current_user.get("user_id")
        # 임시: 인증 없이 게스트로 처리 (sessions 테이블의 user_id는 NULL 허용)
        user_id = None

        # ============================================================
        # 2. 세션 ID 생성 (없으면)
        # ============================================================
        session_id = request.session_id
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            logger.info("create_chat", "New session created", session_id=session_id)

        # ============================================================
        # 3. UseCase 호출 (세션 로딩은 UseCase 내부에서 처리)
        # ============================================================
        print_layer_debug("CONTROLLER", "Chat", "create_chat", "→ Calling UseCase")

        dialogue_result = await usecase.create_dialogue(
            user_id=user_id,
            session_id=session_id,
            scenario_id=request.scenario_id,
            user_message=request.user_input,
            user_name=request.user_name or "여행자"
        )

        # ============================================================
        # 5. 응답 구성
        # ============================================================
        response = ChatResponse(
            session_id=session_id,
            turn_count=dialogue_result.updated_state.get("turn_count", 1),
            dialogues=dialogue_result.dialogues,
            current_stage=dialogue_result.next_stage or dialogue_result.updated_state.get("current_stage", "intro"),
            affinity_scores=dialogue_result.updated_state.get("affinity_scores", {}),
            is_ended=False,  # TODO: 시나리오 종료 체크
            has_more=False,
        )

        logger.info(
            "create_chat",
            "Response sent",
            session_id=session_id,
            dialogues_count=len(response.dialogues),
            status=200
        )
        print_layer_debug(
            "CONTROLLER", "Chat", "create_chat",
            "✅ Response sent",
            dialogues=len(response.dialogues)
        )

        return response

    except AppException as e:
        # 애플리케이션 예외는 그대로 전파 (에러 핸들러가 처리)
        logger.error("create_chat", f"Application error: {e.message}", error_code=e.error_code)
        raise

    except Exception as e:
        # 예상치 못한 에러
        logger.exception("create_chat", "Unexpected error", exc=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/stream", response_model=ChatResponse)
async def create_chat_stream(
    request: ChatRequest,
    usecase: ChatUseCase = Depends(get_chat_usecase),
) -> ChatResponse:
    """
    채팅 메시지 전송 (스트림 엔드포인트, 현재는 일반 응답과 동일)
    TODO: SSE 스트리밍 구현
    """
    return await create_chat(request, usecase)


@router.get("/{session_id}/history", response_model=list[ChatMessage])
async def get_chat_history(
    session_id: str,
    limit: int = 10,
    usecase: ChatUseCase = Depends(get_chat_usecase)
) -> list[ChatMessage]:
    """
    세션의 대화 히스토리 조회

    Args:
        session_id: 세션 ID
        limit: 조회 개수 (기본 10)
        usecase: ChatUseCase

    Returns:
        ChatMessage 리스트
    """
    logger.info("get_chat_history", "Request received", session_id=session_id, limit=limit)

    try:
        messages = await usecase.get_recent_dialogues(session_id, limit)

        logger.info("get_chat_history", f"Response sent: {len(messages)} messages", session_id=session_id)
        return messages

    except Exception as e:
        logger.exception("get_chat_history", "Error", exc=e, session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )


@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    usecase: ChatUseCase = Depends(get_chat_usecase)
) -> Dict[str, Any]:
    """
    세션 삭제

    Args:
        session_id: 세션 ID
        usecase: ChatUseCase

    Returns:
        삭제 결과
    """
    logger.warning("delete_chat_session", "Delete request received", session_id=session_id)

    try:
        count = await usecase.delete_session(session_id)

        logger.warning("delete_chat_session", f"Session deleted: {count} dialogues", session_id=session_id)
        return {
            "success": True,
            "message": f"Session deleted: {count} dialogues removed",
            "dialogues_deleted": count
        }

    except Exception as e:
        logger.exception("delete_chat_session", "Error", exc=e, session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )
