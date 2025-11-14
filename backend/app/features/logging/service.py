"""
Logging Feature - Service Layer
통합 로깅 서비스 (편리한 접근)
Layer 2: Service (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
from functools import wraps

from app.core.logging import get_usecase_logger
from .repository import LoggingRepository

logger = get_usecase_logger("LoggingService")


class LoggingService:
    """
    통합 로깅 서비스

    책임: 시스템 로그, 에러 로그, 성능 메트릭, AI 학습 로그 편리한 인터페이스 제공
    """

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: 데이터베이스 세션
        """
        self.db = db
        self.repository = LoggingRepository(db)

    # ============================================================
    # 시스템 로그
    # ============================================================

    async def log_info(
        self,
        message: str,
        session_id: Optional[str] = None,
        **context
    ):
        """INFO 레벨 로그"""
        await self.repository.create_log(
            log_level="INFO",
            message=message,
            session_id=session_id,
            context_data=context
        )

    async def log_warning(
        self,
        message: str,
        session_id: Optional[str] = None,
        **context
    ):
        """WARNING 레벨 로그"""
        await self.repository.create_log(
            log_level="WARNING",
            message=message,
            session_id=session_id,
            context_data=context
        )

    async def log_error(
        self,
        message: str,
        session_id: Optional[str] = None,
        **context
    ):
        """ERROR 레벨 로그"""
        await self.repository.create_log(
            log_level="ERROR",
            message=message,
            session_id=session_id,
            context_data=context
        )

    async def log_debug(
        self,
        message: str,
        session_id: Optional[str] = None,
        **context
    ):
        """DEBUG 레벨 로그"""
        await self.repository.create_log(
            log_level="DEBUG",
            message=message,
            session_id=session_id,
            context_data=context
        )

    # ============================================================
    # 에러 로그
    # ============================================================

    async def log_exception(
        self,
        exception: Exception,
        session_id: Optional[str] = None,
        **context
    ):
        """
        Exception을 에러 로그로 기록

        Args:
            exception: Exception 객체
            session_id: 세션 ID
            **context: 추가 컨텍스트
        """
        await self.repository.create_error_from_exception(
            exception=exception,
            session_id=session_id,
            context_data=context
        )

        logger.info("log_exception", "Exception logged",
                   exception_type=type(exception).__name__,
                   session_id=session_id)

    async def get_recent_errors(
        self,
        limit: int = 20,
        session_id: Optional[str] = None
    ):
        """최근 에러 로그 조회"""
        return await self.repository.get_error_logs(
            session_id=session_id,
            limit=limit
        )

    # ============================================================
    # 성능 메트릭
    # ============================================================

    async def record_latency(
        self,
        operation_name: str,
        latency_ms: float,
        **tags
    ):
        """
        레이턴시 메트릭 기록

        Args:
            operation_name: 작업 이름 (예: llm_call, db_query)
            latency_ms: 레이턴시 (ms)
            **tags: 추가 태그 (model, endpoint 등)
        """
        await self.repository.record_metric(
            metric_name=f"{operation_name}_latency",
            metric_value=latency_ms,
            metric_unit="ms",
            tags=tags
        )

    async def record_count(
        self,
        metric_name: str,
        count: int = 1,
        **tags
    ):
        """
        카운트 메트릭 기록

        Args:
            metric_name: 메트릭 이름
            count: 카운트
            **tags: 추가 태그
        """
        await self.repository.record_metric(
            metric_name=metric_name,
            metric_value=float(count),
            metric_unit="count",
            tags=tags
        )

    async def get_performance_stats(
        self,
        metric_name: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        성능 통계 조회

        Args:
            metric_name: 메트릭 이름
            hours: 시간 범위 (시간)

        Returns:
            통계 딕셔너리 (avg, min, max, count)
        """
        time_window = timedelta(hours=hours)
        return await self.repository.get_metric_stats(
            metric_name=metric_name,
            time_window=time_window
        )

    def measure_time(self, operation_name: str, **tags):
        """
        함수 실행 시간 측정 데코레이터

        Usage:
            @logging_service.measure_time("my_function", component="chat")
            async def my_function():
                ...
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    await self.record_latency(operation_name, elapsed_ms, **tags)
                    return result
                except Exception as e:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    await self.record_latency(f"{operation_name}_error", elapsed_ms, **tags)
                    raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    # Cannot await in sync function - would need separate handling
                    return result
                except Exception as e:
                    raise

            # Check if async
            if hasattr(func, '__code__') and func.__code__.co_flags & 0x100:
                return async_wrapper
            return sync_wrapper

        return decorator

    # ============================================================
    # AI 학습 로그
    # ============================================================

    async def log_llm_call(
        self,
        session_id: str,
        turn_count: int,
        agent_name: str,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
        latency_ms: Optional[int] = None,
        llm_model: Optional[str] = None,
        token_count: Optional[int] = None,
        **kwargs
    ):
        """
        LLM 호출 로그 기록

        Args:
            session_id: 세션 ID
            turn_count: 턴 번호
            agent_name: 에이전트 이름
            context: 입력 컨텍스트
            model_output: 모델 출력
            latency_ms: 레이턴시 (ms)
            llm_model: LLM 모델명
            token_count: 토큰 수
            **kwargs: 추가 파라미터
        """
        await self.repository.create_training_log(
            session_id=session_id,
            turn_count=turn_count,
            agent_name=agent_name,
            context=context,
            model_output=model_output,
            latency_ms=latency_ms,
            llm_model=llm_model,
            token_count=token_count,
            **kwargs
        )

        logger.info("log_llm_call", "LLM call logged",
                   session_id=session_id, agent=agent_name,
                   latency_ms=latency_ms, tokens=token_count)

    async def get_session_training_logs(
        self,
        session_id: str,
        limit: int = 100
    ):
        """세션의 AI 학습 로그 조회"""
        return await self.repository.get_training_logs(
            session_id=session_id,
            limit=limit
        )

    async def get_agent_performance(
        self,
        agent_name: str,
        limit: int = 100
    ):
        """에이전트별 성능 분석"""
        logs = await self.repository.get_training_logs(
            agent_name=agent_name,
            limit=limit
        )

        if not logs:
            return {
                "agent_name": agent_name,
                "total_calls": 0,
                "avg_latency_ms": 0,
                "error_rate": 0
            }

        total_calls = len(logs)
        total_latency = sum(log.latency_ms or 0 for log in logs)
        error_count = sum(1 for log in logs if log.is_error)

        return {
            "agent_name": agent_name,
            "total_calls": total_calls,
            "avg_latency_ms": total_latency / total_calls if total_calls > 0 else 0,
            "error_rate": error_count / total_calls if total_calls > 0 else 0,
            "error_count": error_count
        }

    # ============================================================
    # 종합 분석
    # ============================================================

    async def get_session_analytics(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        세션 전체 분석 (로그, 에러, 성능, AI 호출)

        Returns:
            {
                "session_id": str,
                "total_logs": int,
                "total_errors": int,
                "total_llm_calls": int,
                "avg_llm_latency_ms": float
            }
        """
        # Get logs
        logs = await self.repository.get_logs(session_id=session_id, limit=1000)

        # Get errors
        errors = await self.repository.get_error_logs(session_id=session_id, limit=1000)

        # Get training logs
        training_logs = await self.repository.get_training_logs(
            session_id=session_id,
            limit=1000
        )

        # Calculate avg latency
        total_latency = sum(log.latency_ms or 0 for log in training_logs)
        avg_latency = (
            total_latency / len(training_logs)
            if training_logs else 0
        )

        return {
            "session_id": session_id,
            "total_logs": len(logs),
            "total_errors": len(errors),
            "total_llm_calls": len(training_logs),
            "avg_llm_latency_ms": avg_latency,
            "error_rate": len(errors) / len(training_logs) if training_logs else 0
        }
