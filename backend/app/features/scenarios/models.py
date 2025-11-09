"""
Scenarios Feature - SQLAlchemy Models
시나리오 댓글, 좋아요 등 DB 테이블 정의
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Boolean, CheckConstraint, UniqueConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.db.base import Base


class ScenarioComment(Base):
    """
    시나리오 댓글
    """
    __tablename__ = "scenario_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(BigInteger, ForeignKey("scenario_comments.id", ondelete="CASCADE"))
    like_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('char_length(content) >= 1 AND char_length(content) <= 1000'),
        CheckConstraint('like_count >= 0'),
        Index('idx_scenario_comments_scenario', 'scenario_id', 'created_at'),
        Index('idx_scenario_comments_scenario_likes', 'scenario_id', 'like_count'),
        Index('idx_scenario_comments_parent', 'parent_comment_id'),
    )

    def __repr__(self):
        return f"<ScenarioComment(id={self.id}, scenario={self.scenario_id}, user={self.user_id})>"


class ScenarioLike(Base):
    """
    시나리오 좋아요
    """
    __tablename__ = "scenario_likes"

    like_id = Column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    scenario_id = Column(String(50), ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('scenario_id', 'user_id', name='scenario_likes_unique'),
        Index('idx_scenario_likes_scenario', 'scenario_id', 'created_at'),
        Index('idx_scenario_likes_user', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<ScenarioLike(scenario={self.scenario_id}, user={self.user_id})>"


class CommentLike(Base):
    """
    댓글 좋아요
    """
    __tablename__ = "comment_likes"

    comment_id = Column(BigInteger, ForeignKey("scenario_comments.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_comment_likes_comment', 'comment_id'),
        Index('idx_comment_likes_user', 'user_id'),
    )

    def __repr__(self):
        return f"<CommentLike(comment={self.comment_id}, user={self.user_id})>"
