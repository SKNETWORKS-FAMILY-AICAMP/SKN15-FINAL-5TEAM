"""grant initial credits to all users

Revision ID: grant_initial_credits
Revises: 75a366f1b383
Create Date: 2025-11-12 00:00:00.000000

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'grant_initial_credits'
down_revision = '75a366f1b383'
branch_labels = None
depends_on = None

INITIAL_CREDITS = 200


def upgrade() -> None:
    """
    모든 사용자에게 초기 크레딧 200개를 지급합니다.
    신규 팀원이 도커를 실행하고 마이그레이션할 때 자동으로 실행됩니다.
    """
    conn = op.get_bind()

    # 1. 크레딧이 없거나 0인 사용자 조회
    result = conn.execute(text("""
        SELECT u.user_id, u.username
        FROM users u
        LEFT JOIN user_credits uc ON u.user_id = uc.user_id
        WHERE uc.user_id IS NULL OR uc.bubble_count = 0
    """))

    users = result.fetchall()

    if not users:
        print("✓ All users already have credits")
        return

    print(f"\n📊 Granting initial credits to {len(users)} users\n")

    # 2. 각 사용자에게 크레딧 지급
    for user in users:
        user_id = str(user.user_id)
        username = user.username

        # 2-1. user_credits 레코드 생성 또는 업데이트
        conn.execute(text("""
            INSERT INTO user_credits (user_id, bubble_count, total_purchased, total_consumed, last_updated, created_at)
            VALUES (:user_id, :amount, :amount, 0, NOW(), NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET
                bubble_count = user_credits.bubble_count + :amount,
                total_purchased = user_credits.total_purchased + :amount,
                last_updated = NOW()
        """), {
            "user_id": user_id,
            "amount": INITIAL_CREDITS
        })

        # 2-2. credit_transactions 기록 생성
        conn.execute(text("""
            INSERT INTO credit_transactions
                (user_id, transaction_type, amount, balance_after, description, created_at)
            VALUES
                (:user_id, 'initial', :amount,
                 (SELECT bubble_count FROM user_credits WHERE user_id = :user_id),
                 :description, NOW())
        """), {
            "user_id": user_id,
            "amount": INITIAL_CREDITS,
            "description": "회원가입 축하 크레딧"
        })

        print(f"  ✓ {username}: +{INITIAL_CREDITS} 버블")

    print(f"\n✓ Successfully granted {INITIAL_CREDITS} credits to {len(users)} users\n")


def downgrade() -> None:
    """
    다운그레이드 시에는 아무것도 하지 않습니다.
    (이미 지급된 크레딧은 롤백하지 않음)
    """
    pass
