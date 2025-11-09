-- ============================================================
-- 019_scenario_comments.sql
-- 시나리오 댓글 시스템
-- ============================================================
-- 목적: 시나리오 상세 페이지에 댓글 기능 추가
-- ============================================================

-- 1. 댓글 테이블
CREATE TABLE IF NOT EXISTS statedb.scenario_comments (
    id BIGSERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) NOT NULL REFERENCES statedb.scenarios(scenario_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,

    -- 댓글 내용
    content TEXT NOT NULL CHECK (char_length(content) >= 1 AND char_length(content) <= 1000),

    -- 대댓글 지원
    parent_comment_id BIGINT REFERENCES statedb.scenario_comments(id) ON DELETE CASCADE,

    -- 추천 수
    like_count INTEGER DEFAULT 0 CHECK (like_count >= 0),

    -- 상태
    is_deleted BOOLEAN DEFAULT FALSE,
    is_edited BOOLEAN DEFAULT FALSE,

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 1-1. 댓글 추천(좋아요) 테이블
CREATE TABLE IF NOT EXISTS statedb.comment_likes (
    comment_id BIGINT NOT NULL REFERENCES statedb.scenario_comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (comment_id, user_id)
);

-- 2. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_scenario_comments_scenario
    ON statedb.scenario_comments(scenario_id, created_at DESC)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_scenario_comments_scenario_likes
    ON statedb.scenario_comments(scenario_id, like_count DESC)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_scenario_comments_user
    ON statedb.scenario_comments(user_id);

CREATE INDEX IF NOT EXISTS idx_scenario_comments_parent
    ON statedb.scenario_comments(parent_comment_id)
    WHERE parent_comment_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comment_likes_comment
    ON statedb.comment_likes(comment_id);

CREATE INDEX IF NOT EXISTS idx_comment_likes_user
    ON statedb.comment_likes(user_id);

-- 3. 댓글 수 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION statedb.update_scenario_comment_count()
RETURNS TRIGGER AS $$
BEGIN
    -- 댓글 추가 시
    IF (TG_OP = 'INSERT' AND NOT NEW.is_deleted AND NEW.parent_comment_id IS NULL) THEN
        UPDATE statedb.scenario_statistics
        SET total_comments = total_comments + 1,
            last_updated = NOW()
        WHERE scenario_id = NEW.scenario_id;

        -- scenario_statistics에 레코드가 없으면 생성
        INSERT INTO statedb.scenario_statistics (scenario_id, total_comments)
        VALUES (NEW.scenario_id, 1)
        ON CONFLICT (scenario_id) DO NOTHING;

    -- 댓글 삭제 시
    ELSIF (TG_OP = 'UPDATE' AND OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE AND NEW.parent_comment_id IS NULL) THEN
        UPDATE statedb.scenario_statistics
        SET total_comments = GREATEST(0, total_comments - 1),
            last_updated = NOW()
        WHERE scenario_id = NEW.scenario_id;

    -- 댓글 복구 시
    ELSIF (TG_OP = 'UPDATE' AND OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE AND NEW.parent_comment_id IS NULL) THEN
        UPDATE statedb.scenario_statistics
        SET total_comments = total_comments + 1,
            last_updated = NOW()
        WHERE scenario_id = NEW.scenario_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_scenario_comment_count ON statedb.scenario_comments;
CREATE TRIGGER trigger_update_scenario_comment_count
    AFTER INSERT OR UPDATE OF is_deleted
    ON statedb.scenario_comments
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_scenario_comment_count();

-- 4. 댓글 추천 수 업데이트 트리거
CREATE OR REPLACE FUNCTION statedb.update_comment_like_count()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE statedb.scenario_comments
        SET like_count = like_count + 1
        WHERE id = NEW.comment_id;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE statedb.scenario_comments
        SET like_count = GREATEST(0, like_count - 1)
        WHERE id = OLD.comment_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_comment_like_count ON statedb.comment_likes;
CREATE TRIGGER trigger_update_comment_like_count
    AFTER INSERT OR DELETE
    ON statedb.comment_likes
    FOR EACH ROW
    EXECUTE FUNCTION statedb.update_comment_like_count();

-- 5. 댓글 조회 함수 (최신순/인기순 지원)
CREATE OR REPLACE FUNCTION statedb.get_scenario_comments(
    p_scenario_id VARCHAR(50),
    p_sort_by VARCHAR(20) DEFAULT 'recent',  -- 'recent' or 'popular'
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0,
    p_user_id UUID DEFAULT NULL  -- 현재 사용자 ID (좋아요 여부 확인용)
)
RETURNS TABLE(
    id BIGINT,
    scenario_id VARCHAR(50),
    user_id UUID,
    username VARCHAR(50),
    display_name VARCHAR(100),
    content TEXT,
    parent_comment_id BIGINT,
    like_count INTEGER,
    reply_count INTEGER,
    is_liked BOOLEAN,
    is_edited BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    WITH comment_replies AS (
        -- 각 댓글의 대댓글 수 계산
        SELECT
            sc.parent_comment_id,
            COUNT(*) as reply_count
        FROM statedb.scenario_comments sc
        WHERE sc.parent_comment_id IS NOT NULL
        AND sc.is_deleted = FALSE
        GROUP BY sc.parent_comment_id
    )
    SELECT
        c.id,
        c.scenario_id,
        c.user_id,
        u.username,
        u.display_name,
        CASE
            WHEN c.is_deleted THEN '삭제된 댓글입니다.'
            ELSE c.content
        END as content,
        c.parent_comment_id,
        c.like_count,
        COALESCE(cr.reply_count, 0)::INTEGER as reply_count,
        CASE
            WHEN p_user_id IS NOT NULL THEN EXISTS(
                SELECT 1 FROM statedb.comment_likes cl
                WHERE cl.comment_id = c.id AND cl.user_id = p_user_id
            )
            ELSE FALSE
        END as is_liked,
        c.is_edited,
        c.created_at,
        c.updated_at
    FROM statedb.scenario_comments c
    LEFT JOIN statedb.users u ON c.user_id = u.user_id
    LEFT JOIN comment_replies cr ON c.id = cr.parent_comment_id
    WHERE c.scenario_id = p_scenario_id
    AND c.parent_comment_id IS NULL  -- 최상위 댓글만
    ORDER BY
        CASE WHEN p_sort_by = 'popular' THEN c.like_count END DESC,
        CASE WHEN p_sort_by = 'recent' THEN c.created_at END DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- 6. 대댓글 조회 함수
CREATE OR REPLACE FUNCTION statedb.get_comment_replies(
    p_parent_comment_id BIGINT,
    p_user_id UUID DEFAULT NULL
)
RETURNS TABLE(
    id BIGINT,
    scenario_id VARCHAR(50),
    user_id UUID,
    username VARCHAR(50),
    display_name VARCHAR(100),
    content TEXT,
    like_count INTEGER,
    is_liked BOOLEAN,
    is_edited BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.scenario_id,
        c.user_id,
        u.username,
        u.display_name,
        CASE
            WHEN c.is_deleted THEN '삭제된 댓글입니다.'
            ELSE c.content
        END as content,
        c.like_count,
        CASE
            WHEN p_user_id IS NOT NULL THEN EXISTS(
                SELECT 1 FROM statedb.comment_likes cl
                WHERE cl.comment_id = c.id AND cl.user_id = p_user_id
            )
            ELSE FALSE
        END as is_liked,
        c.is_edited,
        c.created_at,
        c.updated_at
    FROM statedb.scenario_comments c
    LEFT JOIN statedb.users u ON c.user_id = u.user_id
    WHERE c.parent_comment_id = p_parent_comment_id
    AND c.is_deleted = FALSE
    ORDER BY c.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- 7. 코멘트
COMMENT ON TABLE statedb.scenario_comments IS '시나리오 댓글 (1단계 대댓글 지원, 추천 기능)';
COMMENT ON TABLE statedb.comment_likes IS '댓글 추천(좋아요) 기록';
COMMENT ON COLUMN statedb.scenario_comments.content IS '댓글 내용 (1~1000자)';
COMMENT ON COLUMN statedb.scenario_comments.parent_comment_id IS '상위 댓글 ID (NULL이면 최상위 댓글)';
COMMENT ON COLUMN statedb.scenario_comments.like_count IS '댓글 추천 수';
COMMENT ON COLUMN statedb.scenario_comments.is_deleted IS '소프트 삭제 플래그';
COMMENT ON COLUMN statedb.scenario_comments.is_edited IS '수정 여부';
COMMENT ON FUNCTION statedb.get_scenario_comments IS '시나리오의 최상위 댓글 목록 조회 (최신순/인기순 정렬 지원)';
COMMENT ON FUNCTION statedb.get_comment_replies IS '특정 댓글의 대댓글 목록 조회';
