-- ============================================================
-- Migration 014: Seed Initial Scenario Data
-- ============================================================
-- Purpose: Insert initial scenario data from scenarios.json
-- Author: AI Assistant
-- Date: 2025-11-05
-- Dependencies: 013_scenarios_system.sql
-- ============================================================

-- Insert scenarios
INSERT INTO statedb.scenarios (scenario_id, title, description, image_url, tags, card_size, route_path, display_order, is_active) VALUES
('train', '무한열차', '무한열차에서 펼쳐지는 치열한 전투와 동료애', '/images/무한열차.jpeg', ARRAY['#무한열차', '#꿈속전투', '#엔무'], 'large', '/chat/train', 1, true),
('ending', '엔딩 이후', '최종 결전 후 동료들과 함께하는 평범하지만 소중한 일상', '/images/엔딩이후.png', ARRAY['#엔딩이후', '#일상', '#평화', '#동료애'], 'normal', '/chat/ending', 2, true),
('infinity-castle', '무한성', '무한성에서 펼쳐지는 최종 결전', '/images/무한성.webp', ARRAY['#최종결전', '#귀살대', '#무잔전'], 'large', '/chat/infinity-castle', 3, true),
('tanjiro', '편의점 탄지로', '편의점에서 일하는 탄지로와의 일상 대화', '/images/편의점탄지로.png', ARRAY['#편의점', '#일상', '#탄지로'], 'normal', '/chat/tanjiro', 4, true),
('counseling', '귀칼 상담소 AU', '귀살대원들이 운영하는 고민상담소', '/images/귀칼상담소.png', ARRAY['#상담소', '#힐링AU', '#감정공감'], 'normal', '/chat/counseling', 5, true),
('idol', '아이돌/밴드 AU', '아이돌 또는 밴드로 활동하는 캐릭터들', '/images/아이돌밴드.png', ARRAY['#아이돌AU', '#밴드AU', '#팬심폭발'], 'large', '/chat/idol', 6, true),
('cutscene5_llm_driven', '🔥 무한열차', '갈림길→전략 개입→동료 규합→보스 퇴장 시네마틱→판정→히든/기본 엔딩', '/images/무한열차.jpeg', ARRAY['#무한열차', '#꿈속전투', '#엔무'], 'normal', '/chat/cutscene5_llm_driven', 7, true)
ON CONFLICT (scenario_id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    image_url = EXCLUDED.image_url,
    tags = EXCLUDED.tags,
    card_size = EXCLUDED.card_size,
    route_path = EXCLUDED.route_path,
    display_order = EXCLUDED.display_order,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Insert scenario statistics
INSERT INTO statedb.scenario_statistics (scenario_id, total_likes, total_comments, total_views) VALUES
('train', 98, 32, 890),
('ending', 87, 28, 720),
('infinity-castle', 156, 67, 1850),
('tanjiro', 121, 45, 1200),
('counseling', 134, 52, 1150),
('idol', 203, 89, 2100),
('cutscene5_llm_driven', 98, 32, 890)
ON CONFLICT (scenario_id) DO UPDATE SET
    total_likes = EXCLUDED.total_likes,
    total_comments = EXCLUDED.total_comments,
    total_views = EXCLUDED.total_views,
    last_updated = NOW();

-- ============================================================
-- Migration Complete
-- ============================================================
