#!/usr/bin/env python3
"""직접 DB 연결 테스트"""
from src.database.db_manager import create_database_manager_from_env
import bcrypt

print("="*60)
print("직접 DB 연결 테스트")
print("="*60)

# 1. DatabaseManager 생성
db = create_database_manager_from_env()
print(f"✅ DatabaseManager 생성 완료")

# 2. 테스트 사용자 생성
username = "directtest001"
password = "test1234"
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"\n📝 사용자 생성 시도: {username}")
user_id = db.create_user(
    username=username,
    password_hash=password_hash,
    email=f"{username}@test.com",
    display_name="직접테스트001"
)

if user_id:
    print(f"✅ User created with ID: {user_id}")
else:
    print(f"❌ Failed to create user")

# 3. 생성된 사용자 조회
print(f"\n🔍 사용자 조회 시도: {username}")
user = db.get_user_by_username(username)

if user:
    print(f"✅ User found:")
    print(f"  - user_id: {user['user_id']}")
    print(f"  - username: {user['username']}")
    print(f"  - email: {user['email']}")
    print(f"  - display_name: {user['display_name']}")
else:
    print(f"❌ User not found")

print(f"\n{'='*60}")
print("테스트 완료")
print(f"{'='*60}")
