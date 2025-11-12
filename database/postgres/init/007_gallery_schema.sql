-- Gallery Schema Migration
-- Created: 2025-11-12
-- Purpose: Create gallery schema and related tables

-- ============================================================================
-- Gallery Schema
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS gallery;

-- ============================================================================
-- Gallery Tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS gallery.gallery_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    scenario_id VARCHAR(100) NOT NULL,
    session_id UUID REFERENCES conversation.sessions(session_id) ON DELETE SET NULL,

    -- Image Info
    stage_tag VARCHAR(100) NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    image_type VARCHAR(20) NOT NULL DEFAULT 'generated',

    -- Generation Metadata
    generation_prompt VARCHAR(2000),
    generation_model VARCHAR(100),
    extra_metadata JSONB,

    -- Status
    is_unlocked BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    unlocked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gallery_user_id ON gallery.gallery_images(user_id);
CREATE INDEX IF NOT EXISTS idx_gallery_scenario_id ON gallery.gallery_images(scenario_id);
CREATE INDEX IF NOT EXISTS idx_gallery_session_id ON gallery.gallery_images(session_id);
CREATE INDEX IF NOT EXISTS idx_gallery_user_scenario ON gallery.gallery_images(user_id, scenario_id);

COMMENT ON TABLE gallery.gallery_images IS '사용자 갤러리 이미지 (AI 생성 또는 언락 이미지)';

-- ============================================================================
-- Gallery Image Likes
-- ============================================================================

CREATE TABLE IF NOT EXISTS gallery.gallery_image_likes (
    like_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES gallery.gallery_images(image_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT gallery_image_likes_unique UNIQUE (image_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_gallery_image_likes_image ON gallery.gallery_image_likes(image_id, created_at);
CREATE INDEX IF NOT EXISTS idx_gallery_image_likes_user ON gallery.gallery_image_likes(user_id, created_at);

COMMENT ON TABLE gallery.gallery_image_likes IS '갤러리 이미지 좋아요';

-- ============================================================================
-- Gallery Image Views
-- ============================================================================

CREATE TABLE IF NOT EXISTS gallery.gallery_image_views (
    view_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID REFERENCES gallery.gallery_images(image_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(user_id) ON DELETE SET NULL,
    ip_address INET,
    viewed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_gallery_image_views_image ON gallery.gallery_image_views(image_id, viewed_at);
CREATE INDEX IF NOT EXISTS idx_gallery_image_views_user ON gallery.gallery_image_views(user_id, viewed_at);

COMMENT ON TABLE gallery.gallery_image_views IS '갤러리 이미지 조회 기록';
