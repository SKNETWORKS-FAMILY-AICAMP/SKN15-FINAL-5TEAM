"""create_short_term_memories

Revision ID: 20251117_0002
Revises: 20251117_0001
Create Date: 2025-11-17 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20251117_0002'
down_revision = '20251117_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create short_term_memories table in knowledge schema
    목적: 세션 전용 맥락 저장 (5턴 단위 chunk 요약)
    """
    op.create_table(
        'short_term_memories',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', sa.String(100), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), nullable=False),

        # STM 내용
        sa.Column('stm_summary', sa.Text(), nullable=True),
        sa.Column('chunk_summaries', JSONB, nullable=True),  # 5턴 단위 chunk 배열

        # 통계
        sa.Column('turn_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_turn_timestamp', sa.DateTime(timezone=True), nullable=True),

        # 메타데이터
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'scenario_id', 'session_id'),
        schema='knowledge'
    )

    # Indexes for fast lookup
    op.create_index(
        'idx_stm_session',
        'short_term_memories',
        ['session_id'],
        schema='knowledge'
    )

    op.create_index(
        'idx_stm_user_scenario',
        'short_term_memories',
        ['user_id', 'scenario_id'],
        schema='knowledge'
    )


def downgrade() -> None:
    """
    Drop short_term_memories table
    """
    op.drop_index('idx_stm_user_scenario', table_name='short_term_memories', schema='knowledge')
    op.drop_index('idx_stm_session', table_name='short_term_memories', schema='knowledge')
    op.drop_table('short_term_memories', schema='knowledge')
