"""
Logging Feature - Enhanced Repository
로그, 에러, 성능 메트릭, AI 학습 로그 DB 접근 레이어
Layer 4: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import traceback

from app.core.logging import get_repository_logger
from .models import Log, ErrorLog, PerformanceMetric, TrainingLog

logger = get_repository_logger("Logging")


class LoggingRepository:
    """
    로깅 Repository

    책임: 시스템 로그, 에러 로그, 성능 메트릭, AI 학습 로그 DB 접근
    """

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    # ============================================================
    # 시스템 로그 (Log)
    # ============================================================

    async def create_log(
        self,
        log_level: str,
        message: str,
        session_id: Optional[str] = None,
        stage_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> Log:
        """
        시스템 로그 생성

        Args:
            log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
            message: 로그 메시지
            session_id: 세션 ID (선택적)
            stage_name: 스테이지 이름 (선택적)
            agent_name: 에이전트 이름 (선택적)
            context_data: 추가 컨텍스트 데이터
            duration_ms: 실행 시간 (ms)

        Returns:
            생성된 Log 객체
        """
        try:
            log = Log(
                session_id=uuid.UUID(session_id) if session_id else None,
                log_level=log_level,
                stage_name=stage_name,
                agent_name=agent_name,
                message=message,
                context_data=context_data,
                duration_ms=duration_ms
            )

            self.db.add(log)
            await self.db.commit()
            await self.db.refresh(log)

            logger.debug("create_log", "System log created",
                        id=log.id, level=log_level)

            return log

        except Exception as e:
            await self.db.rollback()
            logger.error("create_log", f"Failed to create log: {e}")
            raise

    async def get_logs(
        self,
        session_id: Optional[str] = None,
        log_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Log]:
        """
        로그 조회

        Args:
            session_id: 세션 ID 필터
            log_level: 로그 레벨 필터
            limit: 조회 개수
            offset: 오프셋
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            Log 리스트
        """
        try:
            conditions = []

            if session_id:
                conditions.append(Log.session_id == uuid.UUID(session_id))
            if log_level:
                conditions.append(Log.log_level == log_level)
            if start_time:
                conditions.append(Log.timestamp >= start_time)
            if end_time:
                conditions.append(Log.timestamp <= end_time)

            stmt = (
                select(Log)
                .where(and_(*conditions)) if conditions else select(Log)
            )
            stmt = stmt.order_by(desc(Log.timestamp)).limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            logs = result.scalars().all()

            logger.debug("get_logs", f"Retrieved {len(logs)} logs",
                        filters={"session_id": session_id, "level": log_level})

            return list(logs)

        except Exception as e:
            logger.error("get_logs", f"Failed to get logs: {e}")
            raise

    # ============================================================
    # 에러 로그 (ErrorLog)
    # ============================================================

    async def create_error_log(
        self,
        error_type: str,
        error_message: str,
        session_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> ErrorLog:
        """
        에러 로그 생성

        Args:
            error_type: 에러 타입 (예: ValueError, HTTPException)
            error_message: 에러 메시지
            session_id: 세션 ID (선택적)
            stack_trace: 스택 트레이스
            context_data: 추가 컨텍스트 데이터

        Returns:
            생성된 ErrorLog 객체
        """
        try:
            error_log = ErrorLog(
                session_id=uuid.UUID(session_id) if session_id else None,
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                context_data=context_data
            )

            self.db.add(error_log)
            await self.db.commit()
            await self.db.refresh(error_log)

            logger.debug("create_error_log", "Error log created",
                        id=error_log.id, type=error_type)

            return error_log

        except Exception as e:
            await self.db.rollback()
            logger.error("create_error_log", f"Failed to create error log: {e}")
            raise

    async def create_error_from_exception(
        self,
        exception: Exception,
        session_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> ErrorLog:
        """
        Exception 객체로부터 에러 로그 생성

        Args:
            exception: Exception 객체
            session_id: 세션 ID
            context_data: 추가 컨텍스트

        Returns:
            생성된 ErrorLog 객체
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()

        return await self.create_error_log(
            error_type=error_type,
            error_message=error_message,
            session_id=session_id,
            stack_trace=stack_trace,
            context_data=context_data
        )

    async def get_error_logs(
        self,
        session_id: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ErrorLog]:
        """
        에러 로그 조회

        Returns:
            ErrorLog 리스트
        """
        try:
            conditions = []

            if session_id:
                conditions.append(ErrorLog.session_id == uuid.UUID(session_id))
            if error_type:
                conditions.append(ErrorLog.error_type == error_type)
            if start_time:
                conditions.append(ErrorLog.timestamp >= start_time)
            if end_time:
                conditions.append(ErrorLog.timestamp <= end_time)

            stmt = (
                select(ErrorLog)
                .where(and_(*conditions)) if conditions else select(ErrorLog)
            )
            stmt = stmt.order_by(desc(ErrorLog.timestamp)).limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            error_logs = result.scalars().all()

            logger.debug("get_error_logs", f"Retrieved {len(error_logs)} error logs")

            return list(error_logs)

        except Exception as e:
            logger.error("get_error_logs", f"Failed to get error logs: {e}")
            raise

    # ============================================================
    # 성능 메트릭 (PerformanceMetric)
    # ============================================================

    async def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> PerformanceMetric:
        """
        성능 메트릭 기록

        Args:
            metric_name: 메트릭 이름 (예: llm_latency, db_query_time)
            metric_value: 메트릭 값
            metric_unit: 단위 (예: ms, seconds, count)
            tags: 태그 (예: {model: gpt-4, endpoint: /chat})

        Returns:
            생성된 PerformanceMetric 객체
        """
        try:
            metric = PerformanceMetric(
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                tags=tags
            )

            self.db.add(metric)
            await self.db.commit()
            await self.db.refresh(metric)

            logger.debug("record_metric", "Performance metric recorded",
                        name=metric_name, value=metric_value, unit=metric_unit)

            return metric

        except Exception as e:
            await self.db.rollback()
            logger.error("record_metric", f"Failed to record metric: {e}")
            raise

    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """
        성능 메트릭 조회
        """
        try:
            conditions = []

            if metric_name:
                conditions.append(PerformanceMetric.metric_name == metric_name)
            if start_time:
                conditions.append(PerformanceMetric.timestamp >= start_time)
            if end_time:
                conditions.append(PerformanceMetric.timestamp <= end_time)

            stmt = (
                select(PerformanceMetric)
                .where(and_(*conditions)) if conditions else select(PerformanceMetric)
            )
            stmt = stmt.order_by(desc(PerformanceMetric.timestamp)).limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            metrics = result.scalars().all()

            logger.debug("get_metrics", f"Retrieved {len(metrics)} metrics",
                        metric_name=metric_name)

            return list(metrics)

        except Exception as e:
            logger.error("get_metrics", f"Failed to get metrics: {e}")
            raise

    async def get_metric_stats(
        self,
        metric_name: str,
        time_window: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """
        메트릭 통계 조회 (평균, 최소, 최대, 개수)

        Args:
            metric_name: 메트릭 이름
            time_window: 시간 윈도우

        Returns:
            통계 딕셔너리
        """
        try:
            start_time = datetime.utcnow() - time_window

            stmt = (
                select(
                    func.avg(PerformanceMetric.metric_value).label("avg"),
                    func.min(PerformanceMetric.metric_value).label("min"),
                    func.max(PerformanceMetric.metric_value).label("max"),
                    func.count(PerformanceMetric.id).label("count")
                )
                .where(and_(
                    PerformanceMetric.metric_name == metric_name,
                    PerformanceMetric.timestamp >= start_time
                ))
            )

            result = await self.db.execute(stmt)
            row = result.first()

            stats = {
                "metric_name": metric_name,
                "time_window_hours": time_window.total_seconds() / 3600,
                "avg": float(row.avg) if row.avg else 0.0,
                "min": float(row.min) if row.min else 0.0,
                "max": float(row.max) if row.max else 0.0,
                "count": int(row.count) if row.count else 0
            }

            logger.debug("get_metric_stats", "Metric stats calculated",
                        metric_name=metric_name, **stats)

            return stats

        except Exception as e:
            logger.error("get_metric_stats", f"Failed to get metric stats: {e}")
            raise

    # ============================================================
    # AI 학습 로그 (TrainingLog)
    # ============================================================

    async def create_training_log(
        self,
        session_id: str,
        turn_count: int,
        agent_name: str,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
        scenario_id: Optional[str] = None,
        current_stage: Optional[str] = None,
        user_input: Optional[str] = None,
        latency_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        llm_model: Optional[str] = None,
        outcome: Optional[str] = None,
        outcome_reason: Optional[str] = None,
        feedback_score: Optional[float] = None,
        is_error: bool = False,
        error_message: Optional[str] = None
    ) -> TrainingLog:
        """
        AI 학습 로그 생성 (LLM 호출 기록)

        Returns:
            생성된 TrainingLog 객체
        """
        try:
            # Handle both UUID and string types
            if isinstance(session_id, uuid.UUID):
                parsed_session_id = session_id
            else:
                parsed_session_id = uuid.UUID(session_id)

            training_log = TrainingLog(
                session_id=parsed_session_id,
                turn_count=turn_count,
                scenario_id=scenario_id,
                current_stage=current_stage,
                agent_name=agent_name,
                user_input=user_input,
                context=context,
                model_output=model_output,
                latency_ms=latency_ms,
                token_count=token_count,
                llm_model=llm_model,
                outcome=outcome,
                outcome_reason=outcome_reason,
                feedback_score=feedback_score,
                is_error=is_error,
                error_message=error_message
            )

            self.db.add(training_log)
            await self.db.commit()
            await self.db.refresh(training_log)

            logger.debug("create_training_log", "Training log created",
                        id=training_log.id, session_id=session_id,
                        turn=turn_count, agent=agent_name)

            return training_log

        except Exception as e:
            await self.db.rollback()
            logger.error("create_training_log", f"Failed to create training log: {e}")
            raise

    async def get_training_logs(
        self,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        outcome: Optional[str] = None,
        is_error: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TrainingLog]:
        """
        AI 학습 로그 조회
        """
        try:
            conditions = []

            if session_id:
                conditions.append(TrainingLog.session_id == uuid.UUID(session_id))
            if agent_name:
                conditions.append(TrainingLog.agent_name == agent_name)
            if outcome:
                conditions.append(TrainingLog.outcome == outcome)
            if is_error is not None:
                conditions.append(TrainingLog.is_error == is_error)

            stmt = (
                select(TrainingLog)
                .where(and_(*conditions)) if conditions else select(TrainingLog)
            )
            stmt = stmt.order_by(desc(TrainingLog.created_at)).limit(limit).offset(offset)

            result = await self.db.execute(stmt)
            logs = result.scalars().all()

            logger.debug("get_training_logs", f"Retrieved {len(logs)} training logs")

            return list(logs)

        except Exception as e:
            logger.error("get_training_logs", f"Failed to get training logs: {e}")
            raise
