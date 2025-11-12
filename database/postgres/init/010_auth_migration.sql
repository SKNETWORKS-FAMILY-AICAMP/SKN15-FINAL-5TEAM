-- Auth Tables Migration
-- Created: 2025-11-12
-- Purpose: Add missing columns to auth tables

-- Add missing columns to users table
ALTER TABLE auth.users
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user',
ADD COLUMN IF NOT EXISTS total_sessions INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_bubbles INTEGER DEFAULT 0;

-- Add comments
COMMENT ON COLUMN auth.users.is_verified IS '이메일 인증 완료 여부';
COMMENT ON COLUMN auth.users.role IS '사용자 역할 (user, admin, moderator)';
COMMENT ON COLUMN auth.users.total_sessions IS '총 세션 수 (비정규화)';
COMMENT ON COLUMN auth.users.total_bubbles IS '총 획득 버블 수 (비정규화)';
