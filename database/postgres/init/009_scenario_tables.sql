-- Scenario Tables Migration (content schema)
-- Created: 2025-11-12
-- Purpose: Add scenario likes, comments tables to content schema

-- ============================================================================
-- Scenario Likes (content schema)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.scenario_likes (
    like_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT scenario_likes_unique UNIQUE (scenario_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_scenario_likes_scenario ON content.scenario_likes(scenario_id, created_at);
CREATE INDEX IF NOT EXISTS idx_scenario_likes_user ON content.scenario_likes(user_id, created_at);

COMMENT ON TABLE content.scenario_likes IS '시나리오 좋아요';

-- ============================================================================
-- Scenario Comments (content schema)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.scenario_comments (
    id BIGSERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    parent_comment_id BIGINT REFERENCES content.scenario_comments(id) ON DELETE CASCADE,
    like_count INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT scenario_comments_content_check CHECK (char_length(content) >= 1 AND char_length(content) <= 1000),
    CONSTRAINT scenario_comments_like_count_check CHECK (like_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_scenario_comments_scenario ON content.scenario_comments(scenario_id, created_at);
CREATE INDEX IF NOT EXISTS idx_scenario_comments_scenario_likes ON content.scenario_comments(scenario_id, like_count);
CREATE INDEX IF NOT EXISTS idx_scenario_comments_parent ON content.scenario_comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_scenario_comments_user ON content.scenario_comments(user_id);

COMMENT ON TABLE content.scenario_comments IS '시나리오 댓글';

-- ============================================================================
-- Comment Likes (content schema)
-- ============================================================================

CREATE TABLE IF NOT EXISTS content.comment_likes (
    comment_id BIGINT NOT NULL REFERENCES content.scenario_comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (comment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_comment_likes_comment ON content.comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_user ON content.comment_likes(user_id);

COMMENT ON TABLE content.comment_likes IS '댓글 좋아요';
