"""
Images Feature - Models
이미지 매핑 데이터 모델
Layer 4: Models (4-Layer Architecture)
"""
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.core.db.base import Base


class ImageMapping(Base):
    """
    이미지 매핑 테이블 (content.image_mappings)

    스테이지별 이미지 매핑 정보
    extra_data JSONB 필드에 priority, stage_id, turn_range 등 저장 가능
    """
    __tablename__ = "image_mappings"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String(50), nullable=True)
    mapping_category = Column(String(50), nullable=False)  # 'character', 'bg', 'cutscene', 'stage'
    image_key = Column(String(255), nullable=False)        # 'rengoku_normal', 'train_bg_1', 'stage_intro'
    image_url = Column(Text, nullable=False)                # S3 URL or local path
    extra_data = Column("metadata", JSONB, default={})      # Maps to DB column 'metadata', Python attribute 'extra_data' (avoid SQLAlchemy reserved word)

    def __repr__(self):
        return f"<ImageMapping(id={self.id}, scenario={self.scenario_id}, key={self.image_key})>"
