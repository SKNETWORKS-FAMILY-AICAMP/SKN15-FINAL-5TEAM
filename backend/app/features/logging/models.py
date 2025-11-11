"""
Logging Feature - SQLAlchemy Models
로그, 에러, 성능 메트릭, AI 학습 로그 테이블
"""
from sqlalchemy import Column, String, BigInteger, Integer, Float, Text, DateTime, JSON, Boolean, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db.base import Base


class Log(Base):
    """
    일반 로그
    기존 logdb.logs 테이블을 public 스키마로 이동
    """
    __tablename__ = "logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    log_level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    stage_name = Column(String(100), nullable=True)
    agent_name = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    context_data = Column(JSON, nullable=True)
    duration_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Log(id={self.id}, level={self.log_level}, message={self.message[:50]})>"


class ErrorLog(Base):
    """
    에러 로그
    기존 logdb.error_logs 테이블을 public 스키마로 이동
    """
    __tablename__ = "error_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ErrorLog(id={self.id}, type={self.error_type})>"


class PerformanceMetric(Base):
    """
    성능 메트릭
    기존 logdb.performance_metrics 테이블을 public 스키마로 이동
    """
    __tablename__ = "performance_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PerformanceMetric(name={self.metric_name}, value={self.metric_value})>"


class TrainingLog(Base):
    """
    AI 학습 로그
    LLM 호출 및 응답 기록, AI 학습 데이터 수집
    """
    __tablename__ = "training_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    turn_count = Column(Integer, nullable=False)

    # 시나리오 정보
    scenario_id = Column(String(50), nullable=True)
    current_stage = Column(String(100), nullable=True)
    agent_name = Column(String(50), nullable=False)

    # 입력/출력
    user_input = Column(Text, nullable=True)
    context = Column(JSON, nullable=False)
    model_output = Column(JSON, nullable=False)

    # 성능 메트릭
    latency_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    llm_model = Column(String(100), nullable=True)

    # 결과 분석
    outcome = Column(String(20), nullable=True)  # success, failure, timeout, etc
    outcome_reason = Column(Text, nullable=True)
    feedback_score = Column(Float, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    labeled_at = Column(DateTime(timezone=True), nullable=True)

    # 에러 처리
    is_error = Column(Boolean, default=False, server_default='false')
    error_message = Column(Text, nullable=True)

    # Vector embedding (pgvector extension)
    # Note: vector(1536) type requires pgvector extension
    # Using String as placeholder - convert to proper vector type if pgvector is installed
    embedding = Column(String, nullable=True)  # Originally: vector(1536)

    # 엔티티 참조
    mentioned_entity_ids = Column(ARRAY(Integer), nullable=True, server_default='{}')

    __table_args__ = (
        CheckConstraint("feedback_score >= 0.0 AND feedback_score <= 1.0",
                        name="training_logs_feedback_score_check"),
    )

    def __repr__(self):
        return f"<TrainingLog(id={self.id}, session={self.session_id}, turn={self.turn_count})>"
