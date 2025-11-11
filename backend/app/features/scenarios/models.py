"""
Scenarios Feature - SQLAlchemy Models
시나리오 댓글, 좋아요 등 DB 테이블 정의
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Boolean, CheckConstraint, UniqueConstraint, Index, ForeignKey, text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from datetime import datetime
import uuid
from app.core.db.base import Base


class Scenarios(Base):
    """
    시나리오 정보 (content.scenarios 테이블)
    """
    __tablename__ = "scenarios"
    __table_args__ = {"schema": "content"}

    scenario_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    image_url = Column(String(500))
    thumbnail_url = Column(String(500))
    tags = Column(ARRAY(Text))
    card_size = Column(String(20), default="normal")
    route_path = Column(String(200))
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    world_id = Column(String(50))

    def __repr__(self):
        return f"<Scenarios(id={self.scenario_id}, title={self.title})>"


class ScenarioComment(Base):
    """
    시나리오 댓글
    """
    __tablename__ = "scenario_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), nullable=False, index=True)  # Scenarios are in JSON files, not DB
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

    like_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(50), nullable=False, index=True)  # Scenarios are in JSON files, not DB
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


class ScenarioView(Base):
    """
    시나리오 조회 기록
    """
    __tablename__ = "scenario_views"

    view_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(50), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    viewed_at = Column(DateTime(timezone=True), nullable=True, server_default=text('now()'))

    def __repr__(self):
        return f"<ScenarioView(scenario={self.scenario_id}, user={self.user_id})>"


class ScenarioStage(Base):
    """
    시나리오 스테이지

    5가지 스테이지 타입 지원:
    - scene: 장면 재생 (micro_beat 지원)
    - mission: 미션 스테이지 (목표 기반)
    - router: 조건 기반 분기
    - free_intent: 자유 의도 파싱
    - open_narrative: 개방형 대화
    """
    __tablename__ = "scenario_stages"
    __table_args__ = {"schema": "content"}

    stage_id = Column(String(100), primary_key=True)
    scenario_id = Column(String(50), ForeignKey("content.scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)
    stage_order = Column(Integer, nullable=False)
    stage_type = Column(String(50), nullable=False)  # scene, mission, router, free_intent, open_narrative

    # Stage 설정 (JSON)
    config = Column(JSONB, nullable=False, default={})

    # Display
    title = Column(String(200))
    description = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "stage_type IN ('scene', 'mission', 'router', 'free_intent', 'open_narrative')",
            name='scenario_stages_type_check'
        ),
        Index('idx_scenario_stages_scenario', 'scenario_id', 'stage_order'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ScenarioStage(id={self.stage_id}, type={self.stage_type})>"


class ScenarioMicroBeat(Base):
    """
    시나리오 마이크로 비트 (scene 타입 전용)

    scene 스테이지 내에서 사용되는 세부 대화/이벤트 단위
    """
    __tablename__ = "scenario_micro_beats"
    __table_args__ = {"schema": "content"}

    beat_id = Column(String(100), primary_key=True)
    stage_id = Column(String(100), ForeignKey("content.scenario_stages.stage_id", ondelete="CASCADE"), nullable=False, index=True)
    beat_order = Column(Integer, nullable=False)

    # Beat 설정
    goal = Column(Text, nullable=False)  # 이 비트의 목표/내용
    speaker_hint = Column(ARRAY(Text))  # 발화자 힌트 (예: ["rengoku", "narr"])
    fx = Column(String(200))  # 효과음/효과 힌트

    # I18N 키 (선택적)
    i18n_key = Column(String(100))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_scenario_micro_beats_stage', 'stage_id', 'beat_order'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ScenarioMicroBeat(id={self.beat_id}, stage={self.stage_id})>"


class ScenarioMission(Base):
    """
    시나리오 미션 (mission 타입 전용)

    목표 기반 미션 스테이지 설정
    """
    __tablename__ = "scenario_missions"
    __table_args__ = {"schema": "content"}

    mission_id = Column(String(100), primary_key=True)
    stage_id = Column(String(100), ForeignKey("content.scenario_stages.stage_id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # 미션 목표
    objective = Column(Text, nullable=False)
    success_condition = Column(JSONB, nullable=False)  # 성공 조건 (JSON)
    failure_condition = Column(JSONB)  # 실패 조건 (JSON, 선택적)

    # 피드백 메시지 (I18N)
    feedback_i18n = Column(JSONB, default={})

    # 보상
    reward_xp = Column(Integer, default=0)
    reward_credits = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScenarioMission(id={self.mission_id}, stage={self.stage_id})>"


class ScenarioRouter(Base):
    """
    시나리오 라우터 (router 타입 전용)

    조건 기반 분기 처리
    """
    __tablename__ = "scenario_routers"
    __table_args__ = {"schema": "content"}

    router_id = Column(String(100), primary_key=True)
    stage_id = Column(String(100), ForeignKey("content.scenario_stages.stage_id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # 라우팅 규칙
    routing_logic = Column(JSONB, nullable=False)  # 조건 → 다음 스테이지 매핑

    # 기본 라우트
    default_next_stage = Column(String(100))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScenarioRouter(id={self.router_id}, stage={self.stage_id})>"


class ScenarioIntentMapping(Base):
    """
    시나리오 인텐트 매핑 (free_intent 타입 전용)

    자유 의도 파싱을 위한 인텐트 → 액션 매핑
    """
    __tablename__ = "scenario_intent_mappings"
    __table_args__ = {"schema": "content"}

    mapping_id = Column(String(100), primary_key=True)
    stage_id = Column(String(100), ForeignKey("content.scenario_stages.stage_id", ondelete="CASCADE"), nullable=False, index=True)

    # 인텐트 정의
    intent_name = Column(String(100), nullable=False)
    intent_keywords = Column(ARRAY(Text))  # 키워드 리스트
    intent_pattern = Column(Text)  # 정규표현식 패턴 (선택적)

    # 액션
    action = Column(JSONB, nullable=False)  # 매칭 시 실행할 액션 (JSON)

    # Priority
    priority = Column(Integer, default=0)  # 우선순위 (높을수록 먼저 매칭)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_scenario_intent_mappings_stage', 'stage_id', 'priority'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ScenarioIntentMapping(id={self.mapping_id}, intent={self.intent_name})>"
