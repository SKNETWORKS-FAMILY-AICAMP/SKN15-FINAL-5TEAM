-- ============================================================
-- KIME Chat Database Schema - Users Table
-- Version: 1.1
-- Description: 사용자 인증 및 계정 관리를 위한 Users 테이블 추가
-- ============================================================

-- ============================================================
-- StateDB Schema: Users 테이블 추가
-- ============================================================

-- ------------------------------------------------------------
-- 1. users: 사용자 계정 정보
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statedb.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    provider VARCHAR(50) DEFAULT 'email',
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_users_username ON statedb.users(username);
CREATE INDEX idx_users_email ON statedb.users(email);
CREATE INDEX idx_users_provider ON statedb.users(provider);
CREATE INDEX idx_users_active ON statedb.users(is_active) WHERE is_active = true;
CREATE INDEX idx_users_created ON statedb.users(created_at DESC);

COMMENT ON TABLE statedb.users IS '사용자 계정 정보';
COMMENT ON COLUMN statedb.users.user_id IS '사용자 고유 ID';
COMMENT ON COLUMN statedb.users.username IS '사용자명 (로그인용, 고유)';
COMMENT ON COLUMN statedb.users.email IS '이메일 (소셜 로그인 시 사용, NULL 가능)';
COMMENT ON COLUMN statedb.users.password_hash IS '비밀번호 해시 (bcrypt)';
COMMENT ON COLUMN statedb.users.provider IS '인증 제공자 (email, google, kakao 등)';
COMMENT ON COLUMN statedb.users.display_name IS '표시 이름';
COMMENT ON COLUMN statedb.users.last_login IS '마지막 로그인 시간';

-- ------------------------------------------------------------
-- 2. sessions 테이블에 user_id 컬럼 추가
-- ------------------------------------------------------------
ALTER TABLE statedb.sessions
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES statedb.users(user_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_user ON statedb.sessions(user_id);

COMMENT ON COLUMN statedb.sessions.user_id IS '세션을 시작한 사용자 ID';

-- ------------------------------------------------------------
-- 3. 기본 테스트 계정 추가 (비밀번호: 123)
-- ------------------------------------------------------------
-- bcrypt 해시: $2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm
-- 비밀번호 "123"의 bcrypt 해시

INSERT INTO statedb.users (username, password_hash, provider, display_name) VALUES
    ('tanjiro', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '탄지로'),
    ('zenitsu', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '젠이츠'),
    ('inosuke', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '이노스케'),
    ('giyu', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '기유'),
    ('rengoku', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '렌고쿠'),
    ('tengen', '$2b$12$uA2z4GTQFex1sqIboFzxhO41gDKAucISRY/4BK/HufRiE/wrfCIXm', 'email', '텐겐')
ON CONFLICT (username) DO NOTHING;

-- 기본 인덱스 통계 업데이트
ANALYZE statedb.users;
ANALYZE statedb.sessions;

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Users Table Created Successfully!';
    RAISE NOTICE 'Test accounts added: tanjiro, zenitsu, inosuke, giyu, rengoku, tengen';
    RAISE NOTICE 'Default password for all accounts: 123';
    RAISE NOTICE '============================================================';
END $$;
