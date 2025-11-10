-- KIME DB Initialization Script

-- Enable UUID extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop existing tables if they exist
DROP TABLE IF EXISTS comment_likes CASCADE;
DROP TABLE IF EXISTS scenario_likes CASCADE;
DROP TABLE IF EXISTS scenario_comments CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS gallery_images CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    total_sessions INTEGER DEFAULT 0,
    total_bubbles INTEGER DEFAULT 0,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Create sessions table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    current_stage VARCHAR(255),
    turn_count INTEGER DEFAULT 0,
    stage_turn INTEGER DEFAULT 0,
    final_ending VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    conversation_summary TEXT,
    summary_updated_at TIMESTAMP,
    summary_turn_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_scenario_id ON sessions(scenario_id);
CREATE INDEX idx_sessions_created ON sessions(created_at);
CREATE INDEX idx_sessions_is_active ON sessions(is_active);

-- Create scenario comments table
CREATE TABLE scenario_comments (
    id BIGSERIAL PRIMARY KEY,
    scenario_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL CHECK (char_length(content) >= 1 AND char_length(content) <= 1000),
    parent_comment_id BIGINT REFERENCES scenario_comments(id) ON DELETE CASCADE,
    like_count INTEGER DEFAULT 0 CHECK (like_count >= 0),
    is_deleted BOOLEAN DEFAULT FALSE,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scenario_comments_scenario ON scenario_comments(scenario_id, created_at);
CREATE INDEX idx_scenario_comments_user ON scenario_comments(user_id);
CREATE INDEX idx_scenario_comments_parent ON scenario_comments(parent_comment_id);

-- Create scenario likes table
CREATE TABLE scenario_likes (
    like_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id VARCHAR(50) NOT NULL,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scenario_id, user_id)
);

CREATE INDEX idx_scenario_likes_scenario ON scenario_likes(scenario_id);
CREATE INDEX idx_scenario_likes_user ON scenario_likes(user_id);

-- Create comment likes table
CREATE TABLE comment_likes (
    comment_id BIGINT NOT NULL REFERENCES scenario_comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comment_id, user_id)
);

CREATE INDEX idx_comment_likes_comment ON comment_likes(comment_id);
CREATE INDEX idx_comment_likes_user ON comment_likes(user_id);

-- Insert test users (password is 'test123' for all)
INSERT INTO users (username, password_hash, display_name, role)
VALUES
    ('tanjiro', '$2b$12$KIXxLVZ7qD3ZqL.AwvVyF.oYxKGJ1pD9mN0fWxqC5XJ1gNvK8Uw.m', '탄지로', 'user'),
    ('admin', '$2b$12$KIXxLVZ7qD3ZqL.AwvVyF.oYxKGJ1pD9mN0fWxqC5XJ1gNvK8Uw.m', '관리자', 'admin'),
    ('nezuko', '$2b$12$KIXxLVZ7qD3ZqL.AwvVyF.oYxKGJ1pD9mN0fWxqC5XJ1gNvK8Uw.m', '네즈코', 'user'),
    ('zenitsu', '$2b$12$KIXxLVZ7qD3ZqL.AwvVyF.oYxKGJ1pD9mN0fWxqC5XJ1gNvK8Uw.m', '젠이츠', 'user');
