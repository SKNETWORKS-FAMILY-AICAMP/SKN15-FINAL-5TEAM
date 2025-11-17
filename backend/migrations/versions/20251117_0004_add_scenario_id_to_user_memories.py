"""add_scenario_id_to_user_memories

Revision ID: 20251117_0004
Revises: 20251117_0003
Create Date: 2025-11-17 00:04:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251117_0004'
down_revision = '20251117_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add scenario_id column to user_memories table
    목적: LTM을 시나리오별로 구분 (free-talk 전용)

    Note: source_session_id는 기존 세션 추적용으로 유지
    """
    # scenario_id 컬럼 추가 (nullable, 기존 데이터는 'free-talk'로 설정)
    op.add_column(
        'user_memories',
        sa.Column('scenario_id', sa.String(100), nullable=True),
        schema='knowledge'
    )

    # 기존 데이터를 'free-talk'로 업데이트
    op.execute("""
        UPDATE knowledge.user_memories
        SET scenario_id = 'free-talk'
        WHERE scenario_id IS NULL
    """)

    # scenario_id를 NOT NULL로 변경
    op.alter_column(
        'user_memories',
        'scenario_id',
        nullable=False,
        schema='knowledge'
    )

    # Index for fast scenario_id lookup
    op.create_index(
        'idx_user_memories_scenario',
        'user_memories',
        ['user_id', 'scenario_id'],
        schema='knowledge'
    )

    # Comment for clarity
    op.execute("""
        COMMENT ON COLUMN knowledge.user_memories.scenario_id IS
        'Scenario identifier - LTM should only be created from free-talk mode'
    """)


def downgrade() -> None:
    """
    Remove scenario_id column from user_memories
    """
    op.drop_index('idx_user_memories_scenario', table_name='user_memories', schema='knowledge')
    op.drop_column('user_memories', 'scenario_id', schema='knowledge')
