"""create_user_profiles

Revision ID: 20251117_0001
Revises: 1445deaf4f1d
Create Date: 2025-11-17 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision = '20251117_0001'
down_revision = '1445deaf4f1d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create user_profiles table in auth schema
    목적: 최소 기억 유지 (이름, 호칭, 말투, 취향 등)
    """
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),

        # 기본 정보
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('speaking_style', sa.String(50), nullable=True),

        # 고정 취향
        sa.Column('likes', ARRAY(sa.String), nullable=True),
        sa.Column('dislikes', ARRAY(sa.String), nullable=True),

        # 안정적 성격 태그
        sa.Column('personality_traits', JSONB, nullable=True),

        # 메타데이터
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
        schema='auth'
    )

    # Index for fast user_id lookup
    op.create_index(
        'idx_user_profiles_user_id',
        'user_profiles',
        ['user_id'],
        schema='auth'
    )


def downgrade() -> None:
    """
    Drop user_profiles table
    """
    op.drop_index('idx_user_profiles_user_id', table_name='user_profiles', schema='auth')
    op.drop_table('user_profiles', schema='auth')
