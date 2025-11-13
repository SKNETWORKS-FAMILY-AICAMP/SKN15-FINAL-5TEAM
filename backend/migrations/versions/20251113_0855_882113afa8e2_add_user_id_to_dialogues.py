"""add_user_id_to_dialogues

Revision ID: 882113afa8e2
Revises: 8e2a6d4bac3b
Create Date: 2025-11-13 08:55:40.868193

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '882113afa8e2'
down_revision = '8e2a6d4bac3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add user_id column to conversation.dialogues table
    """
    # Add user_id column (nullable first for existing data)
    op.add_column(
        'dialogues',
        sa.Column('user_id', sa.UUID(), nullable=True),
        schema='conversation'
    )

    # Update user_id from sessions table for existing dialogues
    op.execute("""
        UPDATE conversation.dialogues d
        SET user_id = s.user_id
        FROM conversation.sessions s
        WHERE d.session_id = s.session_id
    """)

    # Make user_id NOT NULL after data migration
    op.alter_column(
        'dialogues',
        'user_id',
        nullable=False,
        schema='conversation'
    )

    # Add missing columns from the model
    op.add_column(
        'dialogues',
        sa.Column('scenario_id', sa.String(255), nullable=True),
        schema='conversation'
    )

    op.add_column(
        'dialogues',
        sa.Column('stage_tag', sa.String(100), nullable=True),
        schema='conversation'
    )

    op.add_column(
        'dialogues',
        sa.Column('affinity_delta', sa.Float(), nullable=True, server_default='0.0'),
        schema='conversation'
    )

    op.add_column(
        'dialogues',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        schema='conversation'
    )

    # Add created_at column and copy data from timestamp
    op.add_column(
        'dialogues',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        schema='conversation'
    )

    # Copy timestamp to created_at for existing rows
    op.execute("""
        UPDATE conversation.dialogues
        SET created_at = timestamp
        WHERE created_at IS NULL
    """)

    # Update scenario_id from sessions table
    op.execute("""
        UPDATE conversation.dialogues d
        SET scenario_id = s.scenario_id
        FROM conversation.sessions s
        WHERE d.session_id = s.session_id
    """)

    # Make scenario_id NOT NULL after data migration
    op.alter_column(
        'dialogues',
        'scenario_id',
        nullable=False,
        schema='conversation'
    )

    # Create indexes for new columns
    op.create_index(
        'idx_session_user',
        'dialogues',
        ['session_id', 'user_id'],
        schema='conversation'
    )

    op.create_index(
        'idx_user_created',
        'dialogues',
        ['user_id', 'timestamp'],
        schema='conversation'
    )

    # Recreate idx_session_turn index with correct columns
    op.drop_index('idx_dialogues_turn_number', table_name='dialogues', schema='conversation')
    op.create_index(
        'idx_session_turn',
        'dialogues',
        ['session_id', 'turn_number'],
        schema='conversation'
    )


def downgrade() -> None:
    """
    Remove user_id and other added columns from conversation.dialogues table
    """
    # Drop indexes
    op.drop_index('idx_user_created', table_name='dialogues', schema='conversation')
    op.drop_index('idx_session_user', table_name='dialogues', schema='conversation')
    op.drop_index('idx_session_turn', table_name='dialogues', schema='conversation')

    # Recreate original index
    op.create_index(
        'idx_dialogues_turn_number',
        'dialogues',
        ['session_id', 'turn_number'],
        schema='conversation'
    )

    # Drop columns
    op.drop_column('dialogues', 'created_at', schema='conversation')
    op.drop_column('dialogues', 'updated_at', schema='conversation')
    op.drop_column('dialogues', 'affinity_delta', schema='conversation')
    op.drop_column('dialogues', 'stage_tag', schema='conversation')
    op.drop_column('dialogues', 'scenario_id', schema='conversation')
    op.drop_column('dialogues', 'user_id', schema='conversation')
