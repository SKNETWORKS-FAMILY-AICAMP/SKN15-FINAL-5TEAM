"""Add remaining 27 tables from backup

Revision ID: 7fc027c58381
Revises: 14260dbfb3e6
Create Date: 2025-11-10 01:16:35.048448

Adds all missing tables from tm_work backup:
- Logging tables (logs, error_logs, performance_metrics)
- Credits tables (user_credits, credit_transactions, xp_transactions)
- Progression tables (stage_progression, user_progression, user_scenario_progress, game_events, mission_records, rank_definitions)
- Image tables (image_assets, image_mapping_rules, scenario_stage_images, scenario_default_images, user_unlocked_images)
- Scenario tables (scenarios, scenario_statistics, scenario_views)
- Session tables (dialogues, session_snapshots, user_inputs)
- User tables (user_settings, user_equipment)
- Training tables (training_logs, user_feedback)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7fc027c58381'
down_revision = '14260dbfb3e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Logging tables (3)
    op.execute("""
    CREATE TABLE logs (
        id bigserial PRIMARY KEY,
        session_id uuid,
        log_level varchar(20) NOT NULL,
        stage_name varchar(100),
        agent_name varchar(100),
        message text NOT NULL,
        context_data jsonb,
        duration_ms real,
        timestamp timestamptz NOT NULL DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE error_logs (
        id bigserial PRIMARY KEY,
        session_id uuid,
        error_type varchar(100) NOT NULL,
        error_message text NOT NULL,
        stack_trace text,
        context_data jsonb,
        timestamp timestamptz NOT NULL DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE performance_metrics (
        id bigserial PRIMARY KEY,
        metric_name varchar(100) NOT NULL,
        metric_value real NOT NULL,
        metric_unit varchar(50),
        tags jsonb,
        timestamp timestamptz NOT NULL DEFAULT now()
    )
    """)

    # Credits tables (3)
    op.execute("""
    CREATE TABLE user_credits (
        user_id uuid PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        bubble_count integer NOT NULL DEFAULT 200 CHECK (bubble_count >= 0),
        total_purchased integer NOT NULL DEFAULT 200 CHECK (total_purchased >= 0),
        total_consumed integer NOT NULL DEFAULT 0 CHECK (total_consumed >= 0),
        last_updated timestamptz DEFAULT now(),
        created_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE credit_transactions (
        transaction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        amount integer NOT NULL,
        transaction_type varchar(50) NOT NULL CHECK (transaction_type IN ('purchase', 'consume', 'refund', 'bonus', 'initial')),
        balance_after integer NOT NULL,
        description text,
        created_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE xp_transactions (
        transaction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        xp_amount integer NOT NULL,
        xp_type varchar(50) NOT NULL CHECK (xp_type IN ('message', 'session_complete', 'scenario_complete', 'achievement', 'daily_bonus', 'event')),
        xp_balance_after integer NOT NULL CHECK (xp_balance_after >= 0),
        level_before integer,
        level_after integer,
        did_level_up boolean DEFAULT false,
        description text,
        metadata jsonb,
        created_at timestamptz DEFAULT now()
    )
    """)

    # Progression tables (6)
    op.execute("""
    CREATE TABLE stage_progression (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        stage_id varchar(255) NOT NULL,
        stage_order integer NOT NULL,
        entered_at timestamptz DEFAULT now(),
        exited_at timestamptz,
        dialogue_count integer DEFAULT 0,
        stage_turn_count integer DEFAULT 0
    )
    """)

    op.execute("""
    CREATE TABLE user_progression (
        user_id uuid PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        rank_code varchar(50) DEFAULT 'novice',
        experience_points integer DEFAULT 0 CHECK (experience_points >= 0),
        level integer DEFAULT 1 CHECK (level >= 1 AND level <= 99),
        total_messages integer DEFAULT 0 CHECK (total_messages >= 0),
        total_sessions integer DEFAULT 0 CHECK (total_sessions >= 0),
        total_play_minutes integer DEFAULT 0 CHECK (total_play_minutes >= 0),
        scenarios_completed integer DEFAULT 0 CHECK (scenarios_completed >= 0),
        achievements_count integer DEFAULT 0 CHECK (achievements_count >= 0),
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE user_scenario_progress (
        user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        scenario_id varchar(50) NOT NULL,
        has_started boolean DEFAULT false,
        has_completed boolean DEFAULT false,
        completion_percentage integer DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
        last_session_id varchar(100),
        last_played_at timestamptz,
        total_messages integer DEFAULT 0 CHECK (total_messages >= 0),
        total_play_time integer DEFAULT 0 CHECK (total_play_time >= 0),
        is_liked boolean DEFAULT false,
        liked_at timestamptz,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now(),
        PRIMARY KEY (user_id, scenario_id)
    )
    """)

    op.execute("""
    CREATE TABLE game_events (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        turn_number integer NOT NULL,
        event_type varchar(100) NOT NULL,
        event_data jsonb NOT NULL,
        timestamp timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE mission_records (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        mission_type varchar(100) NOT NULL,
        target_character varchar(255),
        attempt_count integer DEFAULT 0,
        success boolean,
        completed_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE rank_definitions (
        rank_code varchar(50) PRIMARY KEY,
        rank_name_ko varchar(100) NOT NULL,
        rank_name_en varchar(100),
        rank_name_ja varchar(100),
        min_xp integer NOT NULL,
        level_range_start integer NOT NULL,
        level_range_end integer NOT NULL,
        icon_emoji varchar(10),
        description_ko text,
        created_at timestamptz DEFAULT now()
    )
    """)

    # Image tables (5)
    op.execute("""
    CREATE TABLE image_assets (
        image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        image_path varchar(500) NOT NULL,
        image_name varchar(255) NOT NULL,
        image_type varchar(50) DEFAULT 'cutscene',
        scenario_id varchar(50),
        index_number integer,
        description text,
        tags text[],
        is_active boolean DEFAULT true,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE image_mapping_rules (
        rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        mapping_id uuid NOT NULL,
        image_id uuid NOT NULL,
        priority integer DEFAULT 50,
        turn_min integer DEFAULT 0,
        turn_max integer DEFAULT 999,
        dialogue_count_min integer DEFAULT 0,
        dialogue_count_max integer DEFAULT 999,
        required_flags text[],
        excluded_flags text[],
        description text,
        is_active boolean DEFAULT true,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE scenario_stage_images (
        mapping_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        scenario_id varchar(50) NOT NULL,
        stage_id varchar(100) NOT NULL,
        default_image_id uuid,
        stage_order integer,
        description text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE scenario_default_images (
        scenario_id varchar(50) PRIMARY KEY,
        default_image_id uuid,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE user_unlocked_images (
        unlock_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        image_id uuid NOT NULL,
        unlocked_at timestamptz DEFAULT now(),
        scenario_id varchar(50),
        session_id uuid,
        stage_id varchar(100),
        unlock_method varchar(50) DEFAULT 'story_progress'
    )
    """)

    # Scenario tables (3)
    op.execute("""
    CREATE TABLE scenarios (
        scenario_id varchar(50) PRIMARY KEY,
        title varchar(200) NOT NULL,
        description text,
        image_url varchar(500),
        thumbnail_url varchar(500),
        tags text[],
        card_size varchar(20) DEFAULT 'normal',
        route_path varchar(200),
        display_order integer DEFAULT 0,
        is_active boolean DEFAULT true,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE scenario_statistics (
        scenario_id varchar(50) PRIMARY KEY,
        total_likes integer DEFAULT 0 CHECK (total_likes >= 0),
        total_comments integer DEFAULT 0 CHECK (total_comments >= 0),
        total_views integer DEFAULT 0 CHECK (total_views >= 0),
        total_completions integer DEFAULT 0 CHECK (total_completions >= 0),
        total_sessions integer DEFAULT 0 CHECK (total_sessions >= 0),
        avg_session_duration integer DEFAULT 0 CHECK (avg_session_duration >= 0),
        last_updated timestamptz DEFAULT now(),
        created_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE scenario_views (
        view_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        scenario_id varchar(50),
        user_id uuid,
        ip_address inet,
        user_agent text,
        viewed_at timestamptz DEFAULT now()
    )
    """)

    # Session/Dialogue tables (3)
    op.execute("""
    CREATE TABLE dialogues (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        turn_number integer NOT NULL,
        speaker varchar(255) NOT NULL,
        content text NOT NULL,
        emotion varchar(100),
        emotion_intensity varchar(50),
        order_index integer,
        timestamp timestamptz DEFAULT now(),
        embedding vector(1536),
        mentioned_entity_ids integer[] DEFAULT '{}'
    )
    """)

    op.execute("""
    CREATE TABLE session_snapshots (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        turn_number integer NOT NULL,
        state_json jsonb NOT NULL,
        created_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE user_inputs (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
        turn_number integer NOT NULL,
        user_input text NOT NULL,
        timestamp timestamptz DEFAULT now()
    )
    """)

    # User tables (2)
    op.execute("""
    CREATE TABLE user_settings (
        user_id uuid PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        sound_enabled boolean DEFAULT true,
        bgm_volume integer DEFAULT 70 CHECK (bgm_volume >= 0 AND bgm_volume <= 100),
        sfx_volume integer DEFAULT 80 CHECK (sfx_volume >= 0 AND sfx_volume <= 100),
        auto_save boolean DEFAULT true,
        language varchar(10) DEFAULT 'ko',
        font_size varchar(20) DEFAULT 'medium' CHECK (font_size IN ('small', 'medium', 'large')),
        animation_speed varchar(20) DEFAULT 'normal' CHECK (animation_speed IN ('slow', 'normal', 'fast')),
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    op.execute("""
    CREATE TABLE user_equipment (
        user_id uuid PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        sword_status varchar(50) DEFAULT 'good' CHECK (sword_status IN ('excellent', 'good', 'fair', 'poor', 'broken')),
        uniform_status varchar(50) DEFAULT 'worn' CHECK (uniform_status IN ('pristine', 'worn', 'equipped', 'damaged', 'torn')),
        crow_status varchar(50) DEFAULT 'waiting' CHECK (crow_status IN ('waiting', 'active', 'resting', 'absent')),
        sword_type varchar(100),
        uniform_color varchar(50),
        crow_name varchar(100),
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    )
    """)

    # Training/Feedback tables (2)
    op.execute("""
    CREATE TABLE training_logs (
        id bigserial PRIMARY KEY,
        session_id uuid NOT NULL,
        turn_count integer NOT NULL,
        scenario_id varchar(50),
        current_stage varchar(100),
        agent_name varchar(50) NOT NULL,
        user_input text,
        context jsonb NOT NULL,
        model_output jsonb NOT NULL,
        latency_ms integer,
        token_count integer,
        llm_model varchar(100),
        outcome varchar(20),
        outcome_reason text,
        feedback_score double precision CHECK (feedback_score >= 0.0 AND feedback_score <= 1.0),
        created_at timestamptz DEFAULT CURRENT_TIMESTAMP,
        labeled_at timestamptz,
        is_error boolean DEFAULT false,
        error_message text,
        embedding vector(1536),
        mentioned_entity_ids integer[] DEFAULT '{}'
    )
    """)

    op.execute("""
    CREATE TABLE user_feedback (
        id bigserial PRIMARY KEY,
        training_log_id bigint,
        feedback_type varchar(50) NOT NULL,
        feedback_text text,
        user_id varchar(100),
        created_at timestamptz DEFAULT CURRENT_TIMESTAMP
    )
    """)


def downgrade() -> None:
    # Drop tables in reverse order to respect foreign key constraints
    op.execute("DROP TABLE IF EXISTS user_feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS training_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS user_equipment CASCADE")
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS user_inputs CASCADE")
    op.execute("DROP TABLE IF EXISTS session_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS dialogues CASCADE")
    op.execute("DROP TABLE IF EXISTS scenario_views CASCADE")
    op.execute("DROP TABLE IF EXISTS scenario_statistics CASCADE")
    op.execute("DROP TABLE IF EXISTS scenarios CASCADE")
    op.execute("DROP TABLE IF EXISTS user_unlocked_images CASCADE")
    op.execute("DROP TABLE IF EXISTS scenario_default_images CASCADE")
    op.execute("DROP TABLE IF EXISTS scenario_stage_images CASCADE")
    op.execute("DROP TABLE IF EXISTS image_mapping_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS image_assets CASCADE")
    op.execute("DROP TABLE IF EXISTS rank_definitions CASCADE")
    op.execute("DROP TABLE IF EXISTS mission_records CASCADE")
    op.execute("DROP TABLE IF EXISTS game_events CASCADE")
    op.execute("DROP TABLE IF EXISTS user_scenario_progress CASCADE")
    op.execute("DROP TABLE IF EXISTS user_progression CASCADE")
    op.execute("DROP TABLE IF EXISTS stage_progression CASCADE")
    op.execute("DROP TABLE IF EXISTS xp_transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS credit_transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS user_credits CASCADE")
    op.execute("DROP TABLE IF EXISTS performance_metrics CASCADE")
    op.execute("DROP TABLE IF EXISTS error_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS logs CASCADE")
