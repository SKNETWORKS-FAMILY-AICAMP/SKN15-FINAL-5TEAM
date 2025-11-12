--
-- PostgreSQL database dump
--

-- Dumped from database version 15.4 (Debian 15.4-2.pgdg120+1)
-- Dumped by pg_dump version 15.4 (Debian 15.4-2.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Install pgvector extension (required for embedding columns)
--
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS auth;


ALTER SCHEMA auth OWNER TO kime;

--
-- Name: SCHEMA auth; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA auth IS 'User authentication, accounts, and credits';


--
-- Name: content; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS content;


ALTER SCHEMA content OWNER TO kime;

--
-- Name: SCHEMA content; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA content IS 'Scenarios, ranks, and game content metadata';


--
-- Name: conversation; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS conversation;


ALTER SCHEMA conversation OWNER TO kime;

--
-- Name: SCHEMA conversation; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA conversation IS 'Chat sessions, dialogues, and user inputs';


--
-- Name: knowledge; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS knowledge;


ALTER SCHEMA knowledge OWNER TO kime;

--
-- Name: SCHEMA knowledge; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA knowledge IS 'Graph RAG: entities, relationships, and memories';


--
-- Name: ml; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS ml;


ALTER SCHEMA ml OWNER TO kime;

--
-- Name: SCHEMA ml; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA ml IS 'AI training logs, feedback, and model evaluations';


--
-- Name: observability; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS observability;


ALTER SCHEMA observability OWNER TO kime;

--
-- Name: SCHEMA observability; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA observability IS 'Logs, errors, and performance metrics';


--
-- Name: progression; Type: SCHEMA; Schema: -; Owner: kime
--

CREATE SCHEMA IF NOT EXISTS progression;


ALTER SCHEMA progression OWNER TO kime;

--
-- Name: SCHEMA progression; Type: COMMENT; Schema: -; Owner: kime
--

COMMENT ON SCHEMA progression IS 'User progress, equipment, missions, and gameplay data';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: credit_transactions; Type: TABLE; Schema: auth; Owner: kime
--

CREATE TABLE auth.credit_transactions (
    transaction_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    amount integer NOT NULL,
    transaction_type character varying(50) NOT NULL,
    balance_after integer NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_transaction_type CHECK (((transaction_type)::text = ANY ((ARRAY['purchase'::character varying, 'consume'::character varying, 'refund'::character varying, 'bonus'::character varying, 'initial'::character varying])::text[])))
);


ALTER TABLE auth.credit_transactions OWNER TO kime;

--
-- Name: TABLE credit_transactions; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON TABLE auth.credit_transactions IS '크레딧 트랜잭션 히스토리';


--
-- Name: COLUMN credit_transactions.transaction_id; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.transaction_id IS '트랜잭션 고유 ID';


--
-- Name: COLUMN credit_transactions.user_id; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.user_id IS '사용자 ID';


--
-- Name: COLUMN credit_transactions.amount; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.amount IS '변경 금액 (양수: 추가, 음수: 차감)';


--
-- Name: COLUMN credit_transactions.transaction_type; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.transaction_type IS '트랜잭션 유형';


--
-- Name: COLUMN credit_transactions.balance_after; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.balance_after IS '트랜잭션 후 잔액';


--
-- Name: COLUMN credit_transactions.description; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.credit_transactions.description IS '트랜잭션 설명';


--
-- Name: password_reset_tokens; Type: TABLE; Schema: auth; Owner: kime
--

CREATE TABLE auth.password_reset_tokens (
    token_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE auth.password_reset_tokens OWNER TO kime;

--
-- Name: TABLE password_reset_tokens; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON TABLE auth.password_reset_tokens IS '비밀번호 재설정 토큰 저장';


--
-- Name: COLUMN password_reset_tokens.token; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.password_reset_tokens.token IS '재설정 토큰 (UUID 또는 랜덤 문자열)';


--
-- Name: COLUMN password_reset_tokens.expires_at; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.password_reset_tokens.expires_at IS '토큰 만료 시간 (보통 1시간)';


--
-- Name: COLUMN password_reset_tokens.used; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.password_reset_tokens.used IS '토큰 사용 여부';


--
-- Name: user_credits; Type: TABLE; Schema: auth; Owner: kime
--

CREATE TABLE auth.user_credits (
    user_id uuid NOT NULL,
    bubble_count integer DEFAULT 100 NOT NULL,
    total_purchased integer DEFAULT 100 NOT NULL,
    total_consumed integer DEFAULT 0 NOT NULL,
    last_updated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT positive_bubble_count CHECK ((bubble_count >= 0)),
    CONSTRAINT positive_totals CHECK (((total_purchased >= 0) AND (total_consumed >= 0)))
);


ALTER TABLE auth.user_credits OWNER TO kime;

--
-- Name: TABLE user_credits; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON TABLE auth.user_credits IS '사용자 크레딧(버블) 정보';


--
-- Name: COLUMN user_credits.user_id; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.user_credits.user_id IS '사용자 ID (외래키)';


--
-- Name: COLUMN user_credits.bubble_count; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.user_credits.bubble_count IS '현재 보유 버블 수';


--
-- Name: COLUMN user_credits.total_purchased; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.user_credits.total_purchased IS '총 구매한 버블 수';


--
-- Name: COLUMN user_credits.total_consumed; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.user_credits.total_consumed IS '총 소비한 버블 수';


--
-- Name: COLUMN user_credits.last_updated; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.user_credits.last_updated IS '마지막 업데이트 시간';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: kime
--

CREATE TABLE auth.users (
    user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(255) NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    provider character varying(50) DEFAULT 'email'::character varying,
    display_name character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    last_login timestamp without time zone,
    is_active boolean DEFAULT true,
    is_verified boolean DEFAULT false,
    role character varying(50) DEFAULT 'user'::character varying,
    total_sessions integer DEFAULT 0,
    total_bubbles integer DEFAULT 0
);


ALTER TABLE auth.users OWNER TO kime;

--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON TABLE auth.users IS '사용자 계정 정보';


--
-- Name: COLUMN users.user_id; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.user_id IS '사용자 고유 ID';


--
-- Name: COLUMN users.username; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.username IS '사용자명 (로그인용, 고유)';


--
-- Name: COLUMN users.email; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.email IS '이메일 (소셜 로그인 시 사용, NULL 가능)';


--
-- Name: COLUMN users.password_hash; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.password_hash IS '비밀번호 해시 (bcrypt)';


--
-- Name: COLUMN users.provider; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.provider IS '인증 제공자 (email, google, kakao 등)';


--
-- Name: COLUMN users.display_name; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.display_name IS '표시 이름';

COMMENT ON COLUMN auth.users.is_active IS '계정 활성화 여부';

COMMENT ON COLUMN auth.users.is_verified IS '이메일 인증 완료 여부';

COMMENT ON COLUMN auth.users.role IS '사용자 역할 (user, admin, moderator)';

COMMENT ON COLUMN auth.users.total_sessions IS '총 세션 수 (비정규화)';

COMMENT ON COLUMN auth.users.total_bubbles IS '총 획득 버블 수 (비정규화)';


--
-- Name: COLUMN users.last_login; Type: COMMENT; Schema: auth; Owner: kime
--

COMMENT ON COLUMN auth.users.last_login IS '마지막 로그인 시간';


--
-- Name: beat_goals; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.beat_goals (
    id integer NOT NULL,
    beat_id character varying(100),
    goal_text text NOT NULL,
    speaker_hints jsonb,
    fx character varying(100),
    display_order integer DEFAULT 0
);


ALTER TABLE content.beat_goals OWNER TO kime;

--
-- Name: beat_goals_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.beat_goals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.beat_goals_id_seq OWNER TO kime;

--
-- Name: beat_goals_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.beat_goals_id_seq OWNED BY content.beat_goals.id;


--
-- Name: character_aliases; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_aliases (
    id integer NOT NULL,
    character_id character varying(50),
    alias character varying(255) NOT NULL
);


ALTER TABLE content.character_aliases OWNER TO kime;

--
-- Name: character_aliases_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_aliases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_aliases_id_seq OWNER TO kime;

--
-- Name: character_aliases_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_aliases_id_seq OWNED BY content.character_aliases.id;


--
-- Name: character_core_values; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_core_values (
    id integer NOT NULL,
    character_id character varying(50),
    value_text text NOT NULL,
    display_order integer DEFAULT 0
);


ALTER TABLE content.character_core_values OWNER TO kime;

--
-- Name: character_core_values_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_core_values_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_core_values_id_seq OWNER TO kime;

--
-- Name: character_core_values_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_core_values_id_seq OWNED BY content.character_core_values.id;


--
-- Name: character_emotional_triggers; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_emotional_triggers (
    id integer NOT NULL,
    character_id character varying(50),
    emotion_type character varying(50) NOT NULL,
    trigger_text text NOT NULL,
    display_order integer DEFAULT 0
);


ALTER TABLE content.character_emotional_triggers OWNER TO kime;

--
-- Name: character_emotional_triggers_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_emotional_triggers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_emotional_triggers_id_seq OWNER TO kime;

--
-- Name: character_emotional_triggers_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_emotional_triggers_id_seq OWNED BY content.character_emotional_triggers.id;


--
-- Name: character_intent_rules; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_intent_rules (
    id integer NOT NULL,
    character_id character varying(50),
    rule_category character varying(50) NOT NULL,
    rule_type character varying(100) NOT NULL,
    rule_value jsonb NOT NULL
);


ALTER TABLE content.character_intent_rules OWNER TO kime;

--
-- Name: character_intent_rules_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_intent_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_intent_rules_id_seq OWNER TO kime;

--
-- Name: character_intent_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_intent_rules_id_seq OWNED BY content.character_intent_rules.id;


--
-- Name: character_quotes; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_quotes (
    id integer NOT NULL,
    character_id character varying(50),
    quote_text text NOT NULL,
    display_order integer DEFAULT 0
);


ALTER TABLE content.character_quotes OWNER TO kime;

--
-- Name: character_quotes_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_quotes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_quotes_id_seq OWNER TO kime;

--
-- Name: character_quotes_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_quotes_id_seq OWNED BY content.character_quotes.id;


--
-- Name: character_relationships; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_relationships (
    id integer NOT NULL,
    scenario_id character varying(50),
    character_id character varying(50),
    target_character_id character varying(50),
    relationship_type character varying(50) NOT NULL,
    description text
);


ALTER TABLE content.character_relationships OWNER TO kime;

--
-- Name: character_relationships_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_relationships_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_relationships_id_seq OWNER TO kime;

--
-- Name: character_relationships_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_relationships_id_seq OWNED BY content.character_relationships.id;


--
-- Name: character_tone; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.character_tone (
    id integer NOT NULL,
    character_id character varying(50),
    affinity_level character varying(20) NOT NULL,
    level_range_min integer NOT NULL,
    level_range_max integer NOT NULL,
    style text NOT NULL,
    calling character varying(50),
    suffix character varying(50),
    samples jsonb
);


ALTER TABLE content.character_tone OWNER TO kime;

--
-- Name: character_tone_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.character_tone_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.character_tone_id_seq OWNER TO kime;

--
-- Name: character_tone_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.character_tone_id_seq OWNED BY content.character_tone.id;


--
-- Name: characters; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.characters (
    character_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    personality text,
    breathing_style character varying(100),
    default_affinity integer DEFAULT 500,
    appearance_hair text,
    appearance_eyes text,
    appearance_distinctive text,
    appearance_impression text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE content.characters OWNER TO kime;

--
-- Name: TABLE characters; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.characters IS 'Character master data with personality and appearance';


--
-- Name: COLUMN characters.default_affinity; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.characters.default_affinity IS 'Default affinity level (0-1000)';


--
-- Name: image_mappings; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.image_mappings (
    id integer NOT NULL,
    scenario_id character varying(50),
    mapping_category character varying(50) NOT NULL,
    image_key character varying(255) NOT NULL,
    image_url text NOT NULL,
    metadata jsonb
);


ALTER TABLE content.image_mappings OWNER TO kime;

--
-- Name: image_mappings_id_seq; Type: SEQUENCE; Schema: content; Owner: kime
--

CREATE SEQUENCE content.image_mappings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE content.image_mappings_id_seq OWNER TO kime;

--
-- Name: image_mappings_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: kime
--

ALTER SEQUENCE content.image_mappings_id_seq OWNED BY content.image_mappings.id;


--
-- Name: rank_definitions; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.rank_definitions (
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


ALTER TABLE content.rank_definitions OWNER TO kime;

--
-- Name: TABLE rank_definitions; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.rank_definitions IS '계급 정의 (견습생 → 대원 → 정예 → 주 후보 → 주)';


--
-- Name: COLUMN rank_definitions.rank_code; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.rank_definitions.rank_code IS '계급 코드 (예: MIZUNOTO, KINOE, HASHIRA)';


--
-- Name: COLUMN rank_definitions.min_xp; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.rank_definitions.min_xp IS '해당 계급 도달에 필요한 최소 경험치';


--
-- Name: scenario_beats; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.scenario_beats (
    beat_id character varying(100) NOT NULL,
    scenario_id character varying(50),
    beat_name character varying(255) NOT NULL,
    beat_category character varying(50),
    display_order integer DEFAULT 0,
    parent_beat_id character varying(100),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE content.scenario_beats OWNER TO kime;

--
-- Name: scenario_statistics; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.scenario_statistics (
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


ALTER TABLE content.scenario_statistics OWNER TO kime;

--
-- Name: TABLE scenario_statistics; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.scenario_statistics IS 'Aggregated statistics for each scenario';


--
-- Name: COLUMN scenario_statistics.total_likes; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenario_statistics.total_likes IS 'Count of users who liked this scenario';


--
-- Name: COLUMN scenario_statistics.total_views; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenario_statistics.total_views IS 'Total number of times scenario was viewed';


--
-- Name: COLUMN scenario_statistics.total_completions; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenario_statistics.total_completions IS 'Number of users who completed this scenario';


--
-- Name: COLUMN scenario_statistics.avg_session_duration; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenario_statistics.avg_session_duration IS 'Average play time in minutes';


--
-- Name: scenario_views; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.scenario_views (
    view_id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id character varying(50),
    user_id uuid,
    ip_address inet,
    user_agent text,
    viewed_at timestamp without time zone DEFAULT now()
);


ALTER TABLE content.scenario_views OWNER TO kime;

--
-- Name: TABLE scenario_views; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.scenario_views IS 'Log of scenario card views for analytics';


--
-- Name: COLUMN scenario_views.user_id; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenario_views.user_id IS 'NULL for anonymous users';


--
-- Name: scenarios; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.scenarios (
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
    updated_at timestamp without time zone DEFAULT now(),
    world_id character varying(50)
);


ALTER TABLE content.scenarios OWNER TO kime;

--
-- Name: TABLE scenarios; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.scenarios IS 'Scenario metadata for HomePage scenario cards';


--
-- Name: COLUMN scenarios.scenario_id; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenarios.scenario_id IS 'Unique identifier matching scenario file names';


--
-- Name: COLUMN scenarios.card_size; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenarios.card_size IS 'Display size on HomePage: large (featured) or normal';


--
-- Name: COLUMN scenarios.display_order; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenarios.display_order IS 'Lower numbers appear first on HomePage';


--
-- Name: COLUMN scenarios.is_active; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON COLUMN content.scenarios.is_active IS 'False = hidden from HomePage (soft delete)';


--
-- Name: v_scenario_cards; Type: VIEW; Schema: content; Owner: kime
--

CREATE VIEW content.v_scenario_cards AS
 SELECT s.scenario_id,
    s.title,
    s.description,
    s.image_url,
    s.thumbnail_url,
    s.tags,
    s.card_size,
    s.route_path,
    s.display_order,
    s.is_active,
    COALESCE(ss.total_likes, 0) AS likes,
    COALESCE(ss.total_comments, 0) AS comments,
    COALESCE(ss.total_views, 0) AS views,
    COALESCE(ss.total_completions, 0) AS total_completions,
    COALESCE(ss.avg_session_duration, 0) AS avg_session_duration,
    s.created_at,
    s.updated_at
   FROM (content.scenarios s
     LEFT JOIN content.scenario_statistics ss ON (((s.scenario_id)::text = (ss.scenario_id)::text)))
  WHERE (s.is_active = true)
  ORDER BY s.display_order, s.created_at DESC;


ALTER TABLE content.v_scenario_cards OWNER TO kime;

--
-- Name: VIEW v_scenario_cards; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON VIEW content.v_scenario_cards IS 'Scenario cards with statistics for HomePage (active scenarios only)';


--
-- Name: worlds; Type: TABLE; Schema: content; Owner: kime
--

CREATE TABLE content.worlds (
    world_id character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    era character varying(100),
    lore jsonb,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE content.worlds OWNER TO kime;

--
-- Name: TABLE worlds; Type: COMMENT; Schema: content; Owner: kime
--

COMMENT ON TABLE content.worlds IS 'World/universe settings for scenarios';


--
-- Name: dialogues; Type: TABLE; Schema: conversation; Owner: kime
--

CREATE TABLE conversation.dialogues (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    speaker character varying(255) NOT NULL,
    content text NOT NULL,
    emotion character varying(100),
    emotion_intensity character varying(50),
    order_index integer,
    "timestamp" timestamp without time zone DEFAULT now(),
    embedding public.vector(1536),
    mentioned_entity_ids integer[] DEFAULT '{}'::integer[]
);


ALTER TABLE conversation.dialogues OWNER TO kime;

--
-- Name: TABLE dialogues; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON TABLE conversation.dialogues IS '캐릭터 대화 기록';


--
-- Name: COLUMN dialogues.speaker; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.dialogues.speaker IS '화자 ID (tanjiro, rengoku 등)';


--
-- Name: COLUMN dialogues.order_index; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.dialogues.order_index IS '같은 턴 내 대화 순서';


--
-- Name: dialogues_id_seq; Type: SEQUENCE; Schema: conversation; Owner: kime
--

CREATE SEQUENCE conversation.dialogues_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE conversation.dialogues_id_seq OWNER TO kime;

--
-- Name: dialogues_id_seq; Type: SEQUENCE OWNED BY; Schema: conversation; Owner: kime
--

ALTER SEQUENCE conversation.dialogues_id_seq OWNED BY conversation.dialogues.id;


--
-- Name: session_snapshots; Type: TABLE; Schema: conversation; Owner: kime
--

CREATE TABLE conversation.session_snapshots (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    state_json jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE conversation.session_snapshots OWNER TO kime;

--
-- Name: TABLE session_snapshots; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON TABLE conversation.session_snapshots IS '세션 상태 스냅샷 (복구 및 분석용)';


--
-- Name: COLUMN session_snapshots.state_json; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.session_snapshots.state_json IS '전체 GraphState를 JSON으로 저장';


--
-- Name: session_snapshots_id_seq; Type: SEQUENCE; Schema: conversation; Owner: kime
--

CREATE SEQUENCE conversation.session_snapshots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE conversation.session_snapshots_id_seq OWNER TO kime;

--
-- Name: session_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: conversation; Owner: kime
--

ALTER SEQUENCE conversation.session_snapshots_id_seq OWNED BY conversation.session_snapshots.id;


--
-- Name: sessions; Type: TABLE; Schema: conversation; Owner: kime
--

CREATE TABLE conversation.sessions (
    session_id uuid NOT NULL,
    scenario_id character varying(255) NOT NULL,
    user_name character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    last_interaction_at timestamp without time zone DEFAULT now(),
    current_stage character varying(255),
    turn_count integer DEFAULT 0,
    stage_turn integer DEFAULT 0,
    final_ending character varying(255),
    is_active boolean DEFAULT true,
    user_id uuid,
    conversation_summary text DEFAULT ''::text,
    summary_updated_at timestamp without time zone,
    summary_turn_count integer DEFAULT 0
);


ALTER TABLE conversation.sessions OWNER TO kime;

--
-- Name: TABLE sessions; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON TABLE conversation.sessions IS '사용자 세션 메타데이터';


--
-- Name: COLUMN sessions.session_id; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.session_id IS '세션 고유 ID';


--
-- Name: COLUMN sessions.scenario_id; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.scenario_id IS '현재 플레이 중인 시나리오 ID';


--
-- Name: COLUMN sessions.current_stage; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.current_stage IS '현재 스테이지 ID';


--
-- Name: COLUMN sessions.turn_count; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.turn_count IS '전체 대화 턴 수';


--
-- Name: COLUMN sessions.stage_turn; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.stage_turn IS '현재 스테이지 내 턴 수';


--
-- Name: COLUMN sessions.user_id; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.user_id IS '세션을 시작한 사용자 ID';


--
-- Name: COLUMN sessions.conversation_summary; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.conversation_summary IS '대화 요약 (장기기억용)';


--
-- Name: COLUMN sessions.last_interaction_at; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.last_interaction_at IS '마지막 상호작용 시간';


--
-- Name: COLUMN sessions.summary_updated_at; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.summary_updated_at IS '마지막 요약 업데이트 시간';


--
-- Name: COLUMN sessions.summary_turn_count; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.sessions.summary_turn_count IS '요약에 포함된 대화 턴 수';


--
-- Name: FUNCTION touch_session_activity(); Type: FUNCTION; Schema: conversation; Owner: kime
--

CREATE OR REPLACE FUNCTION conversation.touch_session_activity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    NEW.last_interaction_at = now();
    RETURN NEW;
END;
$$;


--
-- Name: trigger_touch_session_activity; Type: TRIGGER; Schema: conversation; Owner: kime
--

CREATE TRIGGER trigger_touch_session_activity
    BEFORE UPDATE ON conversation.sessions
    FOR EACH ROW
    EXECUTE FUNCTION conversation.touch_session_activity();


--
-- Name: user_inputs; Type: TABLE; Schema: conversation; Owner: kime
--

CREATE TABLE conversation.user_inputs (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    user_id uuid,
    turn_number integer NOT NULL,
    user_input text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE conversation.user_inputs OWNER TO kime;

--
-- Name: TABLE user_inputs; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON TABLE conversation.user_inputs IS '사용자 입력 히스토리';


--
-- Name: COLUMN user_inputs.turn_number; Type: COMMENT; Schema: conversation; Owner: kime
--

COMMENT ON COLUMN conversation.user_inputs.turn_number IS '해당 세션 내 턴 번호';

COMMENT ON COLUMN conversation.user_inputs.user_id IS '입력한 사용자 ID (세션 사용자 캐시)';

COMMENT ON COLUMN conversation.user_inputs.created_at IS '생성 시각 (timestamp 컬럼과 동일, 이관용)';

--
-- Name: user_inputs_id_seq; Type: SEQUENCE; Schema: conversation; Owner: kime
--

CREATE SEQUENCE conversation.user_inputs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE conversation.user_inputs_id_seq OWNER TO kime;

--
-- Name: user_inputs_id_seq; Type: SEQUENCE OWNED BY; Schema: conversation; Owner: kime
--

ALTER SEQUENCE conversation.user_inputs_id_seq OWNED BY conversation.user_inputs.id;


--
-- Name: entities; Type: TABLE; Schema: knowledge; Owner: kime
--

CREATE TABLE knowledge.entities (
    entity_id integer NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_name character varying(255) NOT NULL,
    canonical_name character varying(255),
    description text,
    properties jsonb DEFAULT '{}'::jsonb,
    embedding public.vector(1536),
    importance_score double precision DEFAULT 0.5,
    community_id integer,
    first_seen_at timestamp without time zone DEFAULT now(),
    last_updated_at timestamp without time zone DEFAULT now(),
    mention_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_entity_type CHECK (((entity_type)::text = ANY ((ARRAY['character'::character varying, 'location'::character varying, 'event'::character varying, 'item'::character varying, 'skill'::character varying])::text[]))),
    CONSTRAINT valid_importance CHECK (((importance_score >= (0.0)::double precision) AND (importance_score <= (1.0)::double precision)))
);


ALTER TABLE knowledge.entities OWNER TO kime;

--
-- Name: TABLE entities; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON TABLE knowledge.entities IS 'Graph RAG entity storage with embeddings for semantic search';


--
-- Name: COLUMN entities.canonical_name; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entities.canonical_name IS 'Normalized name for deduplication (e.g., "렌고쿠" = "렌고쿠 쿄쥬로")';


--
-- Name: COLUMN entities.embedding; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entities.embedding IS 'Vector embedding for semantic similarity search (1536 dimensions)';


--
-- Name: COLUMN entities.importance_score; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entities.importance_score IS 'Entity importance for ranking (0.0 = low, 1.0 = high)';


--
-- Name: COLUMN entities.community_id; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entities.community_id IS 'Graph community ID for clustering related entities';


--
-- Name: entities_entity_id_seq; Type: SEQUENCE; Schema: knowledge; Owner: kime
--

CREATE SEQUENCE knowledge.entities_entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE knowledge.entities_entity_id_seq OWNER TO kime;

--
-- Name: entities_entity_id_seq; Type: SEQUENCE OWNED BY; Schema: knowledge; Owner: kime
--

ALTER SEQUENCE knowledge.entities_entity_id_seq OWNED BY knowledge.entities.entity_id;


--
-- Name: entity_mentions; Type: TABLE; Schema: knowledge; Owner: kime
--

CREATE TABLE knowledge.entity_mentions (
    mention_id integer NOT NULL,
    entity_id integer NOT NULL,
    source_type character varying(50) NOT NULL,
    source_id integer NOT NULL,
    session_id character varying(255),
    turn_number integer,
    mention_context text,
    extraction_method character varying(50),
    confidence double precision DEFAULT 0.8,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT valid_extraction_method CHECK (((extraction_method)::text = ANY ((ARRAY['rule'::character varying, 'llm'::character varying, 'manual'::character varying])::text[]))),
    CONSTRAINT valid_mention_confidence CHECK (((confidence >= (0.0)::double precision) AND (confidence <= (1.0)::double precision))),
    CONSTRAINT valid_source_type CHECK (((source_type)::text = ANY ((ARRAY['training_log'::character varying, 'dialogue'::character varying, 'user_memory'::character varying])::text[])))
);


ALTER TABLE knowledge.entity_mentions OWNER TO kime;

--
-- Name: TABLE entity_mentions; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON TABLE knowledge.entity_mentions IS 'Links entities to logs, dialogues, and memories where they appear';


--
-- Name: COLUMN entity_mentions.source_type; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_mentions.source_type IS 'Type of record: training_log, dialogue, or user_memory';


--
-- Name: COLUMN entity_mentions.source_id; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_mentions.source_id IS 'ID in the corresponding source table';


--
-- Name: COLUMN entity_mentions.extraction_method; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_mentions.extraction_method IS 'How entity was extracted: rule-based, LLM, or manual';


--
-- Name: entity_mentions_mention_id_seq; Type: SEQUENCE; Schema: knowledge; Owner: kime
--

CREATE SEQUENCE knowledge.entity_mentions_mention_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE knowledge.entity_mentions_mention_id_seq OWNER TO kime;

--
-- Name: entity_mentions_mention_id_seq; Type: SEQUENCE OWNED BY; Schema: knowledge; Owner: kime
--

ALTER SEQUENCE knowledge.entity_mentions_mention_id_seq OWNED BY knowledge.entity_mentions.mention_id;


--
-- Name: entity_relationships; Type: TABLE; Schema: knowledge; Owner: kime
--

CREATE TABLE knowledge.entity_relationships (
    relationship_id integer NOT NULL,
    source_entity_id integer NOT NULL,
    target_entity_id integer NOT NULL,
    relationship_type character varying(100) NOT NULL,
    strength double precision DEFAULT 0.5,
    confidence double precision DEFAULT 0.5,
    properties jsonb DEFAULT '{}'::jsonb,
    evidence_count integer DEFAULT 1,
    first_observed_at timestamp without time zone DEFAULT now(),
    last_observed_at timestamp without time zone DEFAULT now(),
    provenance text,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT no_self_loop CHECK ((source_entity_id <> target_entity_id)),
    CONSTRAINT valid_confidence CHECK (((confidence >= (0.0)::double precision) AND (confidence <= (1.0)::double precision))),
    CONSTRAINT valid_strength CHECK (((strength >= (0.0)::double precision) AND (strength <= (1.0)::double precision)))
);


ALTER TABLE knowledge.entity_relationships OWNER TO kime;

--
-- Name: TABLE entity_relationships; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON TABLE knowledge.entity_relationships IS 'Graph edges connecting entities with typed relationships';


--
-- Name: COLUMN entity_relationships.strength; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_relationships.strength IS 'Relationship strength (0.0 = weak, 1.0 = strong)';


--
-- Name: COLUMN entity_relationships.confidence; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_relationships.confidence IS 'Confidence in this relationship (0.0 = uncertain, 1.0 = certain)';


--
-- Name: COLUMN entity_relationships.evidence_count; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_relationships.evidence_count IS 'Number of times this relationship was observed';


--
-- Name: COLUMN entity_relationships.provenance; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.entity_relationships.provenance IS 'Source of relationship: "dialogue:123", "training_log:456"';


--
-- Name: entity_relationships_relationship_id_seq; Type: SEQUENCE; Schema: knowledge; Owner: kime
--

CREATE SEQUENCE knowledge.entity_relationships_relationship_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE knowledge.entity_relationships_relationship_id_seq OWNER TO kime;

--
-- Name: entity_relationships_relationship_id_seq; Type: SEQUENCE OWNED BY; Schema: knowledge; Owner: kime
--

ALTER SEQUENCE knowledge.entity_relationships_relationship_id_seq OWNED BY knowledge.entity_relationships.relationship_id;


--
-- Name: user_memories; Type: TABLE; Schema: knowledge; Owner: kime
--

CREATE TABLE knowledge.user_memories (
    id bigint NOT NULL,
    user_id uuid NOT NULL,
    memory_key character varying(100) NOT NULL,
    memory_type character varying(50) DEFAULT 'fact'::character varying,
    memory_value text NOT NULL,
    context jsonb,
    importance double precision DEFAULT 0.5,
    access_count integer DEFAULT 0,
    last_accessed_at timestamp without time zone,
    source_session_id uuid,
    related_session_ids uuid[],
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true,
    expires_at timestamp without time zone,
    tags character varying(50)[],
    confidence double precision,
    embedding public.vector(1536),
    related_entity_ids integer[] DEFAULT '{}'::integer[],
    CONSTRAINT user_memories_confidence_check CHECK (((confidence >= (0.0)::double precision) AND (confidence <= (1.0)::double precision))),
    CONSTRAINT user_memories_importance_check CHECK (((importance >= (0.0)::double precision) AND (importance <= (1.0)::double precision)))
);


ALTER TABLE knowledge.user_memories OWNER TO kime;

--
-- Name: TABLE user_memories; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON TABLE knowledge.user_memories IS 'User-level long-term memories that persist across sessions for personalized AI interactions';


--
-- Name: COLUMN user_memories.user_id; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.user_id IS 'User who owns this memory';


--
-- Name: COLUMN user_memories.memory_key; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.memory_key IS 'Category/key for this memory (e.g., character_relationship:tanjiro, user_preference:tone)';


--
-- Name: COLUMN user_memories.memory_type; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.memory_type IS 'Type of memory: fact, preference, relationship, event, goal';


--
-- Name: COLUMN user_memories.memory_value; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.memory_value IS 'The actual memory content in natural language';


--
-- Name: COLUMN user_memories.context; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.context IS 'Additional structured metadata (JSONB)';


--
-- Name: COLUMN user_memories.importance; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.importance IS 'Importance score 0.0-1.0 (higher = more important for retrieval)';


--
-- Name: COLUMN user_memories.access_count; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.access_count IS 'Number of times this memory was retrieved';


--
-- Name: COLUMN user_memories.is_active; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.is_active IS 'Whether this memory is still relevant (can be archived without deletion)';


--
-- Name: COLUMN user_memories.confidence; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON COLUMN knowledge.user_memories.confidence IS 'Confidence score for auto-extracted memories (0.0-1.0)';


--
-- Name: user_memories_id_seq; Type: SEQUENCE; Schema: knowledge; Owner: kime
--

CREATE SEQUENCE knowledge.user_memories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE knowledge.user_memories_id_seq OWNER TO kime;

--
-- Name: user_memories_id_seq; Type: SEQUENCE OWNED BY; Schema: knowledge; Owner: kime
--

ALTER SEQUENCE knowledge.user_memories_id_seq OWNED BY knowledge.user_memories.id;


--
-- Name: training_logs; Type: TABLE; Schema: ml; Owner: kime
--

CREATE TABLE ml.training_logs (
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
    embedding public.vector(1536),
    mentioned_entity_ids integer[] DEFAULT '{}'::integer[],
    CONSTRAINT training_logs_feedback_score_check CHECK (((feedback_score >= (0.0)::double precision) AND (feedback_score <= (1.0)::double precision)))
);


ALTER TABLE ml.training_logs OWNER TO kime;

--
-- Name: TABLE training_logs; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON TABLE ml.training_logs IS 'Training data for SLLM LoRA fine-tuning with automatic outcome labeling';


--
-- Name: COLUMN training_logs.session_id; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.session_id IS 'Session UUID to group conversation turns';


--
-- Name: COLUMN training_logs.turn_count; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.turn_count IS 'Turn number in the conversation';


--
-- Name: COLUMN training_logs.agent_name; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.agent_name IS 'Agent that generated this log (router, parent, children, dialogue)';


--
-- Name: COLUMN training_logs.context; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.context IS 'State snapshot (JSONB) - input for the model';


--
-- Name: COLUMN training_logs.model_output; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.model_output IS 'Agent response/decision (JSONB) - expected output for training';


--
-- Name: COLUMN training_logs.outcome; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.outcome IS 'Auto-labeled outcome: success (좋은 예시), failure (나쁜 예시), partial (애매한 예시)';


--
-- Name: COLUMN training_logs.feedback_score; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON COLUMN ml.training_logs.feedback_score IS 'Quality score 0.0-1.0 for weighted learning';


--
-- Name: training_logs_id_seq; Type: SEQUENCE; Schema: ml; Owner: kime
--

CREATE SEQUENCE ml.training_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE ml.training_logs_id_seq OWNER TO kime;

--
-- Name: training_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: ml; Owner: kime
--

ALTER SEQUENCE ml.training_logs_id_seq OWNED BY ml.training_logs.id;


--
-- Name: user_feedback; Type: TABLE; Schema: ml; Owner: kime
--

CREATE TABLE ml.user_feedback (
    id bigint NOT NULL,
    training_log_id bigint,
    feedback_type character varying(50) NOT NULL,
    feedback_text text,
    user_id character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE ml.user_feedback OWNER TO kime;

--
-- Name: TABLE user_feedback; Type: COMMENT; Schema: ml; Owner: kime
--

COMMENT ON TABLE ml.user_feedback IS 'Human feedback for improving auto-labeling and training data quality';


--
-- Name: user_feedback_id_seq; Type: SEQUENCE; Schema: ml; Owner: kime
--

CREATE SEQUENCE ml.user_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE ml.user_feedback_id_seq OWNER TO kime;

--
-- Name: user_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: ml; Owner: kime
--

ALTER SEQUENCE ml.user_feedback_id_seq OWNED BY ml.user_feedback.id;


--
-- Name: error_logs; Type: TABLE; Schema: observability; Owner: kime
--

CREATE TABLE observability.error_logs (
    id bigint NOT NULL,
    session_id uuid,
    error_type character varying(100) NOT NULL,
    error_message text NOT NULL,
    stack_trace text,
    context_data jsonb,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE observability.error_logs OWNER TO kime;

--
-- Name: TABLE error_logs; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON TABLE observability.error_logs IS '에러 로그 (별도 테이블로 빠른 조회)';


--
-- Name: COLUMN error_logs.stack_trace; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.error_logs.stack_trace IS 'Python traceback';


--
-- Name: error_logs_id_seq; Type: SEQUENCE; Schema: observability; Owner: kime
--

CREATE SEQUENCE observability.error_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE observability.error_logs_id_seq OWNER TO kime;

--
-- Name: error_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: observability; Owner: kime
--

ALTER SEQUENCE observability.error_logs_id_seq OWNED BY observability.error_logs.id;


--
-- Name: logs; Type: TABLE; Schema: observability; Owner: kime
--

CREATE TABLE observability.logs (
    id bigint NOT NULL,
    session_id uuid,
    log_level character varying(20) NOT NULL,
    stage_name character varying(100),
    agent_name character varying(100),
    message text NOT NULL,
    context_data jsonb,
    duration_ms real,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE observability.logs OWNER TO kime;

--
-- Name: TABLE logs; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON TABLE observability.logs IS '구조화된 애플리케이션 로그';


--
-- Name: COLUMN logs.log_level; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.logs.log_level IS '로그 레벨 (INFO, WARNING, ERROR, DEBUG)';


--
-- Name: COLUMN logs.stage_name; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.logs.stage_name IS '실행 중인 스테이지';


--
-- Name: COLUMN logs.agent_name; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.logs.agent_name IS '실행 중인 에이전트';


--
-- Name: COLUMN logs.duration_ms; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.logs.duration_ms IS '작업 수행 시간 (밀리초)';


--
-- Name: logs_id_seq; Type: SEQUENCE; Schema: observability; Owner: kime
--

CREATE SEQUENCE observability.logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE observability.logs_id_seq OWNER TO kime;

--
-- Name: logs_id_seq; Type: SEQUENCE OWNED BY; Schema: observability; Owner: kime
--

ALTER SEQUENCE observability.logs_id_seq OWNED BY observability.logs.id;


--
-- Name: performance_metrics; Type: TABLE; Schema: observability; Owner: kime
--

CREATE TABLE observability.performance_metrics (
    id bigint NOT NULL,
    metric_name character varying(100) NOT NULL,
    metric_value real NOT NULL,
    metric_unit character varying(50),
    tags jsonb,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE observability.performance_metrics OWNER TO kime;

--
-- Name: TABLE performance_metrics; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON TABLE observability.performance_metrics IS '성능 메트릭 (응답 시간, 캐시 히트율 등)';


--
-- Name: COLUMN performance_metrics.metric_name; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.performance_metrics.metric_name IS '메트릭 이름 (api_response_time, cache_hit_rate 등)';


--
-- Name: COLUMN performance_metrics.tags; Type: COMMENT; Schema: observability; Owner: kime
--

COMMENT ON COLUMN observability.performance_metrics.tags IS 'JSON 형식의 태그 (환경, 버전 등)';


--
-- Name: performance_metrics_id_seq; Type: SEQUENCE; Schema: observability; Owner: kime
--

CREATE SEQUENCE observability.performance_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE observability.performance_metrics_id_seq OWNER TO kime;

--
-- Name: performance_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: observability; Owner: kime
--

ALTER SEQUENCE observability.performance_metrics_id_seq OWNED BY observability.performance_metrics.id;


--
-- Name: affinity_records; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.affinity_records (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    character_name character varying(255) NOT NULL,
    affinity_score integer NOT NULL,
    change_amount integer,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE progression.affinity_records OWNER TO kime;

--
-- Name: TABLE affinity_records; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.affinity_records IS '캐릭터 친밀도 변화 기록';


--
-- Name: COLUMN affinity_records.affinity_score; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.affinity_records.affinity_score IS '현재 친밀도 점수';


--
-- Name: COLUMN affinity_records.change_amount; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.affinity_records.change_amount IS '이전 턴 대비 변화량';


--
-- Name: affinity_records_id_seq; Type: SEQUENCE; Schema: progression; Owner: kime
--

CREATE SEQUENCE progression.affinity_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE progression.affinity_records_id_seq OWNER TO kime;

--
-- Name: affinity_records_id_seq; Type: SEQUENCE OWNED BY; Schema: progression; Owner: kime
--

ALTER SEQUENCE progression.affinity_records_id_seq OWNED BY progression.affinity_records.id;


--
-- Name: game_events; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.game_events (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    turn_number integer NOT NULL,
    event_type character varying(100) NOT NULL,
    event_data jsonb NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE progression.game_events OWNER TO kime;

--
-- Name: TABLE game_events; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.game_events IS '게임 이벤트 및 시스템 플래그';


--
-- Name: COLUMN game_events.event_type; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.game_events.event_type IS '이벤트 타입 (flag_set, mission_complete 등)';


--
-- Name: COLUMN game_events.event_data; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.game_events.event_data IS 'JSON 형식의 이벤트 상세 데이터';


--
-- Name: game_events_id_seq; Type: SEQUENCE; Schema: progression; Owner: kime
--

CREATE SEQUENCE progression.game_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE progression.game_events_id_seq OWNER TO kime;

--
-- Name: game_events_id_seq; Type: SEQUENCE OWNED BY; Schema: progression; Owner: kime
--

ALTER SEQUENCE progression.game_events_id_seq OWNED BY progression.game_events.id;


--
-- Name: mission_records; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.mission_records (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    mission_type character varying(100) NOT NULL,
    target_character character varying(255),
    attempt_count integer DEFAULT 0,
    success boolean,
    completed_at timestamp without time zone DEFAULT now()
);


ALTER TABLE progression.mission_records OWNER TO kime;

--
-- Name: TABLE mission_records; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.mission_records IS '미션 수행 기록 (RECRUIT 등)';


--
-- Name: COLUMN mission_records.mission_type; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.mission_records.mission_type IS '미션 타입 (RECRUIT, DEFEND 등)';


--
-- Name: COLUMN mission_records.target_character; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.mission_records.target_character IS '미션 대상 캐릭터';


--
-- Name: mission_records_id_seq; Type: SEQUENCE; Schema: progression; Owner: kime
--

CREATE SEQUENCE progression.mission_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE progression.mission_records_id_seq OWNER TO kime;

--
-- Name: mission_records_id_seq; Type: SEQUENCE OWNED BY; Schema: progression; Owner: kime
--

ALTER SEQUENCE progression.mission_records_id_seq OWNED BY progression.mission_records.id;


--
-- Name: stage_progression; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.stage_progression (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    stage_id character varying(255) NOT NULL,
    stage_order integer NOT NULL,
    entered_at timestamp without time zone DEFAULT now(),
    exited_at timestamp without time zone,
    dialogue_count integer DEFAULT 0,
    stage_turn_count integer DEFAULT 0
);


ALTER TABLE progression.stage_progression OWNER TO kime;

--
-- Name: TABLE stage_progression; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.stage_progression IS '스테이지 진행 기록';


--
-- Name: COLUMN stage_progression.stage_order; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.stage_progression.stage_order IS '스테이지 진입 순서';


--
-- Name: COLUMN stage_progression.dialogue_count; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.stage_progression.dialogue_count IS '해당 스테이지에서 생성된 대화 수';


--
-- Name: stage_progression_id_seq; Type: SEQUENCE; Schema: progression; Owner: kime
--

CREATE SEQUENCE progression.stage_progression_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE progression.stage_progression_id_seq OWNER TO kime;

--
-- Name: stage_progression_id_seq; Type: SEQUENCE OWNED BY; Schema: progression; Owner: kime
--

ALTER SEQUENCE progression.stage_progression_id_seq OWNED BY progression.stage_progression.id;


--
-- Name: user_equipment; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.user_equipment (
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


ALTER TABLE progression.user_equipment OWNER TO kime;

--
-- Name: TABLE user_equipment; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.user_equipment IS '사용자 장비 상태 (일륜도, 복장, 까마귀)';


--
-- Name: COLUMN user_equipment.sword_status; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_equipment.sword_status IS '일륜도 상태: excellent(완벽) > good(양호) > fair(보통) > poor(나쁨) > broken(파손)';


--
-- Name: COLUMN user_equipment.uniform_status; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_equipment.uniform_status IS '복장 상태: pristine(새것) > worn(착용중) > equipped(장착) > damaged(손상) > torn(찢김)';


--
-- Name: COLUMN user_equipment.crow_status; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_equipment.crow_status IS '까마귀 상태: waiting(대기중) > active(활동중) > resting(휴식) > absent(부재중)';


--
-- Name: user_progression; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.user_progression (
    user_id uuid NOT NULL,
    rank_code character varying(50) DEFAULT 'MIZUNOTO'::character varying,
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
    CONSTRAINT user_progression_level_check CHECK (((level >= 1) AND (level <= 999))),
    CONSTRAINT user_progression_scenarios_completed_check CHECK ((scenarios_completed >= 0)),
    CONSTRAINT user_progression_total_messages_check CHECK ((total_messages >= 0)),
    CONSTRAINT user_progression_total_play_minutes_check CHECK ((total_play_minutes >= 0)),
    CONSTRAINT user_progression_total_sessions_check CHECK ((total_sessions >= 0))
);


ALTER TABLE progression.user_progression OWNER TO kime;

--
-- Name: TABLE user_progression; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.user_progression IS '사용자별 진행도 (레벨, 경험치, 통계)';


--
-- Name: COLUMN user_progression.experience_points; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_progression.experience_points IS '총 획득 경험치 (XP)';


--
-- Name: COLUMN user_progression.level; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_progression.level IS '현재 레벨 (1-999, 주급은 101+)';


--
-- Name: COLUMN user_progression.total_messages; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_progression.total_messages IS '전체 대화 메시지 수';


--
-- Name: COLUMN user_progression.total_sessions; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_progression.total_sessions IS '전체 세션 수';


--
-- Name: COLUMN user_progression.total_play_minutes; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_progression.total_play_minutes IS '전체 플레이 시간 (분)';


--
-- Name: user_scenario_progress; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.user_scenario_progress (
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


ALTER TABLE progression.user_scenario_progress OWNER TO kime;

--
-- Name: TABLE user_scenario_progress; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.user_scenario_progress IS 'Per-user progress and interactions with each scenario';


--
-- Name: COLUMN user_scenario_progress.has_started; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_scenario_progress.has_started IS 'True if user has played this scenario at least once';


--
-- Name: COLUMN user_scenario_progress.has_completed; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_scenario_progress.has_completed IS 'True if user finished the scenario';


--
-- Name: COLUMN user_scenario_progress.completion_percentage; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_scenario_progress.completion_percentage IS 'Progress 0-100% (based on stages completed)';


--
-- Name: COLUMN user_scenario_progress.is_liked; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.user_scenario_progress.is_liked IS 'User''s like status for this scenario';


--
-- Name: xp_transactions; Type: TABLE; Schema: progression; Owner: kime
--

CREATE TABLE progression.xp_transactions (
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


ALTER TABLE progression.xp_transactions OWNER TO kime;

--
-- Name: TABLE xp_transactions; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON TABLE progression.xp_transactions IS '경험치 획득 내역 (감사 로그)';


--
-- Name: COLUMN xp_transactions.xp_type; Type: COMMENT; Schema: progression; Owner: kime
--

COMMENT ON COLUMN progression.xp_transactions.xp_type IS '획득 타입: message(메시지), session_complete(세션 완료), scenario_complete(시나리오 완료), achievement(업적), daily_bonus(일일 보너스), event(이벤트)';


--
-- Name: beat_goals id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.beat_goals ALTER COLUMN id SET DEFAULT nextval('content.beat_goals_id_seq'::regclass);


--
-- Name: character_aliases id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_aliases ALTER COLUMN id SET DEFAULT nextval('content.character_aliases_id_seq'::regclass);


--
-- Name: character_core_values id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_core_values ALTER COLUMN id SET DEFAULT nextval('content.character_core_values_id_seq'::regclass);


--
-- Name: character_emotional_triggers id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_emotional_triggers ALTER COLUMN id SET DEFAULT nextval('content.character_emotional_triggers_id_seq'::regclass);


--
-- Name: character_intent_rules id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_intent_rules ALTER COLUMN id SET DEFAULT nextval('content.character_intent_rules_id_seq'::regclass);


--
-- Name: character_quotes id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_quotes ALTER COLUMN id SET DEFAULT nextval('content.character_quotes_id_seq'::regclass);


--
-- Name: character_relationships id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships ALTER COLUMN id SET DEFAULT nextval('content.character_relationships_id_seq'::regclass);


--
-- Name: character_tone id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_tone ALTER COLUMN id SET DEFAULT nextval('content.character_tone_id_seq'::regclass);


--
-- Name: image_mappings id; Type: DEFAULT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.image_mappings ALTER COLUMN id SET DEFAULT nextval('content.image_mappings_id_seq'::regclass);


--
-- Name: dialogues id; Type: DEFAULT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.dialogues ALTER COLUMN id SET DEFAULT nextval('conversation.dialogues_id_seq'::regclass);


--
-- Name: session_snapshots id; Type: DEFAULT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.session_snapshots ALTER COLUMN id SET DEFAULT nextval('conversation.session_snapshots_id_seq'::regclass);


--
-- Name: user_inputs id; Type: DEFAULT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.user_inputs ALTER COLUMN id SET DEFAULT nextval('conversation.user_inputs_id_seq'::regclass);


--
-- Name: entities entity_id; Type: DEFAULT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entities ALTER COLUMN entity_id SET DEFAULT nextval('knowledge.entities_entity_id_seq'::regclass);


--
-- Name: entity_mentions mention_id; Type: DEFAULT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_mentions ALTER COLUMN mention_id SET DEFAULT nextval('knowledge.entity_mentions_mention_id_seq'::regclass);


--
-- Name: entity_relationships relationship_id; Type: DEFAULT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_relationships ALTER COLUMN relationship_id SET DEFAULT nextval('knowledge.entity_relationships_relationship_id_seq'::regclass);


--
-- Name: user_memories id; Type: DEFAULT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.user_memories ALTER COLUMN id SET DEFAULT nextval('knowledge.user_memories_id_seq'::regclass);


--
-- Name: training_logs id; Type: DEFAULT; Schema: ml; Owner: kime
--

ALTER TABLE ONLY ml.training_logs ALTER COLUMN id SET DEFAULT nextval('ml.training_logs_id_seq'::regclass);


--
-- Name: user_feedback id; Type: DEFAULT; Schema: ml; Owner: kime
--

ALTER TABLE ONLY ml.user_feedback ALTER COLUMN id SET DEFAULT nextval('ml.user_feedback_id_seq'::regclass);


--
-- Name: error_logs id; Type: DEFAULT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.error_logs ALTER COLUMN id SET DEFAULT nextval('observability.error_logs_id_seq'::regclass);


--
-- Name: logs id; Type: DEFAULT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.logs ALTER COLUMN id SET DEFAULT nextval('observability.logs_id_seq'::regclass);


--
-- Name: performance_metrics id; Type: DEFAULT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.performance_metrics ALTER COLUMN id SET DEFAULT nextval('observability.performance_metrics_id_seq'::regclass);


--
-- Name: affinity_records id; Type: DEFAULT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.affinity_records ALTER COLUMN id SET DEFAULT nextval('progression.affinity_records_id_seq'::regclass);


--
-- Name: game_events id; Type: DEFAULT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.game_events ALTER COLUMN id SET DEFAULT nextval('progression.game_events_id_seq'::regclass);


--
-- Name: mission_records id; Type: DEFAULT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.mission_records ALTER COLUMN id SET DEFAULT nextval('progression.mission_records_id_seq'::regclass);


--
-- Name: stage_progression id; Type: DEFAULT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.stage_progression ALTER COLUMN id SET DEFAULT nextval('progression.stage_progression_id_seq'::regclass);


--
-- Name: credit_transactions credit_transactions_pkey; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.credit_transactions
    ADD CONSTRAINT credit_transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: user_credits user_credits_pkey; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.user_credits
    ADD CONSTRAINT user_credits_pkey PRIMARY KEY (user_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: beat_goals beat_goals_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.beat_goals
    ADD CONSTRAINT beat_goals_pkey PRIMARY KEY (id);


--
-- Name: character_aliases character_aliases_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_aliases
    ADD CONSTRAINT character_aliases_pkey PRIMARY KEY (id);


--
-- Name: character_core_values character_core_values_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_core_values
    ADD CONSTRAINT character_core_values_pkey PRIMARY KEY (id);


--
-- Name: character_emotional_triggers character_emotional_triggers_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_emotional_triggers
    ADD CONSTRAINT character_emotional_triggers_pkey PRIMARY KEY (id);


--
-- Name: character_intent_rules character_intent_rules_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_intent_rules
    ADD CONSTRAINT character_intent_rules_pkey PRIMARY KEY (id);


--
-- Name: character_quotes character_quotes_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_quotes
    ADD CONSTRAINT character_quotes_pkey PRIMARY KEY (id);


--
-- Name: character_relationships character_relationships_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships
    ADD CONSTRAINT character_relationships_pkey PRIMARY KEY (id);


--
-- Name: character_tone character_tone_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_tone
    ADD CONSTRAINT character_tone_pkey PRIMARY KEY (id);


--
-- Name: characters characters_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.characters
    ADD CONSTRAINT characters_pkey PRIMARY KEY (character_id);


--
-- Name: image_mappings image_mappings_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.image_mappings
    ADD CONSTRAINT image_mappings_pkey PRIMARY KEY (id);


--
-- Name: rank_definitions rank_definitions_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.rank_definitions
    ADD CONSTRAINT rank_definitions_pkey PRIMARY KEY (rank_code);


--
-- Name: scenario_beats scenario_beats_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_beats
    ADD CONSTRAINT scenario_beats_pkey PRIMARY KEY (beat_id);


--
-- Name: scenario_statistics scenario_statistics_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_statistics
    ADD CONSTRAINT scenario_statistics_pkey PRIMARY KEY (scenario_id);


--
-- Name: scenario_views scenario_views_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_views
    ADD CONSTRAINT scenario_views_pkey PRIMARY KEY (view_id);


--
-- Name: scenarios scenarios_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenarios
    ADD CONSTRAINT scenarios_pkey PRIMARY KEY (scenario_id);


--
-- Name: character_aliases unique_alias; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_aliases
    ADD CONSTRAINT unique_alias UNIQUE (alias);


--
-- Name: character_intent_rules unique_char_rule; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_intent_rules
    ADD CONSTRAINT unique_char_rule UNIQUE (character_id, rule_category, rule_type);


--
-- Name: character_tone unique_char_tone; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_tone
    ADD CONSTRAINT unique_char_tone UNIQUE (character_id, affinity_level);


--
-- Name: character_relationships unique_scenario_char_rel; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships
    ADD CONSTRAINT unique_scenario_char_rel UNIQUE (scenario_id, character_id, target_character_id);


--
-- Name: image_mappings unique_scenario_image; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.image_mappings
    ADD CONSTRAINT unique_scenario_image UNIQUE (scenario_id, mapping_category, image_key);


--
-- Name: worlds worlds_pkey; Type: CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.worlds
    ADD CONSTRAINT worlds_pkey PRIMARY KEY (world_id);


--
-- Name: dialogues dialogues_pkey; Type: CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.dialogues
    ADD CONSTRAINT dialogues_pkey PRIMARY KEY (id);


--
-- Name: session_snapshots session_snapshots_pkey; Type: CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.session_snapshots
    ADD CONSTRAINT session_snapshots_pkey PRIMARY KEY (id);


--
-- Name: session_snapshots session_snapshots_session_id_turn_number_key; Type: CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.session_snapshots
    ADD CONSTRAINT session_snapshots_session_id_turn_number_key UNIQUE (session_id, turn_number);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


--
-- Name: user_inputs user_inputs_pkey; Type: CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.user_inputs
    ADD CONSTRAINT user_inputs_pkey PRIMARY KEY (id);


--
-- Name: entities entities_entity_type_canonical_name_key; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entities
    ADD CONSTRAINT entities_entity_type_canonical_name_key UNIQUE (entity_type, canonical_name);


--
-- Name: entities entities_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entities
    ADD CONSTRAINT entities_pkey PRIMARY KEY (entity_id);


--
-- Name: entity_mentions entity_mentions_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_mentions
    ADD CONSTRAINT entity_mentions_pkey PRIMARY KEY (mention_id);


--
-- Name: entity_relationships entity_relationships_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_relationships
    ADD CONSTRAINT entity_relationships_pkey PRIMARY KEY (relationship_id);


--
-- Name: entity_relationships entity_relationships_source_entity_id_target_entity_id_rela_key; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_relationships
    ADD CONSTRAINT entity_relationships_source_entity_id_target_entity_id_rela_key UNIQUE (source_entity_id, target_entity_id, relationship_type);


--
-- Name: user_memories unique_user_memory_key; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.user_memories
    ADD CONSTRAINT unique_user_memory_key UNIQUE (user_id, memory_key);


--
-- Name: user_memories user_memories_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.user_memories
    ADD CONSTRAINT user_memories_pkey PRIMARY KEY (id);


--
-- Name: training_logs training_logs_pkey; Type: CONSTRAINT; Schema: ml; Owner: kime
--

ALTER TABLE ONLY ml.training_logs
    ADD CONSTRAINT training_logs_pkey PRIMARY KEY (id);


--
-- Name: user_feedback user_feedback_pkey; Type: CONSTRAINT; Schema: ml; Owner: kime
--

ALTER TABLE ONLY ml.user_feedback
    ADD CONSTRAINT user_feedback_pkey PRIMARY KEY (id);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (id);


--
-- Name: performance_metrics performance_metrics_pkey; Type: CONSTRAINT; Schema: observability; Owner: kime
--

ALTER TABLE ONLY observability.performance_metrics
    ADD CONSTRAINT performance_metrics_pkey PRIMARY KEY (id);


--
-- Name: affinity_records affinity_records_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.affinity_records
    ADD CONSTRAINT affinity_records_pkey PRIMARY KEY (id);


--
-- Name: game_events game_events_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.game_events
    ADD CONSTRAINT game_events_pkey PRIMARY KEY (id);


--
-- Name: mission_records mission_records_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.mission_records
    ADD CONSTRAINT mission_records_pkey PRIMARY KEY (id);


--
-- Name: stage_progression stage_progression_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.stage_progression
    ADD CONSTRAINT stage_progression_pkey PRIMARY KEY (id);


--
-- Name: user_equipment user_equipment_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_equipment
    ADD CONSTRAINT user_equipment_pkey PRIMARY KEY (user_id);


--
-- Name: user_progression user_progression_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_progression
    ADD CONSTRAINT user_progression_pkey PRIMARY KEY (user_id);


--
-- Name: user_scenario_progress user_scenario_progress_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_scenario_progress
    ADD CONSTRAINT user_scenario_progress_pkey PRIMARY KEY (user_id, scenario_id);


--
-- Name: xp_transactions xp_transactions_pkey; Type: CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.xp_transactions
    ADD CONSTRAINT xp_transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: idx_credit_trans_created; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_credit_trans_created ON auth.credit_transactions USING btree (created_at DESC);


--
-- Name: idx_credit_trans_type; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_credit_trans_type ON auth.credit_transactions USING btree (transaction_type);


--
-- Name: idx_credit_trans_user; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_credit_trans_user ON auth.credit_transactions USING btree (user_id);


--
-- Name: idx_password_reset_tokens_expires_at; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_password_reset_tokens_expires_at ON auth.password_reset_tokens USING btree (expires_at);


--
-- Name: idx_password_reset_tokens_token; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_password_reset_tokens_token ON auth.password_reset_tokens USING btree (token);


--
-- Name: idx_password_reset_tokens_user_id; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_password_reset_tokens_user_id ON auth.password_reset_tokens USING btree (user_id);


--
-- Name: idx_user_credits_updated; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_user_credits_updated ON auth.user_credits USING btree (last_updated DESC);


--
-- Name: idx_user_credits_user; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_user_credits_user ON auth.user_credits USING btree (user_id);


--
-- Name: idx_users_active; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_users_active ON auth.users USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_users_created; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_users_created ON auth.users USING btree (created_at DESC);


--
-- Name: idx_users_email; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_users_email ON auth.users USING btree (email);


--
-- Name: idx_users_provider; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_users_provider ON auth.users USING btree (provider);


--
-- Name: idx_users_username; Type: INDEX; Schema: auth; Owner: kime
--

CREATE INDEX idx_users_username ON auth.users USING btree (username);


--
-- Name: idx_beat_goals_beat; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_beat_goals_beat ON content.beat_goals USING btree (beat_id);


--
-- Name: idx_char_rel_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_char_rel_char ON content.character_relationships USING btree (character_id);


--
-- Name: idx_char_rel_scenario; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_char_rel_scenario ON content.character_relationships USING btree (scenario_id);


--
-- Name: idx_character_aliases_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_aliases_char ON content.character_aliases USING btree (character_id);


--
-- Name: idx_character_core_values_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_core_values_char ON content.character_core_values USING btree (character_id);


--
-- Name: idx_character_intent_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_intent_char ON content.character_intent_rules USING btree (character_id);


--
-- Name: idx_character_quotes_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_quotes_char ON content.character_quotes USING btree (character_id);


--
-- Name: idx_character_tone_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_tone_char ON content.character_tone USING btree (character_id);


--
-- Name: idx_character_triggers_char; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_character_triggers_char ON content.character_emotional_triggers USING btree (character_id);


--
-- Name: idx_image_mappings_category; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_image_mappings_category ON content.image_mappings USING btree (mapping_category);


--
-- Name: idx_image_mappings_scenario; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_image_mappings_scenario ON content.image_mappings USING btree (scenario_id);


--
-- Name: idx_scenario_beats_parent; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenario_beats_parent ON content.scenario_beats USING btree (parent_beat_id);


--
-- Name: idx_scenario_beats_scenario; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenario_beats_scenario ON content.scenario_beats USING btree (scenario_id);


--
-- Name: idx_scenario_views_scenario; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenario_views_scenario ON content.scenario_views USING btree (scenario_id, viewed_at DESC);


--
-- Name: idx_scenario_views_user; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenario_views_user ON content.scenario_views USING btree (user_id, viewed_at DESC) WHERE (user_id IS NOT NULL);


--
-- Name: idx_scenarios_active_order; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenarios_active_order ON content.scenarios USING btree (is_active, display_order) WHERE (is_active = true);


--
-- Name: idx_scenarios_id; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenarios_id ON content.scenarios USING btree (scenario_id);


--
-- Name: idx_scenarios_world; Type: INDEX; Schema: content; Owner: kime
--

CREATE INDEX idx_scenarios_world ON content.scenarios USING btree (world_id);


--
-- Name: idx_dialogues_entities; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_dialogues_entities ON conversation.dialogues USING gin (mentioned_entity_ids);


--
-- Name: idx_dialogues_session; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_dialogues_session ON conversation.dialogues USING btree (session_id, turn_number, order_index);


--
-- Name: idx_dialogues_speaker; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_dialogues_speaker ON conversation.dialogues USING btree (speaker);


--
-- Name: idx_dialogues_timestamp; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_dialogues_timestamp ON conversation.dialogues USING btree ("timestamp" DESC);


--
-- Name: idx_sessions_active; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_sessions_active ON conversation.sessions USING btree (is_active) WHERE (is_active = true);


--
-- Name: idx_sessions_created; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_sessions_created ON conversation.sessions USING btree (created_at DESC);


--
-- Name: idx_sessions_scenario; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_sessions_scenario ON conversation.sessions USING btree (scenario_id);


--
-- Name: idx_sessions_user; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_sessions_user ON conversation.sessions USING btree (user_id);


--
-- Name: idx_snapshots_created; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_snapshots_created ON conversation.session_snapshots USING btree (created_at DESC);


--
-- Name: idx_snapshots_session; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_snapshots_session ON conversation.session_snapshots USING btree (session_id, turn_number DESC);


--
-- Name: idx_user_inputs_session; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_user_inputs_session ON conversation.user_inputs USING btree (session_id, turn_number DESC);


--
-- Name: idx_user_inputs_timestamp; Type: INDEX; Schema: conversation; Owner: kime
--

CREATE INDEX idx_user_inputs_timestamp ON conversation.user_inputs USING btree ("timestamp" DESC);


--
-- Name: idx_entities_canonical_name; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_canonical_name ON knowledge.entities USING btree (canonical_name);


--
-- Name: idx_entities_community; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_community ON knowledge.entities USING btree (community_id) WHERE (community_id IS NOT NULL);


--
-- Name: idx_entities_embedding; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_embedding ON knowledge.entities USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: INDEX idx_entities_embedding; Type: COMMENT; Schema: knowledge; Owner: kime
--

COMMENT ON INDEX knowledge.idx_entities_embedding IS 'IVFFlat index for fast cosine similarity search';


--
-- Name: idx_entities_importance; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_importance ON knowledge.entities USING btree (importance_score DESC);


--
-- Name: idx_entities_mention_count; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_mention_count ON knowledge.entities USING btree (mention_count DESC);


--
-- Name: idx_entities_type; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_entities_type ON knowledge.entities USING btree (entity_type);


--
-- Name: idx_mentions_entity; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_mentions_entity ON knowledge.entity_mentions USING btree (entity_id);


--
-- Name: idx_mentions_session; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_mentions_session ON knowledge.entity_mentions USING btree (session_id) WHERE (session_id IS NOT NULL);


--
-- Name: idx_mentions_source; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_mentions_source ON knowledge.entity_mentions USING btree (source_type, source_id);


--
-- Name: idx_relationships_source; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_relationships_source ON knowledge.entity_relationships USING btree (source_entity_id);


--
-- Name: idx_relationships_strength; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_relationships_strength ON knowledge.entity_relationships USING btree (strength DESC);


--
-- Name: idx_relationships_target; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_relationships_target ON knowledge.entity_relationships USING btree (target_entity_id);


--
-- Name: idx_relationships_type; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_relationships_type ON knowledge.entity_relationships USING btree (relationship_type);


--
-- Name: idx_user_memories_active_recent; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_active_recent ON knowledge.user_memories USING btree (user_id, last_accessed_at DESC) WHERE (is_active = true);


--
-- Name: idx_user_memories_context_gin; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_context_gin ON knowledge.user_memories USING gin (context);


--
-- Name: idx_user_memories_entities; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_entities ON knowledge.user_memories USING gin (related_entity_ids);


--
-- Name: idx_user_memories_importance; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_importance ON knowledge.user_memories USING btree (importance DESC) WHERE (is_active = true);


--
-- Name: idx_user_memories_memory_type; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_memory_type ON knowledge.user_memories USING btree (memory_type);


--
-- Name: idx_user_memories_source_session; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_source_session ON knowledge.user_memories USING btree (source_session_id);


--
-- Name: idx_user_memories_tags_gin; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_tags_gin ON knowledge.user_memories USING gin (tags);


--
-- Name: idx_user_memories_user_id; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_user_id ON knowledge.user_memories USING btree (user_id);


--
-- Name: idx_user_memories_user_importance; Type: INDEX; Schema: knowledge; Owner: kime
--

CREATE INDEX idx_user_memories_user_importance ON knowledge.user_memories USING btree (user_id, importance DESC) WHERE (is_active = true);


--
-- Name: idx_training_logs_agent_name; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_agent_name ON ml.training_logs USING btree (agent_name);


--
-- Name: idx_training_logs_agent_outcome_time; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_agent_outcome_time ON ml.training_logs USING btree (agent_name, outcome, created_at DESC);


--
-- Name: idx_training_logs_context_gin; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_context_gin ON ml.training_logs USING gin (context);


--
-- Name: idx_training_logs_created_at; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_created_at ON ml.training_logs USING btree (created_at DESC);


--
-- Name: idx_training_logs_entities; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_entities ON ml.training_logs USING gin (mentioned_entity_ids);


--
-- Name: idx_training_logs_model_output_gin; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_model_output_gin ON ml.training_logs USING gin (model_output);


--
-- Name: idx_training_logs_outcome; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_outcome ON ml.training_logs USING btree (outcome) WHERE (outcome IS NOT NULL);


--
-- Name: idx_training_logs_session_id; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_training_logs_session_id ON ml.training_logs USING btree (session_id);


--
-- Name: idx_user_feedback_created_at; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_user_feedback_created_at ON ml.user_feedback USING btree (created_at DESC);


--
-- Name: idx_user_feedback_log_id; Type: INDEX; Schema: ml; Owner: kime
--

CREATE INDEX idx_user_feedback_log_id ON ml.user_feedback USING btree (training_log_id);


--
-- Name: idx_error_logs_session; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_error_logs_session ON observability.error_logs USING btree (session_id);


--
-- Name: idx_error_logs_timestamp; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_error_logs_timestamp ON observability.error_logs USING btree ("timestamp" DESC);


--
-- Name: idx_error_logs_type; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_error_logs_type ON observability.error_logs USING btree (error_type);


--
-- Name: idx_logs_agent; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_agent ON observability.logs USING btree (agent_name);


--
-- Name: idx_logs_context; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_context ON observability.logs USING gin (context_data);


--
-- Name: idx_logs_level; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_level ON observability.logs USING btree (log_level);


--
-- Name: idx_logs_session; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_session ON observability.logs USING btree (session_id);


--
-- Name: idx_logs_stage; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_stage ON observability.logs USING btree (stage_name);


--
-- Name: idx_logs_timestamp; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_logs_timestamp ON observability.logs USING btree ("timestamp" DESC);


--
-- Name: idx_metrics_name; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_metrics_name ON observability.performance_metrics USING btree (metric_name, "timestamp" DESC);


--
-- Name: idx_metrics_tags; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_metrics_tags ON observability.performance_metrics USING gin (tags);


--
-- Name: idx_metrics_timestamp; Type: INDEX; Schema: observability; Owner: kime
--

CREATE INDEX idx_metrics_timestamp ON observability.performance_metrics USING btree ("timestamp" DESC);


--
-- Name: idx_affinity_character; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_affinity_character ON progression.affinity_records USING btree (character_name);


--
-- Name: idx_affinity_session; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_affinity_session ON progression.affinity_records USING btree (session_id, character_name);


--
-- Name: idx_affinity_timestamp; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_affinity_timestamp ON progression.affinity_records USING btree ("timestamp" DESC);


--
-- Name: idx_events_data; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_events_data ON progression.game_events USING gin (event_data);


--
-- Name: idx_events_session; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_events_session ON progression.game_events USING btree (session_id, turn_number DESC);


--
-- Name: idx_events_type; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_events_type ON progression.game_events USING btree (event_type);


--
-- Name: idx_mission_character; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_mission_character ON progression.mission_records USING btree (target_character);


--
-- Name: idx_mission_session; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_mission_session ON progression.mission_records USING btree (session_id);


--
-- Name: idx_mission_type; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_mission_type ON progression.mission_records USING btree (mission_type);


--
-- Name: idx_stage_active; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_stage_active ON progression.stage_progression USING btree (session_id) WHERE (exited_at IS NULL);


--
-- Name: idx_stage_id; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_stage_id ON progression.stage_progression USING btree (stage_id);


--
-- Name: idx_stage_session; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_stage_session ON progression.stage_progression USING btree (session_id, stage_order DESC);


--
-- Name: idx_user_progression_level; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_user_progression_level ON progression.user_progression USING btree (level DESC);


--
-- Name: idx_user_progression_xp; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_user_progression_xp ON progression.user_progression USING btree (experience_points DESC);


--
-- Name: idx_user_scenario_progress_liked; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_user_scenario_progress_liked ON progression.user_scenario_progress USING btree (user_id, is_liked) WHERE (is_liked = true);


--
-- Name: idx_user_scenario_progress_user; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_user_scenario_progress_user ON progression.user_scenario_progress USING btree (user_id);


--
-- Name: idx_xp_transactions_type; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_xp_transactions_type ON progression.xp_transactions USING btree (xp_type);


--
-- Name: idx_xp_transactions_user_id; Type: INDEX; Schema: progression; Owner: kime
--

CREATE INDEX idx_xp_transactions_user_id ON progression.xp_transactions USING btree (user_id, created_at DESC);


--
-- Name: create_initial_credits(); Type: FUNCTION; Schema: public; Owner: kime
--

CREATE OR REPLACE FUNCTION public.create_initial_credits()
RETURNS TRIGGER AS $$
BEGIN
    -- 신규 사용자에게 100 버블 지급
    INSERT INTO auth.user_credits (user_id, bubble_count, total_purchased, total_consumed)
    VALUES (NEW.user_id, 100, 100, 0);

    -- 초기 지급 트랜잭션 기록
    INSERT INTO auth.credit_transactions (user_id, amount, transaction_type, balance_after, description)
    VALUES (NEW.user_id, 100, 'initial', 100, '신규 가입 환영 버블');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


--
-- Name: users trigger_create_credits; Type: TRIGGER; Schema: auth; Owner: kime
--

CREATE TRIGGER trigger_create_credits AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.create_initial_credits();


--
-- Name: create_user_progression(); Type: FUNCTION; Schema: public; Owner: kime
--

CREATE OR REPLACE FUNCTION public.create_user_progression()
RETURNS TRIGGER AS $$
BEGIN
    -- user_progression 초기화 (계급은 MIZUNOTO로 시작)
    INSERT INTO progression.user_progression (user_id, rank_code, experience_points, level)
    VALUES (NEW.user_id, 'MIZUNOTO', 0, 1);

    -- user_equipment 초기화
    INSERT INTO progression.user_equipment (user_id, sword_status, uniform_status, crow_status)
    VALUES (NEW.user_id, 'good', 'worn', 'waiting');

    -- 초기 XP 거래 기록
    INSERT INTO progression.xp_transactions (user_id, xp_amount, xp_type, xp_balance_after, level_before, level_after, description)
    VALUES (NEW.user_id, 0, 'event', 0, 1, 1, '귀살대 입문 - 계급 계(癸) 부여');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


--
-- Name: users trigger_create_user_progression; Type: TRIGGER; Schema: auth; Owner: kime
--

CREATE TRIGGER trigger_create_user_progression AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.create_user_progression();


--
-- Name: scenario_views trg_increment_scenario_views; Type: TRIGGER; Schema: content; Owner: kime
--

-- CREATE TRIGGER trg_increment_scenario_views AFTER INSERT ON content.scenario_views FOR EACH ROW EXECUTE FUNCTION statedb.increment_scenario_view_count();


--
-- Name: characters trg_update_character_timestamp; Type: TRIGGER; Schema: content; Owner: kime
--

-- CREATE TRIGGER trg_update_character_timestamp BEFORE UPDATE ON content.characters FOR EACH ROW EXECUTE FUNCTION statedb.update_character_updated_at();


--
-- Name: scenarios trg_update_scenario_timestamps; Type: TRIGGER; Schema: content; Owner: kime
--

-- CREATE TRIGGER trg_update_scenario_timestamps BEFORE UPDATE ON content.scenarios FOR EACH ROW EXECUTE FUNCTION statedb.update_scenario_timestamps();


--
-- Name: user_memories trigger_user_memories_updated_at; Type: TRIGGER; Schema: knowledge; Owner: kime
--

-- CREATE TRIGGER trigger_user_memories_updated_at BEFORE UPDATE ON knowledge.user_memories FOR EACH ROW EXECUTE FUNCTION statedb.update_user_memories_timestamp();


--
-- Name: user_scenario_progress trg_update_scenario_likes; Type: TRIGGER; Schema: progression; Owner: kime
--

-- CREATE TRIGGER trg_update_scenario_likes AFTER INSERT OR UPDATE OF is_liked ON progression.user_scenario_progress FOR EACH ROW EXECUTE FUNCTION statedb.update_scenario_like_count();


--
-- Name: credit_transactions credit_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.credit_transactions
    ADD CONSTRAINT credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: user_credits user_credits_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: kime
--

ALTER TABLE ONLY auth.user_credits
    ADD CONSTRAINT user_credits_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: beat_goals beat_goals_beat_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.beat_goals
    ADD CONSTRAINT beat_goals_beat_id_fkey FOREIGN KEY (beat_id) REFERENCES content.scenario_beats(beat_id) ON DELETE CASCADE;


--
-- Name: character_aliases character_aliases_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_aliases
    ADD CONSTRAINT character_aliases_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_core_values character_core_values_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_core_values
    ADD CONSTRAINT character_core_values_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_emotional_triggers character_emotional_triggers_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_emotional_triggers
    ADD CONSTRAINT character_emotional_triggers_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_intent_rules character_intent_rules_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_intent_rules
    ADD CONSTRAINT character_intent_rules_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_quotes character_quotes_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_quotes
    ADD CONSTRAINT character_quotes_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_relationships character_relationships_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships
    ADD CONSTRAINT character_relationships_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_relationships character_relationships_scenario_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships
    ADD CONSTRAINT character_relationships_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: character_relationships character_relationships_target_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_relationships
    ADD CONSTRAINT character_relationships_target_character_id_fkey FOREIGN KEY (target_character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: character_tone character_tone_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.character_tone
    ADD CONSTRAINT character_tone_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.characters(character_id) ON DELETE CASCADE;


--
-- Name: image_mappings image_mappings_scenario_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.image_mappings
    ADD CONSTRAINT image_mappings_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenario_beats scenario_beats_scenario_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_beats
    ADD CONSTRAINT scenario_beats_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenario_statistics scenario_statistics_scenario_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_statistics
    ADD CONSTRAINT scenario_statistics_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenario_views scenario_views_scenario_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_views
    ADD CONSTRAINT scenario_views_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: scenario_views scenario_views_user_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenario_views
    ADD CONSTRAINT scenario_views_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE SET NULL;


--
-- Name: scenarios scenarios_world_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: kime
--

ALTER TABLE ONLY content.scenarios
    ADD CONSTRAINT scenarios_world_id_fkey FOREIGN KEY (world_id) REFERENCES content.worlds(world_id);


--
-- Name: dialogues dialogues_session_id_fkey; Type: FK CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.dialogues
    ADD CONSTRAINT dialogues_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: session_snapshots session_snapshots_session_id_fkey; Type: FK CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.session_snapshots
    ADD CONSTRAINT session_snapshots_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE SET NULL;


--
-- Name: user_inputs user_inputs_session_id_fkey; Type: FK CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.user_inputs
    ADD CONSTRAINT user_inputs_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;

--
-- Name: user_inputs user_inputs_user_id_fkey; Type: FK CONSTRAINT; Schema: conversation; Owner: kime
--

ALTER TABLE ONLY conversation.user_inputs
    ADD CONSTRAINT user_inputs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE SET NULL;


--
-- Name: entity_mentions entity_mentions_entity_id_fkey; Type: FK CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_mentions
    ADD CONSTRAINT entity_mentions_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES knowledge.entities(entity_id) ON DELETE CASCADE;


--
-- Name: entity_relationships entity_relationships_source_entity_id_fkey; Type: FK CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_relationships
    ADD CONSTRAINT entity_relationships_source_entity_id_fkey FOREIGN KEY (source_entity_id) REFERENCES knowledge.entities(entity_id) ON DELETE CASCADE;


--
-- Name: entity_relationships entity_relationships_target_entity_id_fkey; Type: FK CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.entity_relationships
    ADD CONSTRAINT entity_relationships_target_entity_id_fkey FOREIGN KEY (target_entity_id) REFERENCES knowledge.entities(entity_id) ON DELETE CASCADE;


--
-- Name: user_memories user_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: knowledge; Owner: kime
--

ALTER TABLE ONLY knowledge.user_memories
    ADD CONSTRAINT user_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: user_feedback user_feedback_training_log_id_fkey; Type: FK CONSTRAINT; Schema: ml; Owner: kime
--

ALTER TABLE ONLY ml.user_feedback
    ADD CONSTRAINT user_feedback_training_log_id_fkey FOREIGN KEY (training_log_id) REFERENCES ml.training_logs(id) ON DELETE CASCADE;


--
-- Name: affinity_records affinity_records_session_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.affinity_records
    ADD CONSTRAINT affinity_records_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: game_events game_events_session_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.game_events
    ADD CONSTRAINT game_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: mission_records mission_records_session_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.mission_records
    ADD CONSTRAINT mission_records_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: stage_progression stage_progression_session_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.stage_progression
    ADD CONSTRAINT stage_progression_session_id_fkey FOREIGN KEY (session_id) REFERENCES conversation.sessions(session_id) ON DELETE CASCADE;


--
-- Name: user_equipment user_equipment_user_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_equipment
    ADD CONSTRAINT user_equipment_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: user_progression user_progression_rank_code_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_progression
    ADD CONSTRAINT user_progression_rank_code_fkey FOREIGN KEY (rank_code) REFERENCES content.rank_definitions(rank_code);


--
-- Name: user_progression user_progression_user_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_progression
    ADD CONSTRAINT user_progression_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: user_scenario_progress user_scenario_progress_scenario_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_scenario_progress
    ADD CONSTRAINT user_scenario_progress_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES content.scenarios(scenario_id) ON DELETE CASCADE;


--
-- Name: user_scenario_progress user_scenario_progress_user_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.user_scenario_progress
    ADD CONSTRAINT user_scenario_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: xp_transactions xp_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: progression; Owner: kime
--

ALTER TABLE ONLY progression.xp_transactions
    ADD CONSTRAINT xp_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(user_id) ON DELETE CASCADE;


--
-- Name: TABLE scenario_statistics; Type: ACL; Schema: content; Owner: kime
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE content.scenario_statistics TO PUBLIC;


--
-- Name: TABLE scenario_views; Type: ACL; Schema: content; Owner: kime
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE content.scenario_views TO PUBLIC;


--
-- Name: TABLE scenarios; Type: ACL; Schema: content; Owner: kime
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE content.scenarios TO PUBLIC;


--
-- Name: TABLE v_scenario_cards; Type: ACL; Schema: content; Owner: kime
--

GRANT SELECT ON TABLE content.v_scenario_cards TO PUBLIC;


--
-- Name: TABLE user_scenario_progress; Type: ACL; Schema: progression; Owner: kime
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE progression.user_scenario_progress TO PUBLIC;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: auth; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA auth GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: content; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA content GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: conversation; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA conversation GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: knowledge; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA knowledge GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: ml; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA ml GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: observability; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA observability GRANT ALL ON TABLES  TO kime;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: progression; Owner: kime
--

ALTER DEFAULT PRIVILEGES FOR ROLE kime IN SCHEMA progression GRANT ALL ON TABLES  TO kime;


--
-- PostgreSQL database dump complete
--
