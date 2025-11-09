"""Schema consolidation: Move all tables from statedb/logdb to public schema

Revision ID: schema_consolidation
Revises: 467a802d571c
Create Date: 2025-11-09 23:00:00

This migration consolidates all tables from the statedb and logdb schemas
into the public schema for simplified database structure.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'schema_consolidation'
down_revision = '467a802d571c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Move all tables from statedb and logdb schemas to public schema.

    This migration is designed to run on a database that already has
    the statedb and logdb schemas with their respective tables.
    """

    # 1. Move statedb tables to public schema (37 tables)
    statedb_tables = [
        'sessions', 'user_inputs', 'dialogues', 'affinity_records',
        'stage_progression', 'game_events', 'mission_records',
        'session_snapshots', 'users', 'password_reset_tokens',
        'user_credits', 'credit_transactions', 'user_settings',
        'user_memories', 'rank_definitions', 'user_progression',
        'user_equipment', 'xp_transactions', 'scenarios',
        'scenario_statistics', 'user_scenario_progress',
        'scenario_views', 'scenario_comments', 'comment_likes',
        'scenario_likes', 'image_assets', 'scenario_stage_images',
        'image_mapping_rules', 'scenario_default_images',
        'user_unlocked_images', 'user_character_affinity',
        'entities', 'entity_relationships', 'entity_mentions'
    ]

    for table in statedb_tables:
        op.execute(f"ALTER TABLE IF EXISTS statedb.{table} SET SCHEMA public")

    # 2. Move logdb tables to public schema (3 tables)
    logdb_tables = ['logs', 'error_logs', 'performance_metrics']
    for table in logdb_tables:
        op.execute(f"ALTER TABLE IF EXISTS logdb.{table} SET SCHEMA public")

    # 3. Move functions to public schema
    functions = [
        'get_scenario_comments', 'get_comment_replies',
        'upsert_character_affinity', 'update_affinity_level',
        'get_top_affinity_characters', 'get_best_image_for_stage',
        'get_user_unlocked_images'
    ]
    for func in functions:
        # Functions may have different signatures, handle gracefully
        op.execute(f"""
            DO $$
            DECLARE
                func_signature text;
            BEGIN
                FOR func_signature IN
                    SELECT oid::regprocedure::text
                    FROM pg_proc
                    WHERE proname = '{func}'
                    AND pronamespace = 'statedb'::regnamespace
                LOOP
                    EXECUTE 'ALTER FUNCTION ' || func_signature || ' SET SCHEMA public';
                END LOOP;
            END $$;
        """)

    # 4. Move views to public schema
    views = ['v_scenario_cards', 'v_user_progression_summary']
    for view in views:
        op.execute(f"ALTER VIEW IF EXISTS statedb.{view} SET SCHEMA public")

    # 5. Drop empty schemas
    op.execute("DROP SCHEMA IF EXISTS statedb CASCADE")
    op.execute("DROP SCHEMA IF EXISTS logdb CASCADE")


def downgrade() -> None:
    """
    Rollback: Recreate schemas and move tables back.

    This is a complex downgrade that recreates the schema structure.
    """

    # 1. Recreate schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS statedb")
    op.execute("CREATE SCHEMA IF NOT EXISTS logdb")

    # 2. Move tables back to statedb
    statedb_tables = [
        'sessions', 'user_inputs', 'dialogues', 'affinity_records',
        'stage_progression', 'game_events', 'mission_records',
        'session_snapshots', 'users', 'password_reset_tokens',
        'user_credits', 'credit_transactions', 'user_settings',
        'user_memories', 'rank_definitions', 'user_progression',
        'user_equipment', 'xp_transactions', 'scenarios',
        'scenario_statistics', 'user_scenario_progress',
        'scenario_views', 'scenario_comments', 'comment_likes',
        'scenario_likes', 'image_assets', 'scenario_stage_images',
        'image_mapping_rules', 'scenario_default_images',
        'user_unlocked_images', 'user_character_affinity',
        'entities', 'entity_relationships', 'entity_mentions'
    ]

    for table in statedb_tables:
        op.execute(f"ALTER TABLE IF EXISTS public.{table} SET SCHEMA statedb")

    # 3. Move tables back to logdb
    logdb_tables = ['logs', 'error_logs', 'performance_metrics']
    for table in logdb_tables:
        op.execute(f"ALTER TABLE IF EXISTS public.{table} SET SCHEMA logdb")

    # 4. Move functions back to statedb
    functions = [
        'get_scenario_comments', 'get_comment_replies',
        'upsert_character_affinity', 'update_affinity_level',
        'get_top_affinity_characters', 'get_best_image_for_stage',
        'get_user_unlocked_images'
    ]
    for func in functions:
        op.execute(f"""
            DO $$
            DECLARE
                func_signature text;
            BEGIN
                FOR func_signature IN
                    SELECT oid::regprocedure::text
                    FROM pg_proc
                    WHERE proname = '{func}'
                    AND pronamespace = 'public'::regnamespace
                LOOP
                    EXECUTE 'ALTER FUNCTION ' || func_signature || ' SET SCHEMA statedb';
                END LOOP;
            END $$;
        """)

    # 5. Move views back to statedb
    views = ['v_scenario_cards', 'v_user_progression_summary']
    for view in views:
        op.execute(f"ALTER VIEW IF EXISTS public.{view} SET SCHEMA statedb")
