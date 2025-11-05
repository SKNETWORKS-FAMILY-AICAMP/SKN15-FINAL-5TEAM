-- ============================================================
-- KIME Chat Database Schema
-- JSON 데이터 구조 기반으로 설계된 데이터베이스 스키마
-- ============================================================

-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 스키마 생성
CREATE SCHEMA IF NOT EXISTS public;

-- 권한 설정
GRANT ALL PRIVILEGES ON SCHEMA public TO kime;

-- search_path 설정
SET search_path TO public;
ALTER DATABASE kimedb SET search_path TO public;

-- ============================================================
-- 1. 세계관 (Worlds) 테이블
-- ============================================================

DROP TABLE IF EXISTS public.worlds CASCADE;

CREATE TABLE public.worlds (
    world_id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    world_context TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_worlds_active ON public.worlds(is_active);
CREATE INDEX idx_worlds_metadata ON public.worlds USING gin(metadata);

-- ============================================================
-- 2. 캐릭터 (Characters) 테이블
-- ============================================================

DROP TABLE IF EXISTS public.characters CASCADE;

CREATE TABLE public.characters (
    character_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    personality TEXT,
    appearance JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    intent_rules JSONB DEFAULT '{}'::jsonb,
    character_traits JSONB DEFAULT '{}'::jsonb,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_characters_active ON public.characters(is_active);
CREATE INDEX idx_characters_metadata ON public.characters USING gin(metadata);
CREATE INDEX idx_characters_intent_rules ON public.characters USING gin(intent_rules);
CREATE INDEX idx_characters_traits ON public.characters USING gin(character_traits);

-- ============================================================
-- 3. 시나리오 (Scenarios) 테이블
-- ============================================================

DROP TABLE IF EXISTS public.scenarios CASCADE;

CREATE TABLE public.scenarios (
    scenario_id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(20),
    world_id VARCHAR(100) REFERENCES public.worlds(world_id),
    mountable BOOLEAN DEFAULT true,
    character_refs JSONB DEFAULT '{}'::jsonb,
    i18n JSONB DEFAULT '{}'::jsonb,
    stages JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    card_size VARCHAR(20) DEFAULT 'normal',
    display_order INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    route_path VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scenarios_world ON public.scenarios(world_id);
CREATE INDEX idx_scenarios_active ON public.scenarios(is_active);
CREATE INDEX idx_scenarios_display_order ON public.scenarios(display_order);
CREATE INDEX idx_scenarios_tags ON public.scenarios USING gin(tags);
CREATE INDEX idx_scenarios_metadata ON public.scenarios USING gin(metadata);
CREATE INDEX idx_scenarios_stages ON public.scenarios USING gin(stages);

-- ============================================================
-- 4. 시나리오 통계 (Scenario Statistics) 테이블
-- ============================================================

DROP TABLE IF EXISTS public.scenario_statistics CASCADE;

CREATE TABLE public.scenario_statistics (
    scenario_id VARCHAR(100) PRIMARY KEY REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    avg_session_duration INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scenario_stats_likes ON public.scenario_statistics(likes DESC);
CREATE INDEX idx_scenario_stats_views ON public.scenario_statistics(views DESC);

-- ============================================================
-- 5. 이미지 매핑 (Image Mappings) 테이블
-- ============================================================

DROP TABLE IF EXISTS public.image_mappings CASCADE;

CREATE TABLE public.image_mappings (
    id SERIAL PRIMARY KEY,
    mapping_id VARCHAR(100) NOT NULL,
    scenario_id VARCHAR(100) REFERENCES public.scenarios(scenario_id) ON DELETE CASCADE,
    mappings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mapping_id, scenario_id)
);

CREATE INDEX idx_image_mappings_scenario ON public.image_mappings(scenario_id);
CREATE INDEX idx_image_mappings_mapping_id ON public.image_mappings(mapping_id);
CREATE INDEX idx_image_mappings_data ON public.image_mappings USING gin(mappings);

-- ============================================================
-- 6. 업데이트 트리거 생성
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_worlds_updated_at
    BEFORE UPDATE ON public.worlds
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_characters_updated_at
    BEFORE UPDATE ON public.characters
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_scenarios_updated_at
    BEFORE UPDATE ON public.scenarios
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_scenario_statistics_updated_at
    BEFORE UPDATE ON public.scenario_statistics
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_image_mappings_updated_at
    BEFORE UPDATE ON public.image_mappings
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ============================================================
-- 7. 뷰 생성 (편의성)
-- ============================================================

CREATE OR REPLACE VIEW public.v_scenario_cards AS
SELECT
    s.scenario_id,
    s.title,
    s.description,
    s.image_url,
    s.thumbnail_url,
    s.tags,
    s.card_size,
    s.route_path,
    s.display_order,
    s.is_active,
    COALESCE(st.likes, 0) as likes,
    COALESCE(st.comments, 0) as comments,
    COALESCE(st.views, 0) as views,
    COALESCE(st.total_completions, 0) as total_completions,
    COALESCE(st.avg_session_duration, 0) as avg_session_duration,
    s.created_at,
    s.updated_at
FROM public.scenarios s
LEFT JOIN public.scenario_statistics st ON s.scenario_id = st.scenario_id
ORDER BY s.display_order, s.created_at DESC;

CREATE OR REPLACE VIEW public.v_characters_basic AS
SELECT
    character_id,
    name,
    description,
    personality,
    appearance,
    metadata->>'breathing_style' as breathing_style,
    metadata->>'rank' as rank,
    metadata->>'type' as character_type,
    image_url,
    thumbnail_url,
    is_active
FROM public.characters
WHERE is_active = true;

-- ============================================================
-- 8. 권한 설정
-- ============================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kime;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kime;
GRANT USAGE ON SCHEMA public TO kime;
