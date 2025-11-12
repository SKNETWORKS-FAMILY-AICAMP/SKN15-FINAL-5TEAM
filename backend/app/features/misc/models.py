"""
Misc Models
기타 기능 모델 (tm_work 브랜치에서 마이그레이션)
"""
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.db.base import Base
from datetime import datetime


class SessionSnapshot(Base):
    """
    세션 스냅샷

    각 턴마다 세션 상태 스냅샷 저장
    """
    __tablename__ = "session_snapshots"
    __table_args__ = {"schema": "conversation"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("conversation.sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    state_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<SessionSnapshot(id={self.id}, session={self.session_id}, turn={self.turn_number})>"


class ScenarioStatistics(Base):
    """
    시나리오 통계

    시나리오별 좋아요, 댓글, 조회수, 완료율 등
    """
    __tablename__ = "scenario_statistics"

    scenario_id = Column(String(50), primary_key=True)

    # 카운트
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)

    # 평균
    avg_session_duration = Column(Integer, default=0)  # seconds

    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("total_likes >= 0", name="scenario_statistics_total_likes_check"),
        CheckConstraint("total_comments >= 0", name="scenario_statistics_total_comments_check"),
        CheckConstraint("total_views >= 0", name="scenario_statistics_total_views_check"),
        CheckConstraint("total_completions >= 0", name="scenario_statistics_total_completions_check"),
        CheckConstraint("total_sessions >= 0", name="scenario_statistics_total_sessions_check"),
        CheckConstraint("avg_session_duration >= 0", name="scenario_statistics_avg_session_duration_check"),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ScenarioStatistics(scenario={self.scenario_id}, views={self.total_views}, likes={self.total_likes})>"


class UserFeedback(Base):
    """
    사용자 피드백

    사용자의 피드백 및 개선 제안
    """
    __tablename__ = "user_feedback"
    __table_args__ = {"schema": "ml"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    training_log_id = Column(BigInteger)
    feedback_type = Column(String(50), nullable=False)  # bug_report, feature_request, general, rating
    feedback_text = Column(Text)
    user_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, type={self.feedback_type}, user={self.user_id})>"
