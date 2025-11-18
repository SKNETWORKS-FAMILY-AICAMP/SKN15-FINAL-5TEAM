"""add_created_at_to_dialogues

Revision ID: 35877ea00244
Revises: 882113afa8e2
Create Date: 2025-11-13 09:43:02.721536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35877ea00244'
down_revision = '882113afa8e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add created_at column to conversation.dialogues table
    """
    # Add created_at column
    # op.add_column(
    #     'dialogues',
    #     sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    #     schema='conversation'
    # )

    # Copy timestamp to created_at for existing rows
    op.execute("""
        UPDATE conversation.dialogues
        SET created_at = timestamp
        WHERE created_at IS NULL
    """)

    # Make created_at NOT NULL
    op.alter_column(
        'dialogues',
        'created_at',
        nullable=False,
        schema='conversation'
    )


def downgrade() -> None:
    """
    Remove created_at column from conversation.dialogues table
    """
    op.drop_column('dialogues', 'created_at', schema='conversation')
