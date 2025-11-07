"""
Send Message Use Case

채팅 메시지 전송 비즈니스 로직
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from core.interfaces.repositories.session_repository import ISessionRepository
from core.interfaces.repositories.conversation_repository import IConversationRepository
from core.interfaces.managers.session_manager import ISessionManager
from core.exceptions.domain_exceptions import EntityNotFoundError, UnauthorizedError


@dataclass
class SendMessageRequest:
    """메시지 전송 요청 DTO"""
    session_id: str
    user_id: str
    message: str


@dataclass
class SendMessageResponse:
    """메시지 전송 응답 DTO"""
    dialogue_id: int
    session_id: str
    user_input: str
    agent_response: str
    turn_number: int
    metadata: Optional[Dict[str, Any]] = None


class SendMessageUseCase:
    """
    채팅 메시지 전송 Use Case

    책임:
    1. 세션 유효성 검증
    2. 사용자 권한 확인
    3. 대화 저장
    4. 턴 카운트 증가
    """

    def __init__(
        self,
        session_repository: ISessionRepository,
        conversation_repository: IConversationRepository,
        session_manager: ISessionManager
    ):
        """
        Args:
            session_repository: 세션 리포지토리 (DI)
            conversation_repository: 대화 리포지토리 (DI)
            session_manager: 세션 관리자 (DI)
        """
        self._session_repo = session_repository
        self._conversation_repo = conversation_repository
        self._session_manager = session_manager

    async def execute(
        self,
        request: SendMessageRequest,
        agent_response: str  # Agent에서 생성된 응답 (별도 처리)
    ) -> SendMessageResponse:
        """
        메시지 전송 실행

        Args:
            request: 메시지 전송 요청 DTO
            agent_response: AI 에이전트 응답

        Returns:
            SendMessageResponse

        Raises:
            EntityNotFoundError: 세션 없음
            UnauthorizedError: 권한 없음
        """
        # 1. 세션 조회
        session = self._session_repo.get_by_id(request.session_id)
        if not session:
            raise EntityNotFoundError(f"Session {request.session_id} not found")

        # 2. 권한 확인
        if session['user_id'] != request.user_id:
            raise UnauthorizedError("Not authorized to access this session")

        # 3. 턴 카운트 증가
        turn_number = self._session_manager.increment_turn_count(request.session_id)

        # 4. 대화 저장
        dialogue_id = self._conversation_repo.save_dialogue(
            session_id=request.session_id,
            turn_number=turn_number,
            user_input=request.message,
            agent_response=agent_response,
            metadata={'user_id': request.user_id}
        )

        return SendMessageResponse(
            dialogue_id=dialogue_id,
            session_id=request.session_id,
            user_input=request.message,
            agent_response=agent_response,
            turn_number=turn_number
        )
