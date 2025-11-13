"""add_columns_to_user_inputs

Revision ID: 1445deaf4f1d
Revises: 35877ea00244
Create Date: 2025-11-13 09:44:25.619113

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1445deaf4f1d'
down_revision = '35877ea00244'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add user_id and created_at columns to conversation.user_inputs table
    """
    # Add user_id column (nullable first for existing data)
    op.add_column(
        'user_inputs',
        sa.Column('user_id', sa.UUID(), nullable=True),
        schema='conversation'
    )

    # Update user_id from sessions table for existing user_inputs
    op.execute("""
        UPDATE conversation.user_inputs ui
        SET user_id = s.user_id
        FROM conversation.sessions s
        WHERE ui.session_id = s.session_id
    """)

    # Add created_at column
    op.add_column(
        'user_inputs',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        schema='conversation'
    )

    # Copy timestamp to created_at for existing rows
    op.execute("""
        UPDATE conversation.user_inputs
        SET created_at = timestamp
        WHERE created_at IS NULL
    """)

    # Make created_at NOT NULL
    op.alter_column(
        'user_inputs',
        'created_at',
        nullable=False,
        schema='conversation'
    )

    # Add foreign key constraint for user_id
    op.create_foreign_key(
        'user_inputs_user_id_fkey',
        'user_inputs',
        'users',
        ['user_id'],
        ['user_id'],
        source_schema='conversation',
        referent_schema='auth',
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Remove user_id and created_at columns from conversation.user_inputs table
    """
    # Drop foreign key constraint
    op.drop_constraint('user_inputs_user_id_fkey', 'user_inputs', schema='conversation', type_='foreignkey')

    # Drop columns
    op.drop_column('user_inputs', 'created_at', schema='conversation')
    op.drop_column('user_inputs', 'user_id', schema='conversation')
