#!/usr/bin/env python3
"""직접 DB 삽입 및 즉시 검증"""
import sys
import subprocess
from src.database.db_manager import create_database_manager_from_env
import bcrypt
from datetime import datetime

print("="*70)
print("🔬 직접 DB 삽입 및 즉시 검증 테스트")
print("="*70)

# 타임스탬프로 고유 사용자명 생성
timestamp = datetime.now().strftime("%H%M%S%f")
username = f"directtest_{timestamp}"
email = f"{username}@test.com"
display_name = f"직접테스트{timestamp}"
password = "test1234"

print(f"\n📝 생성할 사용자:")
print(f"  Username: {username}")
print(f"  Email: {email}")
print(f"  Display Name: {display_name}")

# 1. DatabaseManager로 사용자 생성
db = create_database_manager_from_env()
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"\n🔨 DatabaseManager.create_user() 호출...")
user_id = db.create_user(
    username=username,
    password_hash=password_hash,
    email=email,
    display_name=display_name
)

if user_id:
    print(f"✅ create_user() 성공: user_id = {user_id}")
else:
    print(f"❌ create_user() 실패!")
    sys.exit(1)

# 2. DatabaseManager로 사용자 조회
print(f"\n🔍 DatabaseManager.get_user_by_username() 호출...")
user = db.get_user_by_username(username)

if user:
    print(f"✅ get_user_by_username() 성공:")
    print(f"  - user_id: {user['user_id']}")
    print(f"  - username: {user['username']}")
    print(f"  - email: {user['email']}")
else:
    print(f"❌ get_user_by_username() 실패 - 사용자 없음")

# 3. PostgreSQL에서 직접 조회
print(f"\n🗄️ PostgreSQL 직접 조회 (docker exec)...")
cmd = [
    "docker", "exec", "kime-postgres", "psql", "-U", "kime", "-d", "kimedb",
    "-c", f"SELECT user_id, username, email, display_name FROM users WHERE username = '{username}';"
]

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)

if username in result.stdout:
    print(f"✅✅✅ 성공! PostgreSQL에 실제로 저장됨!")
else:
    print(f"❌❌❌ 실패! PostgreSQL에 저장되지 않음!")
    print(f"\n🔍 전체 users 테이블 조회:")
    cmd2 = [
        "docker", "exec", "kime-postgres", "psql", "-U", "kime", "-d", "kimedb",
        "-c", "SELECT username, created_at FROM users ORDER BY created_at DESC LIMIT 10;"
    ]
    result2 = subprocess.run(cmd2, capture_output=True, text=True)
    print(result2.stdout)

print(f"\n{'='*70}")
