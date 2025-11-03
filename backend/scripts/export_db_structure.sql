-- DB 구조 전체 추출 스크립트

-- 1. 모든 테이블 구조
\echo '===== TABLE STRUCTURES ====='
\d statedb.sessions
\d statedb.users
\d statedb.entities
\d statedb.entity_mentions
\d statedb.entity_relationships
\d statedb.dialogues
\d statedb.user_inputs
\d statedb.user_memories
\d statedb.affinity_records
\d statedb.game_events
\d statedb.mission_records
\d statedb.stage_progression
\d statedb.session_snapshots
\d statedb.password_reset_tokens
\d public.training_logs
\d public.user_feedback
\d logdb.logs
\d logdb.error_logs
\d logdb.performance_metrics

-- 2. 외래키 관계
\echo '===== FOREIGN KEY RELATIONSHIPS ====='
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema IN ('statedb', 'public', 'logdb')
ORDER BY tc.table_schema, tc.table_name;
