"""
Logging Feature - SQLAlchemy Models
로그, 에러, 성능 메트릭 테이블
"""
from sqlalchemy import Column, String, BigInteger, Integer, Float, Text, DateTime, JSON
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
