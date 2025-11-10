-- Table: user_credits (from statedb)
CREATE TABLE user_credits (
    user_id uuid NOT NULL,
    bubble_count integer DEFAULT 100 NOT NULL,
    total_purchased integer DEFAULT 100 NOT NULL,
    total_consumed integer DEFAULT 0 NOT NULL,
    last_updated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT positive_bubble_count CHECK ((bubble_count >= 0)),
    CONSTRAINT positive_totals CHECK (((total_purchased >= 0) AND (total_consumed >= 0)))
);

-- Table: credit_transactions (from statedb)
CREATE TABLE credit_transactions (
    transaction_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    amount integer NOT NULL,
    transaction_type character varying(50) NOT NULL,
    balance_after integer NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_transaction_type CHECK (((transaction_type)::text = ANY ((ARRAY['purchase'::character varying, 'consume'::character varying, 'refund'::character varying, 'bonus'::character varying, 'initial'::character varying])::text[])))
);

-- Table: xp_transactions (from statedb)
CREATE TABLE xp_transactions (
    transaction_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    xp_amount integer NOT NULL,
    xp_type character varying(50) NOT NULL,
    xp_balance_after integer NOT NULL,
    level_before integer,
    level_after integer,
    did_level_up boolean DEFAULT false,
    description text,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT xp_transactions_xp_balance_after_check CHECK ((xp_balance_after >= 0)),
    CONSTRAINT xp_transactions_xp_type_check CHECK (((xp_type)::text = ANY ((ARRAY['message'::character varying, 'session_complete'::character varying, 'scenario_complete'::character varying, 'achievement'::character varying, 'daily_bonus'::character varying, 'event'::character varying])::text[])))
);

-- Table: stage_progression (from statedb)
CREATE TABLE stage_progression (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    stage_id character varying(255) NOT NULL,
    stage_order integer NOT NULL,
    entered_at timestamp without time zone DEFAULT now(),
    exited_at timestamp without time zone,
    dialogue_count integer DEFAULT 0,
    stage_turn_count integer DEFAULT 0
);

-- Table: user_progression (from statedb)
CREATE TABLE user_progression (
    user_id uuid NOT NULL,
    rank_code character varying(50) DEFAULT 'novice'::character varying,
    experience_points integer DEFAULT 0,
    level integer DEFAULT 1,
    total_messages integer DEFAULT 0,
    total_sessions integer DEFAULT 0,
    total_play_minutes integer DEFAULT 0,
    scenarios_completed integer DEFAULT 0,
    achievements_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT user_progression_achievements_count_check CHECK ((achievements_count >= 0)),
    CONSTRAINT user_progression_experience_points_check CHECK ((experience_points >= 0)),
    CONSTRAINT user_progression_level_check CHECK (((level >= 1) AND (level <= 99))),
    CONSTRAINT user_progression_scenarios_completed_check CHECK ((scenarios_completed >= 0)),
    CONSTRAINT user_progression_total_messages_check CHECK ((total_messages >= 0)),
    CONSTRAINT user_progression_total_play_minutes_check CHECK ((total_play_minutes >= 0)),
    CONSTRAINT user_progression_total_sessions_check CHECK ((total_sessions >= 0))
);

-- Table: user_scenario_progress (from statedb)
CREATE TABLE user_scenario_progress (
    user_id uuid NOT NULL,
    scenario_id character varying(50) NOT NULL,
    has_started boolean DEFAULT false,
    has_completed boolean DEFAULT false,
    completion_percentage integer DEFAULT 0,
    last_session_id character varying(100),
    last_played_at timestamp without time zone,
    total_messages integer DEFAULT 0,
    total_play_time integer DEFAULT 0,
    is_liked boolean DEFAULT false,
    liked_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT user_scenario_progress_completion_percentage_check CHECK (((completion_percentage >= 0) AND (completion_percentage <= 100))),
    CONSTRAINT user_scenario_progress_total_messages_check CHECK ((total_messages >= 0)),
    CONSTRAINT user_scenario_progress_total_play_time_check CHECK ((total_play_time >= 0))
);

-- Table: game_events (from statedb)
CREATE TABLE game_events (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    event_type character varying(100) NOT NULL,
    event_data jsonb NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now()
);

-- Table: mission_records (from statedb)
CREATE TABLE mission_records (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    mission_type character varying(100) NOT NULL,
    target_character character varying(255),
    attempt_count integer DEFAULT 0,
    success boolean,
    completed_at timestamp without time zone DEFAULT now()
);

-- Table: rank_definitions (from statedb)
CREATE TABLE rank_definitions (
    rank_code character varying(50) NOT NULL,
    rank_name_ko character varying(100) NOT NULL,
    rank_name_en character varying(100),
    rank_name_ja character varying(100),
    min_xp integer NOT NULL,
    level_range_start integer NOT NULL,
    level_range_end integer NOT NULL,
    icon_emoji character varying(10),
    description_ko text,
    created_at timestamp without time zone DEFAULT now()
);

-- Table: image_assets (from statedb)
CREATE TABLE image_assets (
    image_id uuid DEFAULT gen_random_uuid() NOT NULL,
    image_path character varying(500) NOT NULL,
    image_name character varying(255) NOT NULL,
    image_type character varying(50) DEFAULT 'cutscene'::character varying,
    scenario_id character varying(50),
    index_number integer,
    description text,
    tags text[],
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: image_mapping_rules (from statedb)
CREATE TABLE image_mapping_rules (
    rule_id uuid DEFAULT gen_random_uuid() NOT NULL,
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
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: scenario_stage_images (from statedb)
CREATE TABLE scenario_stage_images (
    mapping_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id character varying(50) NOT NULL,
    stage_id character varying(100) NOT NULL,
    default_image_id uuid,
    stage_order integer,
    description text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: scenario_default_images (from statedb)
CREATE TABLE scenario_default_images (
    scenario_id character varying(50) NOT NULL,
    default_image_id uuid,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: user_unlocked_images (from statedb)
CREATE TABLE user_unlocked_images (
    unlock_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    image_id uuid NOT NULL,
    unlocked_at timestamp without time zone DEFAULT now(),
    scenario_id character varying(50),
    session_id uuid,
    stage_id character varying(100),
    unlock_method character varying(50) DEFAULT 'story_progress'::character varying
);

-- Table: scenario_statistics (from statedb)
CREATE TABLE scenario_statistics (
    scenario_id character varying(50) NOT NULL,
    total_likes integer DEFAULT 0,
    total_comments integer DEFAULT 0,
    total_views integer DEFAULT 0,
    total_completions integer DEFAULT 0,
    total_sessions integer DEFAULT 0,
    avg_session_duration integer DEFAULT 0,
    last_updated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT scenario_statistics_avg_session_duration_check CHECK ((avg_session_duration >= 0)),
    CONSTRAINT scenario_statistics_total_comments_check CHECK ((total_comments >= 0)),
    CONSTRAINT scenario_statistics_total_completions_check CHECK ((total_completions >= 0)),
    CONSTRAINT scenario_statistics_total_likes_check CHECK ((total_likes >= 0)),
    CONSTRAINT scenario_statistics_total_sessions_check CHECK ((total_sessions >= 0)),
    CONSTRAINT scenario_statistics_total_views_check CHECK ((total_views >= 0))
);

-- Table: scenario_views (from statedb)
CREATE TABLE scenario_views (
    view_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id character varying(50),
    user_id uuid,
    ip_address inet,
    user_agent text,
    viewed_at timestamp without time zone DEFAULT now()
);

-- Table: scenarios (from statedb)
CREATE TABLE scenarios (
    scenario_id character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    image_url character varying(500),
    thumbnail_url character varying(500),
    tags text[],
    card_size character varying(20) DEFAULT 'normal'::character varying,
    route_path character varying(200),
    display_order integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);

-- Table: dialogues (from statedb)
CREATE TABLE dialogues (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    speaker character varying(255) NOT NULL,
    content text NOT NULL,
    emotion character varying(100),
    emotion_intensity character varying(50),
    order_index integer,
    "timestamp" timestamp without time zone DEFAULT now(),
    embedding vector(1536),
    mentioned_entity_ids integer[] DEFAULT '{}'::integer[]
);

-- Table: session_snapshots (from statedb)
CREATE TABLE session_snapshots (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    state_json jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);

-- Table: user_inputs (from statedb)
CREATE TABLE user_inputs (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    user_input text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now()
);

-- Table: user_settings (from statedb)
CREATE TABLE user_settings (
    user_id uuid NOT NULL,
    sound_enabled boolean DEFAULT true,
    bgm_volume integer DEFAULT 70,
    sfx_volume integer DEFAULT 80,
    auto_save boolean DEFAULT true,
    language character varying(10) DEFAULT 'ko'::character varying,
    font_size character varying(20) DEFAULT 'medium'::character varying,
    animation_speed character varying(20) DEFAULT 'normal'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT user_settings_animation_speed_check CHECK (((animation_speed)::text = ANY ((ARRAY['slow'::character varying, 'normal'::character varying, 'fast'::character varying])::text[]))),
    CONSTRAINT user_settings_bgm_volume_check CHECK (((bgm_volume >= 0) AND (bgm_volume <= 100))),
    CONSTRAINT user_settings_font_size_check CHECK (((font_size)::text = ANY ((ARRAY['small'::character varying, 'medium'::character varying, 'large'::character varying])::text[]))),
    CONSTRAINT user_settings_sfx_volume_check CHECK (((sfx_volume >= 0) AND (sfx_volume <= 100)))
);

-- Table: user_equipment (from statedb)
CREATE TABLE user_equipment (
    user_id uuid NOT NULL,
    sword_status character varying(50) DEFAULT 'good'::character varying,
    uniform_status character varying(50) DEFAULT 'worn'::character varying,
    crow_status character varying(50) DEFAULT 'waiting'::character varying,
    sword_type character varying(100),
    uniform_color character varying(50),
    crow_name character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT user_equipment_crow_status_check CHECK (((crow_status)::text = ANY ((ARRAY['waiting'::character varying, 'active'::character varying, 'resting'::character varying, 'absent'::character varying])::text[]))),
    CONSTRAINT user_equipment_sword_status_check CHECK (((sword_status)::text = ANY ((ARRAY['excellent'::character varying, 'good'::character varying, 'fair'::character varying, 'poor'::character varying, 'broken'::character varying])::text[]))),
    CONSTRAINT user_equipment_uniform_status_check CHECK (((uniform_status)::text = ANY ((ARRAY['pristine'::character varying, 'worn'::character varying, 'equipped'::character varying, 'damaged'::character varying, 'torn'::character varying])::text[])))
);

-- Table: training_logs (from public)
CREATE TABLE training_logs (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_count integer NOT NULL,
    scenario_id character varying(50),
    current_stage character varying(100),
    agent_name character varying(50) NOT NULL,
    user_input text,
    context jsonb NOT NULL,
    model_output jsonb NOT NULL,
    latency_ms integer,
    token_count integer,
    llm_model character varying(100),
    outcome character varying(20),
    outcome_reason text,
    feedback_score double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    labeled_at timestamp without time zone,
    is_error boolean DEFAULT false,
    error_message text,
    embedding vector(1536),
    mentioned_entity_ids integer[] DEFAULT '{}'::integer[],
    CONSTRAINT training_logs_feedback_score_check CHECK (((feedback_score >= (0.0)::double precision) AND (feedback_score <= (1.0)::double precision)))
);

-- Table: user_feedback (from public)
CREATE TABLE user_feedback (
    id bigint NOT NULL,
    training_log_id bigint,
    feedback_type character varying(50) NOT NULL,
    feedback_text text,
    user_id character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

