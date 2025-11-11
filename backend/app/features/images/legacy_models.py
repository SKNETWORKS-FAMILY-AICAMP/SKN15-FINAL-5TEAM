"""
Legacy Image Models
이미지 관련 레거시 모델 (tm_work 브랜치에서 마이그레이션)
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from app.core.db.base import Base
from datetime import datetime
import uuid


class ImageAsset(Base):
    """
    이미지 에셋

    게임 내 사용되는 모든 이미지 에셋 관리
    """
    __tablename__ = "image_assets"

    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_path = Column(String(500), nullable=False)
    image_name = Column(String(255), nullable=False)
    image_type = Column(String(50), default="cutscene")  # cutscene, character, background, ui, icon
    scenario_id = Column(String(50))
    index_number = Column(Integer)
    description = Column(Text)
    tags = Column(ARRAY(Text))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ImageAsset(id={self.image_id}, name={self.image_name})>"


class ScenarioStageImage(Base):
    """
    시나리오 스테이지별 이미지 매핑

    각 스테이지에 대한 기본 이미지 설정
    """
    __tablename__ = "scenario_stage_images"

    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(50), nullable=False)
    stage_id = Column(String(100), nullable=False)
    default_image_id = Column(UUID(as_uuid=True))
    stage_order = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScenarioStageImage(scenario={self.scenario_id}, stage={self.stage_id})>"


class ScenarioDefaultImage(Base):
    """
    시나리오 기본 이미지

    각 시나리오의 기본 대표 이미지
    """
    __tablename__ = "scenario_default_images"

    scenario_id = Column(String(50), primary_key=True)
    default_image_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScenarioDefaultImage(scenario={self.scenario_id})>"


class ImageMappingRule(Base):
    """
    이미지 매핑 규칙

    조건에 따른 이미지 동적 매핑 규칙
    """
    __tablename__ = "image_mapping_rules"

    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mapping_id = Column(UUID(as_uuid=True), nullable=False)
    image_id = Column(UUID(as_uuid=True), nullable=False)

    # 우선순위 및 조건
    priority = Column(Integer, default=50)
    turn_min = Column(Integer, default=0)
    turn_max = Column(Integer, default=999)
    dialogue_count_min = Column(Integer, default=0)
    dialogue_count_max = Column(Integer, default=999)

    # 플래그 기반 조건
    required_flags = Column(ARRAY(Text))
    excluded_flags = Column(ARRAY(Text))

    description = Column(Text)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ImageMappingRule(id={self.rule_id}, priority={self.priority})>"
