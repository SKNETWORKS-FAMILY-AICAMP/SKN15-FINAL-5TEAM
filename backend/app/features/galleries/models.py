"""
Galleries Feature - Models
이미지 갤러리 데이터베이스 모델
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.db.base import Base


class GalleryImage(Base):
    """
    사용자 갤러리 이미지
    AI 생성 이미지 또는 언락 이미지 저장
    """
    __tablename__ = "gallery_images"

    # Primary Key
    image_id = Column(String(36), primary_key=True)  # UUID

    # Foreign Keys
    user_id = Column(String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    scenario_id = Column(String(100), nullable=False)
    session_id = Column(String(36), nullable=True)  # 생성 시 세션 ID

    # Image Info
    stage_tag = Column(String(100), nullable=False)  # 스테이지 태그
    image_url = Column(String(500), nullable=False)  # 이미지 URL (S3, CDN 등)
    image_type = Column(String(20), nullable=False, default="generated")  # generated, unlocked, default

    # Generation Metadata
    generation_prompt = Column(String(2000), nullable=True)  # 생성 프롬프트
    generation_model = Column(String(100), nullable=True)  # 생성 모델 (dall-e-3 등)
    metadata = Column(JSON, nullable=True)  # 추가 메타데이터 (크기, 스타일 등)

    # Status
    is_unlocked = Column(Boolean, default=False)  # 언락 여부
    is_favorite = Column(Boolean, default=False)  # 즐겨찾기 여부

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    unlocked_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_gallery_user_id", "user_id"),
        Index("idx_gallery_scenario_id", "scenario_id"),
        Index("idx_gallery_session_id", "session_id"),
        Index("idx_gallery_user_scenario", "user_id", "scenario_id"),
    )

    def __repr__(self):
        return f"<GalleryImage(image_id={self.image_id}, user_id={self.user_id}, stage_tag={self.stage_tag})>"
