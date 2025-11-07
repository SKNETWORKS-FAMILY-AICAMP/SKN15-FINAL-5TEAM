-- ============================================================
-- 전체 데이터 Import SQL (Master Script)
-- ============================================================

SET search_path TO public;

\i import_worlds.sql
\i import_characters.sql
\i import_scenarios.sql

SELECT COUNT(*) as world_count FROM public.worlds;
SELECT COUNT(*) as character_count FROM public.characters;
SELECT COUNT(*) as scenario_count FROM public.scenarios;
