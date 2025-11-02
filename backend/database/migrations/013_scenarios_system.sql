-- ============================================================
-- Migration 013: Scenario Management System
-- ============================================================
-- Purpose: Create tables and views for dynamic scenario management
-- Enables HomePage to load scenario cards from database instead of hardcoded array
-- Author: AI Assistant
-- Date: 2025-11-02
-- Dependencies: 001_initial_schema.sql (users table)
-- ============================================================

-- ============================================================
-- Table 1: scenarios (시나리오 메타데이터)
-- ============================================================
-- Stores core scenario information displayed on HomePage cards

CREATE TABLE IF NOT EXISTS statedb.scenarios (
    scenario_id VARCHAR(50) PRIMARY KEY,  -- e.g., 'tanjiro', 'train', 'infinity-castle'
    title VARCHAR(200) NOT NULL,          -- Display title (e.g., '편의점 알바생 탄지로')
    description TEXT,                     -- Scenario description
    image_url VARCHAR(500),               -- Path to main image (e.g., '/images/편의점탄지로.png')
    thumbnail_url VARCHAR(500),           -- Optional smaller thumbnail
    tags TEXT[],                          -- Array of tags (e.g., ['편의점', '일상', '탄지로'])
    card_size VARCHAR(20) DEFAULT 'normal', -- 'large' or 'normal' for UI display
    route_path VARCHAR(200),              -- Frontend route (e.g., '/chat/tanjiro')
    display_order INT DEFAULT 0,          -- Order for sorting on HomePage
    is_active BOOLEAN DEFAULT true,       -- Soft delete flag
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for active scenarios query (most common query)
CREATE INDEX IF NOT EXISTS idx_scenarios_active_order
ON statedb.scenarios(is_active, display_order)
WHERE is_active = true;

-- Index for scenario lookup by ID
CREATE INDEX IF NOT EXISTS idx_scenarios_id
ON statedb.scenarios(scenario_id);

COMMENT ON TABLE statedb.scenarios IS 'Scenario metadata for HomePage scenario cards';
COMMENT ON COLUMN statedb.scenarios.scenario_id IS 'Unique identifier matching scenario file names';
COMMENT ON COLUMN statedb.scenarios.card_size IS 'Display size on HomePage: large (featured) or normal';
COMMENT ON COLUMN statedb.scenarios.display_order IS 'Lower numbers appear first on HomePage';
COMMENT ON COLUMN statedb.scenarios.is_active IS 'False = hidden from HomePage (soft delete)';


-- ============================================================
-- Table 2: scenario_statistics (시나리오 통계)
-- ============================================================
-- Aggregated statistics for each scenario (likes, views, completions)

CREATE TABLE IF NOT EXISTS statedb.scenario_statistics (
    scenario_id VARCHAR(50) PRIMARY KEY REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    total_likes INT DEFAULT 0 CHECK (total_likes >= 0),
    total_comments INT DEFAULT 0 CHECK (total_comments >= 0),
    total_views INT DEFAULT 0 CHECK (total_views >= 0),
    total_completions INT DEFAULT 0 CHECK (total_completions >= 0),
    total_sessions INT DEFAULT 0 CHECK (total_sessions >= 0),
    avg_session_duration INT DEFAULT 0 CHECK (avg_session_duration >= 0),  -- minutes
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE statedb.scenario_statistics IS 'Aggregated statistics for each scenario';
COMMENT ON COLUMN statedb.scenario_statistics.total_likes IS 'Count of users who liked this scenario';
COMMENT ON COLUMN statedb.scenario_statistics.total_views IS 'Total number of times scenario was viewed';
COMMENT ON COLUMN statedb.scenario_statistics.total_completions IS 'Number of users who completed this scenario';
COMMENT ON COLUMN statedb.scenario_statistics.avg_session_duration IS 'Average play time in minutes';


-- ============================================================
-- Table 3: user_scenario_progress (사용자별 시나리오 진행도)
-- ============================================================
-- Tracks each user's progress and interactions with scenarios

CREATE TABLE IF NOT EXISTS statedb.user_scenario_progress (
    user_id UUID REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    scenario_id VARCHAR(50) REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    has_started BOOLEAN DEFAULT false,
    has_completed BOOLEAN DEFAULT false,
    completion_percentage INT DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    last_session_id VARCHAR(100),         -- Reference to most recent session
    last_played_at TIMESTAMP,
    total_messages INT DEFAULT 0 CHECK (total_messages >= 0),
    total_play_time INT DEFAULT 0 CHECK (total_play_time >= 0),  -- minutes
    is_liked BOOLEAN DEFAULT false,       -- User's like status for this scenario
    liked_at TIMESTAMP,                   -- When user liked (NULL if not liked)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, scenario_id)
);

-- Index for user's scenario list query
CREATE INDEX IF NOT EXISTS idx_user_scenario_progress_user
ON statedb.user_scenario_progress(user_id);

-- Index for liked scenarios
CREATE INDEX IF NOT EXISTS idx_user_scenario_progress_liked
ON statedb.user_scenario_progress(user_id, is_liked)
WHERE is_liked = true;

COMMENT ON TABLE statedb.user_scenario_progress IS 'Per-user progress and interactions with each scenario';
COMMENT ON COLUMN statedb.user_scenario_progress.has_started IS 'True if user has played this scenario at least once';
COMMENT ON COLUMN statedb.user_scenario_progress.has_completed IS 'True if user finished the scenario';
COMMENT ON COLUMN statedb.user_scenario_progress.completion_percentage IS 'Progress 0-100% (based on stages completed)';
COMMENT ON COLUMN statedb.user_scenario_progress.is_liked IS 'User''s like status for this scenario';


-- ============================================================
-- Table 4: scenario_views (시나리오 조회 기록)
-- ============================================================
-- Log table for tracking individual scenario views (for analytics)

CREATE TABLE IF NOT EXISTS statedb.scenario_views (
    view_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(50) REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    user_id UUID REFERENCES statedb.users(user_id) ON DELETE SET NULL,  -- NULL for anonymous
    ip_address INET,                      -- For anonymous tracking
    user_agent TEXT,                      -- Browser info
    viewed_at TIMESTAMP DEFAULT NOW()
);

-- Index for scenario view counts
CREATE INDEX IF NOT EXISTS idx_scenario_views_scenario
ON statedb.scenario_views(scenario_id, viewed_at DESC);

-- Index for user view history
CREATE INDEX IF NOT EXISTS idx_scenario_views_user
ON statedb.scenario_views(user_id, viewed_at DESC)
WHERE user_id IS NOT NULL;

COMMENT ON TABLE statedb.scenario_views IS 'Log of scenario card views for analytics';
COMMENT ON COLUMN statedb.scenario_views.user_id IS 'NULL for anonymous users';


-- ============================================================
-- View 1: v_scenario_cards (홈페이지용 시나리오 카드 뷰)
-- ============================================================
-- Combines scenario metadata with statistics for HomePage display

CREATE OR REPLACE VIEW statedb.v_scenario_cards AS
SELECT
    s.scenario_id,
    s.title,
    s.description,
    s.image_url,
    s.thumbnail_url,
    s.tags,
    s.card_size,
    s.route_path,
    s.display_order,
    s.is_active,
    COALESCE(ss.total_likes, 0) as likes,
    COALESCE(ss.total_comments, 0) as comments,
    COALESCE(ss.total_views, 0) as views,
    COALESCE(ss.total_completions, 0) as total_completions,
    COALESCE(ss.avg_session_duration, 0) as avg_session_duration,
    s.created_at,
    s.updated_at
FROM statedb.scenarios s
LEFT JOIN statedb.scenario_statistics ss ON s.scenario_id = ss.scenario_id
WHERE s.is_active = true
ORDER BY s.display_order, s.created_at DESC;

COMMENT ON VIEW statedb.v_scenario_cards IS 'Scenario cards with statistics for HomePage (active scenarios only)';


-- ============================================================
-- Function 1: increment_scenario_view_count()
-- ============================================================
-- Trigger function to update total_views when scenario_views record inserted

CREATE OR REPLACE FUNCTION statedb.increment_scenario_view_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Update scenario_statistics.total_views
    UPDATE statedb.scenario_statistics
    SET
        total_views = total_views + 1,
        last_updated = NOW()
    WHERE scenario_id = NEW.scenario_id;

    -- If statistics row doesn't exist, create it
    IF NOT FOUND THEN
        INSERT INTO statedb.scenario_statistics (scenario_id, total_views)
        VALUES (NEW.scenario_id, 1)
        ON CONFLICT (scenario_id) DO UPDATE
        SET total_views = statedb.scenario_statistics.total_views + 1,
            last_updated = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION statedb.increment_scenario_view_count() IS 'Auto-increment total_views when scenario_views record inserted';


-- ============================================================
-- Trigger 1: After scenario view inserted
-- ============================================================

DROP TRIGGER IF EXISTS trg_increment_scenario_views ON statedb.scenario_views;

CREATE TRIGGER trg_increment_scenario_views
    AFTER INSERT ON statedb.scenario_views
    FOR EACH ROW
    EXECUTE FUNCTION statedb.increment_scenario_view_count();


-- ============================================================
-- Function 2: update_scenario_like_count()
-- ============================================================
-- Update total_likes when user likes/unlikes a scenario

CREATE OR REPLACE FUNCTION statedb.update_scenario_like_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate new like count
    DECLARE
        new_like_count INT;
    BEGIN
        SELECT COUNT(*) INTO new_like_count
        FROM statedb.user_scenario_progress
        WHERE scenario_id = NEW.scenario_id AND is_liked = true;

        -- Update scenario_statistics
        UPDATE statedb.scenario_statistics
        SET
            total_likes = new_like_count,
            last_updated = NOW()
        WHERE scenario_id = NEW.scenario_id;

        -- If statistics row doesn't exist, create it
        IF NOT FOUND THEN
            INSERT INTO statedb.scenario_statistics (scenario_id, total_likes)
            VALUES (NEW.scenario_id, new_like_count)
            ON CONFLICT (scenario_id) DO UPDATE
            SET total_likes = EXCLUDED.total_likes,
                last_updated = NOW();
        END IF;
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION statedb.update_scenario_like_count() IS 'Recalculate total_likes when user likes/unlikes scenario';


-- ============================================================
-- Trigger 2: After user_scenario_progress updated
-- ============================================================

DROP TRIGGER IF EXISTS trg_update_scenario_likes ON statedb.user_scenario_progress;

CREATE TRIGGER trg_update_scenario_likes
    AFTER INSERT OR UPDATE OF is_liked ON statedb.user_scenario_progress
    FOR EACH ROW
    WHEN (NEW.is_liked IS DISTINCT FROM OLD.is_liked OR OLD IS NULL)
    EXECUTE FUNCTION statedb.update_scenario_like_count();


-- ============================================================
-- Function 3: update_scenario_timestamps()
-- ============================================================
-- Auto-update updated_at timestamp on scenarios table

CREATE OR REPLACE FUNCTION statedb.update_scenario_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- Trigger 3: Before scenario updated
-- ============================================================

DROP TRIGGER IF EXISTS trg_update_scenario_timestamps ON statedb.scenarios;

CREATE TRIGGER trg_update_scenario_timestamps
    BEFORE UPDATE ON statedb.scenarios
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_scenario_timestamps();


-- ============================================================
-- Grant Permissions
-- ============================================================

-- Grant access to tables
GRANT SELECT, INSERT, UPDATE, DELETE ON statedb.scenarios TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON statedb.scenario_statistics TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON statedb.user_scenario_progress TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON statedb.scenario_views TO PUBLIC;

-- Grant access to view
GRANT SELECT ON statedb.v_scenario_cards TO PUBLIC;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION statedb.increment_scenario_view_count() TO PUBLIC;
GRANT EXECUTE ON FUNCTION statedb.update_scenario_like_count() TO PUBLIC;
GRANT EXECUTE ON FUNCTION statedb.update_scenario_timestamps() TO PUBLIC;


-- ============================================================
-- Migration Complete
-- ============================================================

-- Verification queries (run after migration)
-- SELECT * FROM statedb.scenarios;
-- SELECT * FROM statedb.scenario_statistics;
-- SELECT * FROM statedb.v_scenario_cards;
