"""create_scenario_buffers

Revision ID: 20251117_0003
Revises: 20251117_0002
Create Date: 2025-11-17 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '20251117_0003'
down_revision = '20251117_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create scenario_buffers table in knowledge schema
    목적: 시나리오 진행 정보 임시 저장 (시나리오 완료 시 삭제)
    """
    op.create_table(
        'scenario_buffers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', sa.String(100), nullable=False),

        # Buffer 내용
        sa.Column('buffer_summary', sa.Text(), nullable=True),
        sa.Column('progress_data', JSONB, nullable=True),  # 선택지, 진행 상황, 플래그

        # 메타데이터
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'scenario_id'),
        schema='knowledge'
    )

    # Index for fast lookup
    op.create_index(
        'idx_scenario_buffer_user',
        'scenario_buffers',
        ['user_id', 'scenario_id'],
        schema='knowledge'
    )


def downgrade() -> None:
    """
    Drop scenario_buffers table
    """
    op.drop_index('idx_scenario_buffer_user', table_name='scenario_buffers', schema='knowledge')
    op.drop_table('scenario_buffers', schema='knowledge')
