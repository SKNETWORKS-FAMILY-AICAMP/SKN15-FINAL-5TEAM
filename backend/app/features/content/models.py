"""
Content Feature - SQLAlchemy Models
월드, 캐릭터, 이미지 매핑 등 DB 테이블 정의
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.db.base import Base


class World(Base):
    """
    게임 월드/세계관 정보
    """
    __tablename__ = "worlds"
    __table_args__ = {"schema": "content"}

    world_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)  # DB 컬럼명
    description = Column(Text)
    era = Column(String(100))  # DB 컬럼
    lore = Column(JSONB, default={})  # DB 컬럼

    # 월드 컨텍스트 (LLM에 전달될 세계관 정보)
    world_context = Column(Text)

    # 규칙 (combat, social, world 등)
    rules = Column(JSONB, default={})

    # 말투/어조 가이드
    tone_guidelines = Column(JSONB, default={})

    # 고유명사/용어
    terminology = Column(JSONB, default={})

    # 메타데이터
    metadata = Column(JSONB, default={})

    # 활성화 여부
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<World(id={self.world_id}, name={self.name})>"


class Character(Base):
    """
    캐릭터 정보
    """
    __tablename__ = "characters"
    __table_args__ = {"schema": "content"}

    character_id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    personality = Column(String(500))

    # 호흡법/전투 스타일
    breathing_style = Column(String(100))
    rank = Column(String(50))

    # 기본 호감도
    default_affinity = Column(Integer, default=500)

    # 호감도 표시 여부
    affinity_visible = Column(Boolean, default=True)
    affinity_applicable = Column(Boolean, default=True)

    # Intent 규칙 (가중치, 민감도, 패턴)
    intent_rules = Column(JSONB, default={})

    # 외형
    appearance = Column(JSONB, default={})

    # 핵심 가치관
    core_values = Column(ARRAY(Text))

    # 감정 트리거
    emotional_triggers = Column(JSONB, default={})

    # 행동 패턴
    behavior_patterns = Column(JSONB, default={})

    # 대표 대사
    signature_quotes = Column(ARRAY(Text))

    # 별칭
    aliases = Column(ARRAY(Text))

    # 말투 (호감도별)
    tone = Column(JSONB, default={})

    # 시나리오별 특수 설정
    scenario_specific = Column(JSONB, default={})

    # 활성화 여부
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_characters_name', 'name'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<Character(id={self.character_id}, name={self.name})>"


class ImageMapping(Base):
    """
    이미지 매핑 정보 (시나리오별)
    """
    __tablename__ = "image_mappings"
    __table_args__ = {"schema": "content"}

    mapping_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), ForeignKey("content.scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)

    # 우선순위 (높을수록 먼저 매칭)
    priority = Column(Integer, default=50)

    # 매칭 조건
    stage = Column(String(50))  # 스테이지 이름 (또는 배열)
    stage_list = Column(ARRAY(String))  # 여러 스테이지에 적용
    turn_min = Column(Integer)
    turn_max = Column(Integer)
    dialogue_count_min = Column(Integer)
    dialogue_count_max = Column(Integer)

    # 플래그 조건
    flags = Column(ARRAY(String))  # 특정 플래그가 있을 때만 매칭

    # 이미지 정보
    image = Column(String(500), nullable=False)
    description = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_image_mappings_scenario', 'scenario_id', 'priority'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ImageMapping(id={self.mapping_id}, scenario={self.scenario_id}, image={self.image})>"


class ImageMetadata(Base):
    """
    이미지 메타데이터 (LLM 이미지 선택용)
    """
    __tablename__ = "image_metadata"
    __table_args__ = {"schema": "content"}

    metadata_id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), ForeignKey("content.scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True)

    # 이미지 정보
    image_index = Column(String(10))  # "1", "2", etc.
    image_id = Column(String(100))
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # 태그 및 키워드
    tags = Column(ARRAY(String))
    keywords = Column(ARRAY(String))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_image_metadata_scenario', 'scenario_id', 'image_index'),
        {"schema": "content"}
    )

    def __repr__(self):
        return f"<ImageMetadata(id={self.metadata_id}, scenario={self.scenario_id}, name={self.name})>"
