-- ============================================================================
-- Migration 014: Logical Schemas for Backend Search Path
-- ============================================================================
-- Purpose:
--   The Python backend always sets `search_path` to
--   auth, conversation, knowledge, content, progression, observability, ml, public
--   but the existing tables live in `statedb` (and `logdb` for logs).
--   This migration creates the expected schemas and lightweight updatable views
--   so that `auth.users` → `statedb.users`, etc. without duplicating data.
-- ============================================================================

-- Ensure schemas exist -------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS conversation;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS progression;
CREATE SCHEMA IF NOT EXISTS observability;
CREATE SCHEMA IF NOT EXISTS ml;

-- ============================================================================
-- Auth schema aliases
-- ============================================================================
CREATE OR REPLACE VIEW auth.users AS SELECT * FROM statedb.users;
CREATE OR REPLACE VIEW auth.password_reset_tokens AS SELECT * FROM statedb.password_reset_tokens;
CREATE OR REPLACE VIEW auth.user_credits AS SELECT * FROM statedb.user_credits;
CREATE OR REPLACE VIEW auth.credit_transactions AS SELECT * FROM statedb.credit_transactions;

-- ============================================================================
-- Conversation schema aliases
-- ============================================================================
CREATE OR REPLACE VIEW conversation.sessions AS SELECT * FROM statedb.sessions;
CREATE OR REPLACE VIEW conversation.user_inputs AS SELECT * FROM statedb.user_inputs;
CREATE OR REPLACE VIEW conversation.dialogues AS SELECT * FROM statedb.dialogues;
CREATE OR REPLACE VIEW conversation.session_snapshots AS SELECT * FROM statedb.session_snapshots;

-- ============================================================================
-- Knowledge schema aliases
-- ============================================================================
CREATE OR REPLACE VIEW knowledge.user_memories AS SELECT * FROM statedb.user_memories;
CREATE OR REPLACE VIEW knowledge.entities AS SELECT * FROM statedb.entities;
CREATE OR REPLACE VIEW knowledge.entity_relationships AS SELECT * FROM statedb.entity_relationships;
CREATE OR REPLACE VIEW knowledge.entity_mentions AS SELECT * FROM statedb.entity_mentions;

-- ============================================================================
-- Progression schema aliases
-- ============================================================================
CREATE OR REPLACE VIEW progression.affinity_records AS SELECT * FROM statedb.affinity_records;
CREATE OR REPLACE VIEW progression.stage_progression AS SELECT * FROM statedb.stage_progression;
CREATE OR REPLACE VIEW progression.game_events AS SELECT * FROM statedb.game_events;
CREATE OR REPLACE VIEW progression.mission_records AS SELECT * FROM statedb.mission_records;
CREATE OR REPLACE VIEW progression.rank_definitions AS SELECT * FROM statedb.rank_definitions;
CREATE OR REPLACE VIEW progression.user_progression AS SELECT * FROM statedb.user_progression;
CREATE OR REPLACE VIEW progression.user_equipment AS SELECT * FROM statedb.user_equipment;
CREATE OR REPLACE VIEW progression.xp_transactions AS SELECT * FROM statedb.xp_transactions;
CREATE OR REPLACE VIEW progression.user_scenario_progress AS SELECT * FROM statedb.user_scenario_progress;
CREATE OR REPLACE VIEW progression.v_user_progression_summary AS SELECT * FROM statedb.v_user_progression_summary;

-- ============================================================================
-- Content schema aliases
-- ============================================================================
CREATE OR REPLACE VIEW content.scenarios AS SELECT * FROM statedb.scenarios;
CREATE OR REPLACE VIEW content.scenario_statistics AS SELECT * FROM statedb.scenario_statistics;
CREATE OR REPLACE VIEW content.scenario_views AS SELECT * FROM statedb.scenario_views;
CREATE OR REPLACE VIEW content.v_scenario_cards AS SELECT * FROM statedb.v_scenario_cards;
CREATE OR REPLACE VIEW content.rank_definitions AS SELECT * FROM statedb.rank_definitions;

-- ============================================================================
-- Observability schema aliases (maps onto logdb)
-- ============================================================================
CREATE OR REPLACE VIEW observability.logs AS SELECT * FROM logdb.logs;
CREATE OR REPLACE VIEW observability.error_logs AS SELECT * FROM logdb.error_logs;
CREATE OR REPLACE VIEW observability.performance_metrics AS SELECT * FROM logdb.performance_metrics;

-- ============================================================================
-- Notes:
-- - Views are simple SELECT * wrappers, so they remain fully updatable
--   (INSERT/UPDATE/DELETE) and reuse the same indexes/storage as the base tables.
-- - Additional content tables such as character profiles, beats, or image mappings
--   still need dedicated migrations; once created under statedb they can be exposed
--   the same way.
-- ============================================================================
