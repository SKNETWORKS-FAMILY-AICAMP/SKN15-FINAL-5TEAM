"""
Grant Initial Credits to Existing Users

회원가입 시 지급되는 200 크레딧을 기존 사용자들에게 소급 지급하는 스크립트
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.core.logging import get_parent_logger

logger = get_parent_logger("GrantInitialCredits")
settings = get_settings()

INITIAL_CREDITS = 200


async def grant_initial_credits():
    """
    모든 기존 사용자에게 초기 크레딧 200개를 지급합니다.
    이미 크레딧이 있는 사용자는 건너뜁니다.
    """
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # 1. 크레딧이 없는 사용자 조회
            query_users = text("""
                SELECT u.user_id, u.username, u.display_name
                FROM users u
                LEFT JOIN user_credits uc ON u.user_id = uc.user_id
                WHERE uc.user_id IS NULL OR uc.bubble_count = 0
                ORDER BY u.created_at
            """)

            result = await session.execute(query_users)
            users = result.fetchall()

            if not users:
                logger.info("grant_initial_credits", "No users need initial credits")
                print("✓ All users already have credits")
                return

            logger.info("grant_initial_credits", f"Found {len(users)} users without credits")
            print(f"\n📊 Found {len(users)} users without credits\n")

            # 2. 각 사용자에게 크레딧 지급
            granted_count = 0
            failed_count = 0

            for user in users:
                user_id = str(user.user_id)
                username = user.username
                display_name = user.display_name

                try:
                    # 2-1. user_credits 레코드 생성 또는 업데이트
                    upsert_credits = text("""
                        INSERT INTO user_credits (user_id, bubble_count, total_purchased, total_consumed, last_updated, created_at)
                        VALUES (:user_id, :amount, :amount, 0, NOW(), NOW())
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            bubble_count = user_credits.bubble_count + :amount,
                            total_purchased = user_credits.total_purchased + :amount,
                            last_updated = NOW()
                    """)

                    await session.execute(upsert_credits, {
                        "user_id": user_id,
                        "amount": INITIAL_CREDITS
                    })

                    # 2-2. credit_transactions 기록 생성
                    insert_transaction = text("""
                        INSERT INTO credit_transactions
                            (user_id, transaction_type, amount, balance_after, description, created_at)
                        VALUES
                            (:user_id, 'initial', :amount,
                             (SELECT bubble_count FROM user_credits WHERE user_id = :user_id),
                             :description, NOW())
                    """)

                    await session.execute(insert_transaction, {
                        "user_id": user_id,
                        "amount": INITIAL_CREDITS,
                        "description": "회원가입 축하 크레딧 (소급 지급)"
                    })

                    granted_count += 1
                    logger.info("grant_initial_credits", f"Granted credits to user",
                                user_id=user_id, username=username, amount=INITIAL_CREDITS)
                    print(f"  ✓ {username} ({display_name}): +{INITIAL_CREDITS} 버블")

                except Exception as e:
                    failed_count += 1
                    logger.error("grant_initial_credits", f"Failed to grant credits: {e}",
                                 user_id=user_id, username=username)
                    print(f"  ✗ {username}: 실패 - {e}")

            # 3. 커밋
            await session.commit()

            # 4. 결과 출력
            print(f"\n{'='*60}")
            print(f"📈 Summary:")
            print(f"  - Total users processed: {len(users)}")
            print(f"  - Successfully granted: {granted_count}")
            print(f"  - Failed: {failed_count}")
            print(f"  - Credits per user: {INITIAL_CREDITS} 버블")
            print(f"  - Total credits granted: {granted_count * INITIAL_CREDITS} 버블")
            print(f"{'='*60}\n")

            logger.info("grant_initial_credits", "Initial credits granted successfully",
                        total=len(users), granted=granted_count, failed=failed_count)

        except Exception as e:
            await session.rollback()
            logger.error("grant_initial_credits", f"Failed to grant initial credits: {e}")
            print(f"\n✗ Error: {e}")
            raise

        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎁 Grant Initial Credits to Existing Users")
    print("="*60)
    print(f"Amount: {INITIAL_CREDITS} 버블 per user")
    print("="*60 + "\n")

    asyncio.run(grant_initial_credits())

    print("✓ Done!\n")
