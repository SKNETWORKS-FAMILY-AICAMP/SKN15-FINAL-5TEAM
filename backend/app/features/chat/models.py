"""
Chat Feature - SQLAlchemy Models
DB 테이블 정의
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, BigInteger, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.core.db.base import Base, TimestampMixin


class ImageMapping(Base):
    """
    이미지 매핑 테이블 (content.image_mappings)

    스테이지별 이미지 매핑 정보
    metadata JSONB 필드에 priority, stage_id, turn_range 등 저장 가능
    """
    __tablename__ = "image_mappings"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), nullable=True)
    mapping_category = Column(String(50), nullable=False)  # 'character', 'bg', 'cutscene', 'stage'
    image_key = Column(String(255), nullable=False)        # 'rengoku_normal', 'train_bg_1', 'stage_intro'
    image_url = Column(Text, nullable=False)                # S3 URL or local path
    metadata = Column(JSONB, default={})                    # Additional data: priority, stage_id, turn_range, etc.

    def __repr__(self):
        return f"<ImageMapping(id={self.id}, scenario={self.scenario_id}, key={self.image_key})>"


class DialogueTurn(Base, TimestampMixin):
    """
    대화 턴 기록

    각 대사를 개별 row로 저장
    """
    __tablename__ = "dialogue_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    scenario_id = Column(String(255), nullable=False)
    turn_count = Column(Integer, nullable=False)

    # 대사 내용
    speaker = Column(String(100), nullable=False)
    text = Column(Text, nullable=False)  # ✅ text로 통일 (content 아님!)
    emotion = Column(String(50), default="neutral")

    # 메타데이터
    stage_tag = Column(String(100))
    affinity_delta = Column(Float, default=0.0)

    # 인덱스
    __table_args__ = (
        Index('idx_session_user', 'session_id', 'user_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<DialogueTurn(id={self.id}, speaker={self.speaker}, session={self.session_id})>"


class UserCharacterAffinity(Base):
    """
    사용자별 캐릭터 친밀도 (글로벌)
    """
    __tablename__ = "user_character_affinity"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    character_name = Column(String(255), nullable=False)
    total_affinity_score = Column(Integer, nullable=False, default=0)
    affinity_level = Column(Integer, nullable=False, default=1)
    total_interactions = Column(Integer, nullable=False, default=0)
    last_interaction_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'character_name'),
        CheckConstraint('total_affinity_score >= 0 AND total_affinity_score <= 1000'),
        CheckConstraint('affinity_level >= 1 AND affinity_level <= 10'),
        Index('idx_user_character_affinity_character', 'character_name'),
        Index('idx_user_character_affinity_score', 'user_id', 'total_affinity_score'),
    )

    def __repr__(self):
        return f"<UserCharacterAffinity(user={self.user_id}, character={self.character_name}, level={self.affinity_level})>"


class AffinityRecord(Base):
    """
    세션별 친밀도 변화 기록
    """
    __tablename__ = "affinity_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    character_name = Column(String(255), nullable=False)
    affinity_score = Column(Integer, nullable=False)
    change_amount = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_affinity_session', 'session_id', 'character_name'),
        Index('idx_affinity_character', 'character_name'),
        Index('idx_affinity_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AffinityRecord(session={self.session_id}, character={self.character_name}, score={self.affinity_score})>"


class Entity(Base):
    """
    엔티티 (캐릭터, 장소, 이벤트, 아이템, 스킬)
    """
    __tablename__ = "entities"

    entity_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_name = Column(String(255), nullable=False)
    canonical_name = Column(String(255))
    description = Column(Text)
    properties = Column(JSONB, default={})
    embedding = Column(Vector(1536))  # OpenAI text-embedding-3-small
    importance_score = Column(Float, default=0.5)
    community_id = Column(Integer)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('entity_type', 'canonical_name'),
        CheckConstraint("entity_type IN ('character', 'location', 'event', 'item', 'skill')", name='valid_entity_type'),
        CheckConstraint('importance_score >= 0.0 AND importance_score <= 1.0', name='valid_importance'),
        Index('idx_entities_type', 'entity_type'),
        Index('idx_entities_canonical_name', 'canonical_name'),
        Index('idx_entities_importance', 'importance_score'),
        Index('idx_entities_mention_count', 'mention_count'),
        Index('idx_entities_community', 'community_id'),
    )

    def __repr__(self):
        return f"<Entity(id={self.entity_id}, type={self.entity_type}, name={self.entity_name})>"


class EntityRelationship(Base):
    """
    엔티티 간 관계
    """
    __tablename__ = "entity_relationships"

    relationship_id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity_id = Column(Integer, ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)
    strength = Column(Float, default=0.5)
    context = Column(Text)
    properties = Column(JSONB, default={})
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    mention_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('source_entity_id', 'target_entity_id', 'relationship_type'),
        CheckConstraint('strength >= 0.0 AND strength <= 1.0', name='valid_strength'),
        Index('idx_relationships_source', 'source_entity_id'),
        Index('idx_relationships_target', 'target_entity_id'),
        Index('idx_relationships_type', 'relationship_type'),
        Index('idx_relationships_strength', 'strength'),
    )

    def __repr__(self):
        return f"<EntityRelationship(source={self.source_entity_id}, target={self.target_entity_id}, type={self.relationship_type})>"


class EntityMention(Base):
    """
    대화 턴별 엔티티 언급 기록
    """
    __tablename__ = "entity_mentions"

    mention_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, ForeignKey("entities.entity_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    mention_text = Column(Text)
    context_window = Column(Text)
    sentiment_score = Column(Float)
    mentioned_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('sentiment_score >= -1.0 AND sentiment_score <= 1.0', name='valid_sentiment'),
        Index('idx_mentions_entity', 'entity_id', 'mentioned_at'),
        Index('idx_mentions_session', 'session_id', 'turn_number'),
    )

    def __repr__(self):
        return f"<EntityMention(entity={self.entity_id}, session={self.session_id}, turn={self.turn_number})>"


class UserMemory(Base):
    """
    사용자별 장기 기억
    """
    __tablename__ = "user_memories"

    memory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    scenario_id = Column(String(50))
    memory_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    importance_score = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("memory_type IN ('episodic', 'semantic', 'procedural')", name='valid_memory_type'),
        CheckConstraint('importance_score >= 0.0 AND importance_score <= 1.0', name='valid_memory_importance'),
        Index('idx_memories_user', 'user_id', 'created_at'),
        Index('idx_memories_type', 'memory_type'),
        Index('idx_memories_importance', 'importance_score'),
        Index('idx_memories_scenario', 'scenario_id'),
    )

    def __repr__(self):
        return f"<UserMemory(id={self.memory_id}, user={self.user_id}, type={self.memory_type})>"
