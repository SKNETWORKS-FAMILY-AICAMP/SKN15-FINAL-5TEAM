-- 관리자 계정 생성
-- Username: admin
-- Password: admin123
-- Bcrypt hash: $2b$12$7.2tSHKVQ24kujVBx.G84e7DxKat.sXkXDvwtq2YEKGGQSB0CmZxO

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
    gen_random_uuid(),
    'admin',
    '$2b$12$7.2tSHKVQ24kujVBx.G84e7DxKat.sXkXDvwtq2YEKGGQSB0CmZxO',
    'email',
    'Administrator',
    'admin@example.com',
    true,
    true,
    'admin',
    0,
    0,
    NULL,
    NOW(),
    NOW()
)
ON CONFLICT (username) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_verified = true,
    updated_at = NOW();

-- Show created admin
SELECT user_id, username, email, role, is_active, is_verified, created_at
FROM auth.users
WHERE username = 'admin';
