"""
Create test users for development
"""
import asyncio
import uuid
import bcrypt
from datetime import datetime
from sqlalchemy import text
from app.core.database import engine


async def create_test_users():
    """Create test users for login functionality testing"""

    test_users = [
        {
            "username": "tanjiro",
            "password": "test123",
            "display_name": "탄지로",
            "email": "tanjiro@test.com",
            "role": "user"
        },
        {
            "username": "zenitsu",
            "password": "test123",
            "display_name": "젠이츠",
            "email": "zenitsu@test.com",
            "role": "user"
        },
        {
            "username": "admin",
            "password": "admin123",
            "display_name": "관리자",
            "email": "admin@test.com",
            "role": "admin"
        }
    ]

    async with engine.begin() as conn:
        for user_data in test_users:
            # Generate UUID
            user_id = uuid.uuid4()

            # Hash password using bcrypt
            password_bytes = user_data["password"].encode('utf-8')
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

            # Insert user
            query = text("""
                INSERT INTO users (
                    user_id, username, password_hash, display_name, email,
                    is_active, is_verified, role, total_sessions, total_bubbles,
                    created_at, updated_at
                )
                VALUES (
                    :user_id, :username, :password_hash, :display_name, :email,
                    :is_active, :is_verified, :role, :total_sessions, :total_bubbles,
                    :created_at, :updated_at
                )
                ON CONFLICT (username) DO NOTHING
            """)

            await conn.execute(query, {
                "user_id": user_id,
                "username": user_data["username"],
                "password_hash": password_hash,
                "display_name": user_data["display_name"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": True,
                "role": user_data["role"],
                "total_sessions": 0,
                "total_bubbles": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

            print(f"✅ Created user: {user_data['username']} (password: {user_data['password']})")

    print("\n🎉 All test users created successfully!")
    print("\nTest users:")
    print("  - tanjiro / test123")
    print("  - zenitsu / test123")
    print("  - admin / admin123")


if __name__ == "__main__":
    asyncio.run(create_test_users())
