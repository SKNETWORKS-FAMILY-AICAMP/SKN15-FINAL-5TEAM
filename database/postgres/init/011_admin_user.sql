-- 관리자 계정 생성
-- Username: admin
-- Password: admin123
-- Bcrypt hash: $2b$12$7.2tSHKVQ24kujVBx.G84e7DxKat.sXkXDvwtq2YEKGGQSB0CmZxO
-- Fixed UUID: 00000000-0000-0000-0000-000000000001 (deterministic for admin)

-- Create admin user in auth.users
INSERT INTO auth.users (
    user_id,
    username,
    password_hash,
    provider,
    display_name,
    email,
    is_active,
    is_verified,
    role,
    total_sessions,
    total_bubbles,
    last_login,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'admin',
    '$2b$12$7.2tSHKVQ24kujVBx.G84e7DxKat.sXkXDvwtq2YEKGGQSB0CmZxO',
    'email',
    'Administrator',
    'admin@example.com',
    true,
    true,
    'admin',
    0,
    50000,
    NULL,
    NOW(),
    NOW()
)
ON CONFLICT (username) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_verified = true,
    updated_at = NOW();

-- Initialize admin user credits
INSERT INTO auth.user_credits (user_id, bubble_count, total_purchased, total_consumed)
SELECT user_id, 50000, 50000, 0
FROM auth.users
WHERE username = 'admin'
ON CONFLICT (user_id) DO UPDATE SET
    bubble_count = 50000,
    total_purchased = 50000,
    last_updated = NOW();

-- Show created admin
SELECT user_id, username, email, role, is_active, is_verified, created_at
FROM auth.users
WHERE username = 'admin';
