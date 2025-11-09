#!/usr/bin/env python3
"""API 서버가 사용하는 DB 연결 정보 확인"""
import sys
sys.path.insert(0, '/Users/jtm427/Desktop/workspace/backend')

from src.database.session_manager import create_hybrid_session_manager_from_env

print("="*60)
print("API 서버 DB 연결 정보 확인")
print("="*60)

# HybridSessionManager 생성 (API 서버와 동일한 방식)
hybrid_manager = create_hybrid_session_manager_from_env()

# DatabaseManager 정보 확인
db = hybrid_manager.db

print(f"\n📊 Connection Pool 정보:")
print(f"  - Min connections: {db.connection_pool.minconn}")
print(f"  - Max connections: {db.connection_pool.maxconn}")

# 연결 가져와서 정보 출력
with db.get_connection() as conn:
    dsn_params = conn.get_dsn_parameters()
    print(f"\n🔌 실제 연결 정보:")
    print(f"  - Host: {dsn_params.get('host')}")
    print(f"  - Port: {dsn_params.get('port')}")
    print(f"  - Database: {dsn_params.get('dbname')}")
    print(f"  - User: {dsn_params.get('user')}")

    # 테스트: 사용자 수 확인
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        print(f"\n👥 users 테이블 사용자 수: {count}")

        # 최근 사용자 5명 조회
        cur.execute("""
            SELECT username, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 5
        """)
        users = cur.fetchall()
        print(f"\n📋 최근 생성된 사용자들:")
        for username, created_at in users:
            print(f"  - {username}: {created_at}")

print(f"\n{'='*60}")
