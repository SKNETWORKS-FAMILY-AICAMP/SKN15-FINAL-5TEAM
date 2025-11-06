-- ============================================================================
-- Schema Refactoring: Step 1 - Create New Schemas
-- ============================================================================
-- Purpose: Create 7 domain-based schemas to replace statedb/logdb/public
-- Date: 2025-11-06
-- Safe to run: YES (creates only, no drops)
-- ============================================================================

-- ============================================================================
-- 1. Create New Schemas
-- ============================================================================

-- Authentication & User Management
CREATE SCHEMA IF NOT EXISTS auth;
COMMENT ON SCHEMA auth IS 'User authentication, accounts, and credits';

-- Conversation & Chat System
CREATE SCHEMA IF NOT EXISTS conversation;
COMMENT ON SCHEMA conversation IS 'Chat sessions, dialogues, and user inputs';

-- Knowledge Graph & Long-term Memory
CREATE SCHEMA IF NOT EXISTS knowledge;
COMMENT ON SCHEMA knowledge IS 'Graph RAG: entities, relationships, and memories';

-- Game Content & Scenarios
CREATE SCHEMA IF NOT EXISTS content;
COMMENT ON SCHEMA content IS 'Scenarios, ranks, and game content metadata';

-- User Progression & Gameplay
CREATE SCHEMA IF NOT EXISTS progression;
COMMENT ON SCHEMA progression IS 'User progress, equipment, missions, and gameplay data';

-- System Observability
CREATE SCHEMA IF NOT EXISTS observability;
COMMENT ON SCHEMA observability IS 'Logs, errors, and performance metrics';

-- Machine Learning & Training
CREATE SCHEMA IF NOT EXISTS ml;
COMMENT ON SCHEMA ml IS 'AI training logs, feedback, and model evaluations';

-- ============================================================================
-- 2. Grant Permissions
-- ============================================================================

GRANT ALL ON SCHEMA auth TO kime;
GRANT ALL ON SCHEMA conversation TO kime;
GRANT ALL ON SCHEMA knowledge TO kime;
GRANT ALL ON SCHEMA content TO kime;
GRANT ALL ON SCHEMA progression TO kime;
GRANT ALL ON SCHEMA observability TO kime;
GRANT ALL ON SCHEMA ml TO kime;

-- ============================================================================
-- 3. Set Default Privileges (for future tables)
-- ============================================================================

ALTER DEFAULT PRIVILEGES IN SCHEMA auth
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA conversation
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA knowledge
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA content
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA progression
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA observability
  GRANT ALL ON TABLES TO kime;

ALTER DEFAULT PRIVILEGES IN SCHEMA ml
  GRANT ALL ON TABLES TO kime;

-- ============================================================================
-- 4. Verification
-- ============================================================================

\echo '✅ New schemas created successfully!'
\echo ''
\echo 'Schemas:'
SELECT nspname AS schema_name,
       pg_catalog.pg_get_userbyid(nspowner) AS owner,
       obj_description(oid, 'pg_namespace') AS description
FROM pg_namespace
WHERE nspname IN ('auth', 'conversation', 'knowledge', 'content',
                  'progression', 'observability', 'ml')
ORDER BY nspname;
