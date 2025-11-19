"""
Chat Feature - Controller
HTTP/WS 입출력, 인증, DTO 검증
Layer 1: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, AsyncGenerator
import json
import asyncio

from .schemas import ChatRequest, ChatResponse, ChatMessage
from .usecase import ChatUseCase
from .services.dialogue_service import DialogueService
from .sse_helper import sse_generator
from app.core.db.session import get_db
from app.core.logging import get_controller_logger, print_layer_debug
from app.core.errors import AppException
from app.core.auth import get_current_user_id

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

@router.post("")
async def create_chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    usecase: ChatUseCase = Depends(get_chat_usecase)
):
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
        # user_id는 JWT에서 이미 가져옴 (Depends(get_current_user_id))

        # ============================================================
        # 1. 세션 ID 생성 (없으면)
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
        # 5. 응답 구성 (대사 렌더링 - {user} 플레이스홀더 치환)
        # ============================================================
        dialogue_service = DialogueService()
        # State 준비 (렌더링에 필요한 user_name)
        render_state = {
            "user_name": request.user_name or dialogue_result.updated_state.get("user_name") or "여행자"
        }
        # 대사 렌더링 ({user} → 실제 사용자 이름)
        rendered_dialogues = dialogue_service.format_dialogues(
            [{"speaker": d.speaker, "text": d.text, "emotion": d.emotion} for d in dialogue_result.dialogues],
            render_state
        )
        # dict → ChatMessage 변환
        rendered_chat_messages = [
            ChatMessage(speaker=d["speaker"], text=d["text"], emotion=d.get("emotion", "neutral"))
            for d in rendered_dialogues
        ]

        # SSE 스트리밍으로 응답
        logger.info(
            "create_chat",
            "Streaming response",
            session_id=session_id,
            dialogues_count=len(rendered_chat_messages)
        )

        current_image = dialogue_result.current_image

        # ✅ 엔딩 정보 구성
        ending_info = {}
        if dialogue_result.session_ended:
            current_stage = dialogue_result.updated_state.get("current_stage", "")

            # 엔딩 타입별 메시지
            ending_messages = {
                "END_HIDDEN": {
                    "title": "🎉 히든 엔딩 달성!",
                    "message": "축하합니다! 모든 동료를 모아 최고의 결말에 도달했습니다.",
                    "type": "hidden"
                },
                "END_BASIC": {
                    "title": "✨ 스토리 완료",
                    "message": "축하합니다! 스토리가 완료되었습니다.",
                    "type": "basic"
                },
                "END_BAD": {
                    "title": "💔 배드 엔딩",
                    "message": "스토리가 완료되었습니다.",
                    "type": "bad"
                }
            }

            ending_info = ending_messages.get(current_stage, {
                "title": "✨ 스토리 완료",
                "message": "축하합니다! 스토리가 완료되었습니다.",
                "type": "normal"
            })
            ending_info["ending_id"] = current_stage

        # ✅ Router 스테이지에서 대화가 없으면 자동으로 다음 스테이지 호출
        current_stage = dialogue_result.updated_state.get("current_stage", "unknown")
        next_stage = dialogue_result.next_stage
        has_more = False

        # ✅ Router 스테이지 감지:
        # - 현재 스테이지가 router이거나
        # - 다음 스테이지로 전환 중이고 다음이 router인 경우
        is_current_router = current_stage.endswith("_ROUTER") or current_stage == "ROUTER"
        is_next_router = next_stage and (next_stage.endswith("_ROUTER") or next_stage == "ROUTER")

        # Stage 전환 중 (stage_complete=True이고 next_stage가 있음)
        is_transitioning = dialogue_result.stage_complete and next_stage and next_stage != current_stage

        logger.info("create_chat",
                   f"Checking auto-advance | current={current_stage} | next={next_stage} | "
                   f"is_current_router={is_current_router} | is_next_router={is_next_router} | "
                   f"transitioning={is_transitioning} | dialogues={len(rendered_chat_messages)}")

        # Router 스테이지로 전환 중이거나, Router 스테이지에서 대화가 없는 경우
        if (is_transitioning and is_next_router) or (is_current_router and len(rendered_chat_messages) == 0):
            has_more = True
            logger.info("create_chat", "✅ Router stage detected - setting has_more=True for auto-advance")

        return StreamingResponse(
            sse_generator(
                session_id=session_id,
                dialogues=rendered_chat_messages,
                turn_count=dialogue_result.updated_state.get("turn_count", 1),
                current_stage=dialogue_result.next_stage or dialogue_result.updated_state.get("current_stage", "intro"),
                affinity_scores=dialogue_result.affinity_scores or {},
                is_ended=dialogue_result.session_ended,  # ✅ 엔딩 스테이지 도달 시 세션 종료
                has_more=has_more,
                current_image=current_image,
                output={"ending": ending_info} if ending_info else {},
                memory_events=dialogue_result.memory_events,
                stage_turn=dialogue_result.updated_state.get("stage_turn", 0),
                user_language=request.user_language or "ko"  # ✅ 다국어 지원
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

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
    user_language: str = "ko",  # ✅ 다국어 지원
    usecase: ChatUseCase = Depends(get_chat_usecase)
) -> list[ChatMessage]:
    """
    세션의 대화 히스토리 조회 (다국어 지원)

    Args:
        session_id: 세션 ID
        limit: 조회 개수 (기본 10)
        user_language: 사용자 언어 (ko/en/ja)
        usecase: ChatUseCase

    Returns:
        ChatMessage 리스트 (번역된 텍스트)
    """
    logger.info("get_chat_history", "Request received", session_id=session_id, limit=limit, language=user_language)

    try:
        messages = await usecase.get_recent_dialogues(session_id, limit)

        # 번역 처리
        if user_language != "ko":
            from app.features.chat.services import TranslationService
            translator = TranslationService()

            for message in messages:
                if message.text:
                    translated_text = await translator.translate_dialogue(
                        text=message.text,
                        to_lang=user_language,
                        speaker=message.speaker,
                        emotion=message.emotion or "neutral"
                    )
                    message.text = translated_text

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


@router.post("/{session_id}/finalize")
async def finalize_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    usecase: ChatUseCase = Depends(get_chat_usecase)
) -> Dict[str, Any]:
    """
    세션 종료: 남은 대화 요약 및 메모리 추출

    Args:
        session_id: 세션 ID
        user_id: 사용자 ID (자동 주입)
        usecase: ChatUseCase

    Returns:
        종료 결과 (생성된 메모리 개수 포함)
    """
    logger.info("finalize_session", "Finalize request received",
               session_id=session_id, user_id=user_id)

    try:
        result = await usecase.finalize_session(
            session_id=session_id,
            user_id=user_id
        )

        if not result["success"]:
            logger.warning("finalize_session", "Finalization failed",
                          session_id=session_id, error=result.get("error"))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Session finalization failed")
            )

        logger.info("finalize_session", "Session finalized successfully",
                   session_id=session_id, memories_created=result["memories_created"])

        return {
            "success": True,
            "message": result.get("message", "Session finalized"),
            "memories_created": result["memories_created"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("finalize_session", "Error", exc=e, session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to finalize session"
        )
