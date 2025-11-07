-- Password Reset Tokens Table
-- 비밀번호 재설정을 위한 토큰 저장

CREATE TABLE IF NOT EXISTS statedb.password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 토큰 검색을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON statedb.password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON statedb.password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON statedb.password_reset_tokens(expires_at);

-- 만료된 토큰 자동 삭제 함수 (선택사항)
CREATE OR REPLACE FUNCTION statedb.cleanup_expired_reset_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM statedb.password_reset_tokens
    WHERE expires_at < NOW() OR used = true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE statedb.password_reset_tokens IS '비밀번호 재설정 토큰 저장';
COMMENT ON COLUMN statedb.password_reset_tokens.token IS '재설정 토큰 (UUID 또는 랜덤 문자열)';
COMMENT ON COLUMN statedb.password_reset_tokens.expires_at IS '토큰 만료 시간 (보통 1시간)';
COMMENT ON COLUMN statedb.password_reset_tokens.used IS '토큰 사용 여부';
