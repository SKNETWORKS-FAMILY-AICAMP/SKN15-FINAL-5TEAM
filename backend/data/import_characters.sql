-- ============================================================
-- 캐릭터 데이터 Import SQL
-- Generated from: backend/data/characters/*.json
-- ============================================================

SET search_path TO public;

-- 카마도 탄지로
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'tanjiro',
    '카마도 탄지로',
    '정직하고 배려심 깊음. 동료애가 강함',
    'compassionate, determined, empathetic, strong-willed',
    '{"breathing_style": "물의 호흡", "default_affinity": 500}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 카마도 네즈코
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'nezuko',
    '카마도 네즈코',
    '탄지로의 여동생. 귀신이 되었지만 인간성을 유지',
    'protective, caring, fierce when protecting loved ones',
    '{"demon_state": true, "blood_demon_art": "폭혈"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 아가츠마 젠이츠
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'zenitsu',
    '아가츠마 젠이츠',
    '겁이 많지만 위기의 순간 강력한 힘을 발휘',
    'cowardly, loyal, powerful when asleep',
    '{"breathing_style": "뇌의 호흡", "special_skill": "수면 전투"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 하시비라 이노스케
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'inosuke',
    '하시비라 이노스케',
    '산에서 자란 야성적인 성격. 멧돼지 가면 착용',
    'wild, aggressive, competitive, loyal',
    '{"breathing_style": "짐승의 호흡", "special_item": "멧돼지 가면"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 렌고쿠 쿄쥬로
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'rengoku',
    '렌고쿠 쿄쥬로',
    '염주. 정의감이 강하고 열정적',
    'passionate, righteous, inspiring, protective',
    '{"breathing_style": "염의 호흡", "rank": "하시라", "title": "염주"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 아카자
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'akaza',
    '아카자',
    '상현의 참. 강자를 추구하는 무술가',
    'honorable warrior, respects strength, tragic past',
    '{"rank": "상현의 참", "blood_demon_art": "파괴살", "type": "demon"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

-- 엔무
INSERT INTO public.characters (
    character_id,
    name,
    description,
    personality,
    metadata
) VALUES (
    'enmu',
    '엔무',
    '하현의 일. 꿈을 조종하는 능력',
    'sadistic, cunning, obsessed with nightmares',
    '{"rank": "하현의 일", "blood_demon_art": "강제 혼면", "type": "demon"}'::jsonb
) ON CONFLICT (character_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    personality = EXCLUDED.personality,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;

SELECT character_id, name, personality FROM public.characters ORDER BY character_id;
