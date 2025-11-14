"""sync database schema with models

Revision ID: 8e2a6d4bac3b
Revises: grant_initial_credits
Create Date: 2025-11-13 07:24:03.689609

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8e2a6d4bac3b'
down_revision = 'grant_initial_credits'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    This migration marks the database as synchronized with models.
    All tables already exist in the database, so no operations are performed.

    Database state at this point:
    - All auth.* tables exist
    - All content.* tables exist
    - All conversation.* tables exist
    - All gallery.* tables exist (newly created)
    - All knowledge.* tables exist
    - All ml.* tables exist
    - All observability.* tables exist
    - All progression.* tables exist
    - Legacy tables in public schema exist (image_assets, etc.)
    """
    pass


def downgrade() -> None:
    """
    No downgrade operations as this is a sync migration.
    """
    pass
