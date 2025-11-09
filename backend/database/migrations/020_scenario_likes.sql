-- ============================================================
-- Migration 020: Scenario Likes System
-- ============================================================
-- Purpose: 시나리오 좋아요 기능
-- ============================================================

-- ============================================================
-- 1. Create scenario_likes table
-- ============================================================
CREATE TABLE IF NOT EXISTS statedb.scenario_likes (
    like_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    -- Foreign Keys
    CONSTRAINT scenario_likes_scenario_id_fkey
        FOREIGN KEY (scenario_id)
        REFERENCES statedb.scenarios(scenario_id)
        ON DELETE CASCADE,
    CONSTRAINT scenario_likes_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES statedb.users(user_id)
        ON DELETE CASCADE,

    -- Unique constraint: 한 유저는 시나리오당 한 번만 좋아요 가능
    CONSTRAINT scenario_likes_unique
        UNIQUE (scenario_id, user_id)
);

-- ============================================================
-- 2. Create indexes for performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_scenario_likes_scenario
    ON statedb.scenario_likes(scenario_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scenario_likes_user
    ON statedb.scenario_likes(user_id, created_at DESC);

-- ============================================================
-- 3. Create trigger function to update scenario_statistics
-- ============================================================
CREATE OR REPLACE FUNCTION statedb.update_scenario_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- 좋아요 추가 시
        UPDATE statedb.scenario_statistics
        SET
            total_likes = total_likes + 1,
            last_updated = NOW()
        WHERE scenario_id = NEW.scenario_id;

        -- statistics 레코드가 없으면 생성
        IF NOT FOUND THEN
            INSERT INTO statedb.scenario_statistics (scenario_id, total_likes)
            VALUES (NEW.scenario_id, 1)
            ON CONFLICT (scenario_id) DO UPDATE
            SET total_likes = statedb.scenario_statistics.total_likes + 1,
                last_updated = NOW();
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        -- 좋아요 취소 시
        UPDATE statedb.scenario_statistics
        SET
            total_likes = GREATEST(0, total_likes - 1),
            last_updated = NOW()
        WHERE scenario_id = OLD.scenario_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 4. Create trigger
-- ============================================================
DROP TRIGGER IF EXISTS trigger_update_scenario_like_count ON statedb.scenario_likes;

CREATE TRIGGER trigger_update_scenario_like_count
AFTER INSERT OR DELETE ON statedb.scenario_likes
FOR EACH ROW
EXECUTE FUNCTION statedb.update_scenario_like_count();

-- ============================================================
-- 5. Initialize statistics for existing scenarios
-- ============================================================
INSERT INTO statedb.scenario_statistics (scenario_id, total_likes, total_comments, total_views)
SELECT
    s.scenario_id,
    0 as total_likes,
    0 as total_comments,
    0 as total_views
FROM statedb.scenarios s
WHERE NOT EXISTS (
    SELECT 1 FROM statedb.scenario_statistics ss
    WHERE ss.scenario_id = s.scenario_id
)
ON CONFLICT (scenario_id) DO NOTHING;

-- ============================================================
-- 6. Success message
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 020: Scenario Likes System created successfully!';
END $$;
