-- ============================================================
-- 시나리오 데이터 Import SQL
-- Generated from: backend/data/scenarios/*.json
-- ============================================================

SET search_path TO public;

-- 🔥 무한열차
INSERT INTO public.scenarios (
    scenario_id,
    title,
    description,
    version,
    world_id,
    mountable,
    character_refs,
    i18n,
    stages,
    metadata,
    image_url,
    thumbnail_url,
    tags,
    route_path,
    card_size,
    display_order
) VALUES (
    'cutscene5_llm_driven',
    '🔥 무한열차',
    '갈림길→전략 개입→동료 규합→보스 퇴장 시네마틱→판정→히든/기본 엔딩',
    '6.0',
    'demon_slayer_taisho',
    true,
    '{"rengoku": "backend/data/characters/rengoku.json", "tanjiro": "backend/data/characters/tanjiro.json", "akaza": "backend/data/characters/akaza.json", "zenitsu": "backend/data/characters/zenitsu.json", "inosuke": "backend/data/characters/inosuke.json", "nezuko": "backend/data/characters/nezuko.json", "enmu": "backend/data/characters/enmu.json"}'::jsonb,
    (SELECT i18n FROM (VALUES ('{}'::jsonb)) AS dummy(i18n)),
    (SELECT stages FROM (VALUES ('[]'::jsonb)) AS dummy(stages)),
    (SELECT metadata FROM (VALUES ('{}'::jsonb)) AS dummy(metadata)),
    '/images/무한열차.jpeg',
    '/images/무한열차.jpeg',
    ARRAY['무한열차', '꿈속전투', '엔무'],
    '/character/train',
    'normal',
    2
) ON CONFLICT (scenario_id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    version = EXCLUDED.version,
    world_id = EXCLUDED.world_id,
    mountable = EXCLUDED.mountable,
    character_refs = EXCLUDED.character_refs,
    image_url = EXCLUDED.image_url,
    thumbnail_url = EXCLUDED.thumbnail_url,
    tags = EXCLUDED.tags,
    route_path = EXCLUDED.route_path,
    card_size = EXCLUDED.card_size,
    display_order = EXCLUDED.display_order,
    updated_at = CURRENT_TIMESTAMP;

SELECT scenario_id, title, description, version FROM public.scenarios;
