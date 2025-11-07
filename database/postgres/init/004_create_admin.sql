-- 관리자 계정 추가 명령 :  docker exec -i postgresql psql -U kime -d kimedb < backend/create_admin.sql
-- admin/ admin123

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create admin user
-- Password: admin123 (bcrypt hash)
-- You can change this password later
INSERT INTO users (username, password_hash, role)
VALUES ('admin', '$2b$12$7.2tSHKVQ24kujVBx.G84e7DxKat.sXkXDvwtq2YEKGGQSB0CmZxO', 'admin')
ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Show created admin
SELECT id, username, role, created_at FROM users WHERE role = 'admin';
