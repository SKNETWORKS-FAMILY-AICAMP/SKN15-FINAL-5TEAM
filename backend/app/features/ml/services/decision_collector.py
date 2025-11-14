"""
DecisionCollector Service

모든 에이전트의 의사결정 데이터를 수집하는 서비스
"""
import time
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..repository import DecisionLogRepository
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("DecisionCollector")


class DecisionCollector:
    """
    에이전트 의사결정 수집 서비스

    모든 에이전트(Parent, Children, Router, Guardrail 등)에서 호출되어
    의사결정 데이터를 수집하고 저장합니다.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DecisionLogRepository(db)

    async def collect(
        self,
        session_id: UUID,
        agent_name: str,
        decision_type: str,
        decision_output: Dict[str, Any],
        turn_number: Optional[int] = None,
        user_input: Optional[str] = None,
        extracted_keywords: Optional[Dict[str, Any]] = None,
        context_state: Optional[Dict[str, Any]] = None,
        llm_prompt: Optional[str] = None,
        llm_parameters: Optional[Dict[str, Any]] = None,
        llm_model: Optional[str] = None,
        reasoning: Optional[str] = None,
        confidence: Optional[float] = None,
        execution_time_ms: Optional[int] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
    ) -> int:
        """
        의사결정 데이터 수집

        Args:
            session_id: 세션 ID
            agent_name: 에이전트 이름
                - "parent_agent": ParentAgent
                - "children_agent": ChildrenAgent
                - "router_agent": RouterAgent
                - "guardrail_agent": GuardrailAgent
                - "mission_service": MissionService
                - "affinity_service": AffinityService
            decision_type: 의사결정 타입
                - "stage_selection": 스테이지 핸들러 선택
                - "dialogue_generation": 대화 생성
                - "routing": 분기 선택
                - "mission_evaluation": 미션 성공/실패 평가
                - "affinity_update": 친밀도 변화
                - "input_guardrail": 입력 안전성 검증
                - "output_guardrail": 출력 안전성 검증
            decision_output: 의사결정 결과 (JSON)
            turn_number: 턴 번호
            user_input: 사용자 입력
            extracted_keywords: 추출된 키워드
            context_state: 현재 컨텍스트 상태
            llm_prompt: LLM 프롬프트
            llm_parameters: LLM 파라미터
            llm_model: LLM 모델명
            reasoning: 의사결정 이유
            confidence: 확신도 (0.0 ~ 1.0)
            execution_time_ms: 실행 시간 (밀리초)
            is_error: 에러 발생 여부
            error_message: 에러 메시지

        Returns:
            저장된 decision_id
        """
        try:
            logger.info(
                "collect",
                f"Collecting decision: {agent_name}/{decision_type}",
                session_id=session_id,
                turn_number=turn_number,
                has_keywords=extracted_keywords is not None,
            )

            decision_log = await self.repository.save_decision(
                session_id=session_id,
                turn_number=turn_number,
                agent_name=agent_name,
                decision_type=decision_type,
                decision_output=decision_output,
                user_input=user_input,
                extracted_keywords=extracted_keywords,
                context_state=context_state,
                llm_prompt=llm_prompt,
                llm_parameters=llm_parameters,
                llm_model=llm_model,
                reasoning=reasoning,
                confidence=confidence,
                execution_time_ms=execution_time_ms,
                is_error=is_error,
                error_message=error_message,
            )

            logger.info("collect", f"Decision collected successfully: {decision_log.decision_id}")
            return decision_log.decision_id

        except Exception as e:
            logger.error("collect", f"Failed to collect decision: {e}", exc_info=True)
            # 수집 실패해도 에이전트 동작에는 영향 없음
            return -1

    async def collect_with_timing(
        self,
        session_id: UUID,
        agent_name: str,
        decision_type: str,
        decision_output: Dict[str, Any],
        start_time: float,
        **kwargs,
    ) -> int:
        """
        실행 시간을 자동 계산하여 수집

        Args:
            session_id: 세션 ID
            agent_name: 에이전트 이름
            decision_type: 의사결정 타입
            decision_output: 의사결정 결과
            start_time: 시작 시간 (time.time())
            **kwargs: 기타 파라미터

        Returns:
            저장된 decision_id
        """
        execution_time_ms = int((time.time() - start_time) * 1000)

        return await self.collect(
            session_id=session_id,
            agent_name=agent_name,
            decision_type=decision_type,
            decision_output=decision_output,
            execution_time_ms=execution_time_ms,
            **kwargs,
        )

    async def collect_error(
        self,
        session_id: UUID,
        agent_name: str,
        decision_type: str,
        error_message: str,
        **kwargs,
    ) -> int:
        """
        에러 발생 시 수집

        Args:
            session_id: 세션 ID
            agent_name: 에이전트 이름
            decision_type: 의사결정 타입
            error_message: 에러 메시지
            **kwargs: 기타 파라미터

        Returns:
            저장된 decision_id
        """
        return await self.collect(
            session_id=session_id,
            agent_name=agent_name,
            decision_type=decision_type,
            decision_output={"error": error_message},
            is_error=True,
            error_message=error_message,
            **kwargs,
        )


class DecisionContext:
    """
    의사결정 컨텍스트 관리 헬퍼

    with 구문으로 자동 타이밍 측정 및 수집
    """

    def __init__(
        self,
        collector: DecisionCollector,
        session_id: UUID,
        agent_name: str,
        decision_type: str,
        **kwargs,
    ):
        self.collector = collector
        self.session_id = session_id
        self.agent_name = agent_name
        self.decision_type = decision_type
        self.kwargs = kwargs
        self.start_time = None
        self.decision_output = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    def set_output(self, decision_output: Dict[str, Any]):
        """의사결정 결과 설정"""
        self.decision_output = decision_output

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 동기 컨텍스트에서는 자동 수집 불가 (async 필요)
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 에러 발생
            await self.collector.collect_error(
                session_id=self.session_id,
                agent_name=self.agent_name,
                decision_type=self.decision_type,
                error_message=str(exc_val),
                **self.kwargs,
            )
        elif self.decision_output is not None:
            # 정상 종료
            await self.collector.collect_with_timing(
                session_id=self.session_id,
                agent_name=self.agent_name,
                decision_type=self.decision_type,
                decision_output=self.decision_output,
                start_time=self.start_time,
                **self.kwargs,
            )
