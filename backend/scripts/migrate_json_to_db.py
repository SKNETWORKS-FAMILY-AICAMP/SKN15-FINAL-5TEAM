#!/usr/bin/env python3
"""
Migrate JSON game content to PostgreSQL database
- Characters
- Scenario beats
- Image mappings
- World data
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.database.db_manager import DatabaseManager

# Paths
BASE_DIR = Path(__file__).parent.parent
CHARACTERS_DIR = BASE_DIR / 'data' / 'characters'
SCENARIOS_DIR = BASE_DIR / 'data' / 'scenarios'
IMAGE_MAPPINGS_DIR = BASE_DIR / 'data' / 'image_mappings'

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def migrate_world():
    """Migrate world data"""
    print_header("Migrating World Data")

    db = DatabaseManager()

    world_data = {
        'world_id': 'demon_slayer_taisho',
        'name': '귀멸의 칼날 - 다이쇼 시대',
        'description': '일본 다이쇼 시대를 배경으로 한 귀멸의 칼날 세계관',
        'era': 'Taisho Era (1912-1926)',
        'lore': json.dumps({
            'setting': '인간과 도깨비(귀)가 공존하는 세계',
            'organization': '귀살대 - 도깨비를 퇴치하는 조직',
            'breathing_styles': ['물의 호흡', '불의 호흡', '천둥의 호흡', '바람의 호흡', '돌의 호흡'],
            'pillars': ['불기둥', '물기둥', '바람기둥', '음기둥', '뱀기둥', '사랑기둥', '안개기둥', '벌레기둥', '돌기둥']
        })
    }

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO content.worlds (world_id, name, description, era, lore)
                VALUES (%(world_id)s, %(name)s, %(description)s, %(era)s, %(lore)s::jsonb)
                ON CONFLICT (world_id) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    era = EXCLUDED.era,
                    lore = EXCLUDED.lore
            """, world_data)

    print(f"✅ World created: {world_data['world_id']}")

def migrate_character(character_file: Path, db: DatabaseManager):
    """Migrate a single character file"""

    with open(character_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    char_id = character_file.stem
    char_data = data['characters'][char_id]

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Insert character
            cur.execute("""
                INSERT INTO content.characters (
                    character_id, name, description, personality,
                    breathing_style, default_affinity,
                    appearance_hair, appearance_eyes,
                    appearance_distinctive, appearance_impression
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (character_id) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    personality = EXCLUDED.personality,
                    breathing_style = EXCLUDED.breathing_style,
                    default_affinity = EXCLUDED.default_affinity,
                    appearance_hair = EXCLUDED.appearance_hair,
                    appearance_eyes = EXCLUDED.appearance_eyes,
                    appearance_distinctive = EXCLUDED.appearance_distinctive,
                    appearance_impression = EXCLUDED.appearance_impression
            """, (
                char_id,
                char_data.get('name'),
                char_data.get('description'),
                char_data.get('personality'),
                char_data.get('breathing_style'),
                char_data.get('default_affinity', 500),
                char_data.get('appearance', {}).get('hair'),
                char_data.get('appearance', {}).get('eyes'),
                char_data.get('appearance', {}).get('distinctive'),
                char_data.get('appearance', {}).get('impression')
            ))

            # 2. Core values
            if 'core_values' in char_data:
                cur.execute("DELETE FROM content.character_core_values WHERE character_id = %s", (char_id,))
                for idx, value in enumerate(char_data['core_values']):
                    cur.execute("""
                        INSERT INTO content.character_core_values (character_id, value_text, display_order)
                        VALUES (%s, %s, %s)
                    """, (char_id, value, idx))

            # 3. Emotional triggers
            if 'emotional_triggers' in char_data:
                cur.execute("DELETE FROM content.character_emotional_triggers WHERE character_id = %s", (char_id,))
                for emotion_type, triggers in char_data['emotional_triggers'].items():
                    for idx, trigger_text in enumerate(triggers):
                        cur.execute("""
                            INSERT INTO content.character_emotional_triggers (character_id, emotion_type, trigger_text, display_order)
                            VALUES (%s, %s, %s, %s)
                        """, (char_id, emotion_type, trigger_text, idx))

            # 4. Tone settings
            if 'tone' in char_data:
                cur.execute("DELETE FROM content.character_tone WHERE character_id = %s", (char_id,))
                for level, tone_data in char_data['tone'].items():
                    cur.execute("""
                        INSERT INTO content.character_tone (
                            character_id, affinity_level,
                            level_range_min, level_range_max,
                            style, calling, suffix, samples
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    """, (
                        char_id, level,
                        tone_data['level_range'][0],
                        tone_data['level_range'][1],
                        tone_data.get('style'),
                        tone_data.get('calling'),
                        tone_data.get('suffix'),
                        json.dumps(tone_data.get('samples', []))
                    ))

            # 5. Aliases
            if 'aliases' in char_data:
                cur.execute("DELETE FROM content.character_aliases WHERE character_id = %s", (char_id,))
                for alias in char_data['aliases']:
                    cur.execute("""
                        INSERT INTO content.character_aliases (character_id, alias)
                        VALUES (%s, %s)
                        ON CONFLICT (alias) DO NOTHING
                    """, (char_id, alias))

            # 6. Quotes
            if 'signature_quotes' in char_data:
                cur.execute("DELETE FROM content.character_quotes WHERE character_id = %s", (char_id,))
                for idx, quote in enumerate(char_data['signature_quotes']):
                    cur.execute("""
                        INSERT INTO content.character_quotes (character_id, quote_text, display_order)
                        VALUES (%s, %s, %s)
                    """, (char_id, quote, idx))

            # 7. Intent rules
            if 'intent_rules' in char_data:
                cur.execute("DELETE FROM content.character_intent_rules WHERE character_id = %s", (char_id,))
                for category, rules in char_data['intent_rules'].items():
                    for rule_type, rule_value in rules.items():
                        cur.execute("""
                            INSERT INTO content.character_intent_rules (character_id, rule_category, rule_type, rule_value)
                            VALUES (%s, %s, %s, %s::jsonb)
                        """, (char_id, category, rule_type, json.dumps(rule_value)))

    print(f"✅ Character migrated: {char_data.get('name')} ({char_id})")

def migrate_characters():
    """Migrate all character files"""
    print_header("Migrating Characters")

    db = DatabaseManager()
    char_files = list(CHARACTERS_DIR.glob('*.json'))

    for char_file in char_files:
        migrate_character(char_file, db)

    print(f"\n📊 Total: {len(char_files)} characters migrated")

def migrate_scenario_beats():
    """Migrate scenario beat data"""
    print_header("Migrating Scenario Beats")

    scenario_file = SCENARIOS_DIR / 'cutscene5_llm_driven.json'

    if not scenario_file.exists():
        print("⚠️  Scenario file not found, skipping")
        return

    with open(scenario_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Map JSON scenario_id to database scenario_id
    scenario_id = 'train'  # Database uses 'train' for cutscene5_llm_driven
    db = DatabaseManager()

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Update scenario world_id
            cur.execute("""
                UPDATE content.scenarios
                SET world_id = %s
                WHERE scenario_id = %s
            """, (data.get('world_id'), scenario_id))

            # Extract beats from i18n
            if 'i18n' in data and 'ko' in data['i18n']:
                beats_data = data['i18n']['ko']

                for beat_name, goals in beats_data.items():
                    if isinstance(goals, list):
                        beat_id = f"{scenario_id}:{beat_name}"

                        # Insert beat
                        cur.execute("""
                            INSERT INTO content.scenario_beats (beat_id, scenario_id, beat_name, display_order)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (beat_id) DO UPDATE
                            SET beat_name = EXCLUDED.beat_name
                        """, (beat_id, scenario_id, beat_name, 0))

                        # Insert goals
                        cur.execute("DELETE FROM content.beat_goals WHERE beat_id = %s", (beat_id,))
                        for idx, goal in enumerate(goals):
                            cur.execute("""
                                INSERT INTO content.beat_goals (beat_id, goal_text, speaker_hints, fx, display_order)
                                VALUES (%s, %s, %s::jsonb, %s, %s)
                            """, (
                                beat_id,
                                goal.get('goal'),
                                json.dumps(goal.get('speaker_hint', [])),
                                goal.get('fx'),
                                idx
                            ))

                print(f"✅ Scenario beats migrated: {scenario_id}")
                print(f"   Beats: {len([k for k in beats_data.keys() if isinstance(beats_data[k], list)])}")

def migrate_image_mappings():
    """Migrate image mapping files"""
    print_header("Migrating Image Mappings")

    db = DatabaseManager()
    mapping_files = list(IMAGE_MAPPINGS_DIR.glob('*.json'))

    total_images = 0

    for mapping_file in mapping_files:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Infer scenario_id from filename
        filename = mapping_file.stem
        if 'train' in filename or 'mugen' in filename or 'cutscene5' in filename:
            scenario_id = 'train'  # All train/mugen/cutscene5 files map to 'train' scenario
        else:
            scenario_id = 'unknown'

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Handle array-based image mappings
                if 'images' in data and isinstance(data['images'], list):
                    for image_data in data['images']:
                        image_id = image_data.get('id')
                        # Store the full image metadata as JSONB
                        metadata = {
                            'name': image_data.get('name'),
                            'description': image_data.get('description'),
                            'tags': image_data.get('tags', []),
                            'keywords': image_data.get('keywords', []),
                            'index': image_data.get('index')
                        }
                        cur.execute("""
                            INSERT INTO content.image_mappings (scenario_id, mapping_category, image_key, image_url, metadata)
                            VALUES (%s, %s, %s, %s, %s::jsonb)
                            ON CONFLICT (scenario_id, mapping_category, image_key) DO UPDATE
                            SET image_url = EXCLUDED.image_url,
                                metadata = EXCLUDED.metadata
                        """, (scenario_id, 'scene', image_id, f'/images/{scenario_id}/{image_id}.jpg', json.dumps(metadata)))
                        total_images += 1

        print(f"✅ Image mappings from: {mapping_file.name}")

    print(f"\n📊 Total: {total_images} image mappings migrated")

def main():
    print("=" * 70)
    print("  🚀 JSON to Database Migration")
    print("=" * 70)

    try:
        # 1. World
        migrate_world()

        # 2. Characters
        migrate_characters()

        # 3. Scenario beats
        migrate_scenario_beats()

        # 4. Image mappings
        migrate_image_mappings()

        print_header("✨ Migration Complete!")
        print("\nNext steps:")
        print("  1. Verify data in database")
        print("  2. Update code to load from database")
        print("  3. Test character loading")
        print("  4. Remove or backup JSON files")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
