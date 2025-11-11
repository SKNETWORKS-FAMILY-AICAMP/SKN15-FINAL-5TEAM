"""add_scenario_image_tables

Revision ID: 75a366f1b383
Revises: 7fc027c58381
Create Date: 2025-11-11 14:22:00.423620

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '75a366f1b383'
down_revision = '7fc027c58381'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scenario_image_mappings table
    op.create_table(
        'scenario_image_mappings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('scenario_id', sa.String(50), nullable=False),
        sa.Column('mapping_type', sa.String(50), nullable=False),  # 'cutscene', 'llm_driven', etc.
        sa.Column('priority', sa.Integer, server_default='50'),
        sa.Column('stage', sa.String(50)),
        sa.Column('stage_list', postgresql.JSONB),  # For multiple stages
        sa.Column('turn_min', sa.Integer),
        sa.Column('turn_max', sa.Integer),
        sa.Column('dialogue_count_min', sa.Integer),
        sa.Column('dialogue_count_max', sa.Integer),
        sa.Column('flags', postgresql.JSONB),  # Store as JSONB array
        sa.Column('image', sa.String(500), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        schema='content'
    )

    # Create foreign key for scenario_image_mappings.scenario_id
    op.create_foreign_key(
        'fk_scenario_image_mappings_scenario_id',
        'scenario_image_mappings', 'scenarios',
        ['scenario_id'], ['scenario_id'],
        source_schema='content',
        referent_schema='content',
        ondelete='CASCADE'
    )

    # Create index on scenario_image_mappings
    op.create_index(
        'idx_scenario_image_mappings_scenario',
        'scenario_image_mappings',
        ['scenario_id', 'priority'],
        schema='content'
    )

    # Create scenario_image_metadata table
    op.create_table(
        'scenario_image_metadata',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('scenario_id', sa.String(50), nullable=False),
        sa.Column('image_index', sa.String(10)),
        sa.Column('image_id', sa.String(100)),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('tags', postgresql.JSONB),
        sa.Column('keywords', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        schema='content'
    )

    # Create foreign key for scenario_image_metadata.scenario_id
    op.create_foreign_key(
        'fk_scenario_image_metadata_scenario_id',
        'scenario_image_metadata', 'scenarios',
        ['scenario_id'], ['scenario_id'],
        source_schema='content',
        referent_schema='content',
        ondelete='CASCADE'
    )

    # Create index on scenario_image_metadata
    op.create_index(
        'idx_scenario_image_metadata_scenario',
        'scenario_image_metadata',
        ['scenario_id', 'image_index'],
        schema='content'
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('scenario_image_metadata', schema='content')
    op.drop_table('scenario_image_mappings', schema='content')
