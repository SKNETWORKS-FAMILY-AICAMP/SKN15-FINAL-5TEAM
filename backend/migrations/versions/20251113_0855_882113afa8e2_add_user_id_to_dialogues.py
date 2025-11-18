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
    # NOTE: All operations in this migration are skipped because they are
    # already handled by the initial SQL scripts (e.g., 007_dialogues_migration.sql).
    # Attempting to run them again causes errors like 'DuplicateColumn'.
    pass


def downgrade() -> None:
    # NOTE: Correspondingly, the downgrade operations are also skipped.
    pass

