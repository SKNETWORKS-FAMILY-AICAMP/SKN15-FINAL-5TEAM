"""
JSON/YAML 파일에서 콘텐츠 데이터를 DB로 import하는 스크립트

Usage:
    python scripts/import_content_data.py
"""
import json
import yaml
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings

# Initialize settings
settings = Settings()


def load_yaml(file_path: Path) -> dict:
    """YAML 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(file_path: Path) -> dict:
    """JSON 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def import_world(session, world_data: dict, world_id: str):
    """World 데이터 import"""
    print(f"Importing world: {world_id}")

    # Check if world already exists
    result = session.execute(
        text("SELECT world_id FROM content.worlds WHERE world_id = :world_id"),
        {"world_id": world_id}
    )
    exists = result.fetchone()

    if exists:
        print(f"  -> World {world_id} already exists, skipping")
        return

    # Insert world
    session.execute(
        text("""
            INSERT INTO content.worlds (world_id, name, description, era, lore, created_at)
            VALUES (:world_id, :name, :description, :era, :lore, NOW())
        """),
        {
            "world_id": world_id,
            "name": world_data.get("title", ""),
            "description": world_data.get("description", ""),
            "era": world_data.get("metadata", {}).get("era", ""),
            "lore": json.dumps({
                "world_context": world_data.get("world_context", ""),
                "rules": world_data.get("rules", {}),
                "tone_guidelines": world_data.get("tone_guidelines", {}),
                "terminology": world_data.get("terminology", {}),
                "metadata": world_data.get("metadata", {})
            }, ensure_ascii=False)
        }
    )
    session.commit()
    print(f"  -> World {world_id} imported successfully")


def import_character(session, character_data: dict, character_id: str):
    """Character 데이터 import"""
    char = character_data["characters"][character_id]
    print(f"Importing character: {character_id} ({char['name']})")

    # Check if character already exists
    result = session.execute(
        text("SELECT character_id FROM content.characters WHERE character_id = :character_id"),
        {"character_id": character_id}
    )
    exists = result.fetchone()

    if exists:
        print(f"  -> Character {character_id} already exists, skipping")
        return

    # Insert character
    appearance = char.get("appearance", {})
    session.execute(
        text("""
            INSERT INTO content.characters (
                character_id, name, description, personality, breathing_style,
                default_affinity, appearance_hair, appearance_eyes,
                appearance_distinctive, appearance_impression,
                created_at, updated_at
            )
            VALUES (
                :character_id, :name, :description, :personality, :breathing_style,
                :default_affinity, :appearance_hair, :appearance_eyes,
                :appearance_distinctive, :appearance_impression,
                NOW(), NOW()
            )
        """),
        {
            "character_id": character_id,
            "name": char.get("name", ""),
            "description": char.get("description", ""),
            "personality": char.get("personality", ""),
            "breathing_style": char.get("breathing_style", ""),
            "default_affinity": char.get("default_affinity", 500),
            "appearance_hair": appearance.get("hair", ""),
            "appearance_eyes": appearance.get("eyes", ""),
            "appearance_distinctive": appearance.get("distinctive", ""),
            "appearance_impression": appearance.get("impression", "")
        }
    )

    # Insert aliases
    for alias in char.get("aliases", []):
        session.execute(
            text("""
                INSERT INTO content.character_aliases (character_id, alias)
                VALUES (:character_id, :alias)
            """),
            {"character_id": character_id, "alias": alias}
        )

    # Insert core values
    for value in char.get("core_values", []):
        session.execute(
            text("""
                INSERT INTO content.character_core_values (character_id, value_text)
                VALUES (:character_id, :value_text)
            """),
            {"character_id": character_id, "value_text": value}
        )

    # Insert signature quotes
    for quote in char.get("signature_quotes", []):
        session.execute(
            text("""
                INSERT INTO content.character_quotes (character_id, quote_text)
                VALUES (:character_id, :quote_text)
            """),
            {"character_id": character_id, "quote_text": quote}
        )

    # Insert intent rules (using new schema: rule_category, rule_type, rule_value as JSONB)
    intent_rules = char.get("intent_rules", {})

    # Weights as 'weights' category
    for intent_name, weight in intent_rules.get("weights", {}).items():
        session.execute(
            text("""
                INSERT INTO content.character_intent_rules
                (character_id, rule_category, rule_type, rule_value)
                VALUES (:character_id, 'weights', :intent_name, :rule_value)
            """),
            {
                "character_id": character_id,
                "intent_name": intent_name,
                "rule_value": json.dumps({"weight": weight}, ensure_ascii=False)
            }
        )

    # Sensitivities as 'sensitivities' category
    for sensitivity_name, value in intent_rules.get("sensitivities", {}).items():
        session.execute(
            text("""
                INSERT INTO content.character_intent_rules
                (character_id, rule_category, rule_type, rule_value)
                VALUES (:character_id, 'sensitivities', :sensitivity_name, :rule_value)
            """),
            {
                "character_id": character_id,
                "sensitivity_name": sensitivity_name,
                "rule_value": json.dumps({"value": value}, ensure_ascii=False)
            }
        )

    # Patterns as 'patterns' category
    for pattern_name, keywords in intent_rules.get("patterns", {}).items():
        session.execute(
            text("""
                INSERT INTO content.character_intent_rules
                (character_id, rule_category, rule_type, rule_value)
                VALUES (:character_id, 'patterns', :pattern_name, :rule_value)
            """),
            {
                "character_id": character_id,
                "pattern_name": pattern_name,
                "rule_value": json.dumps({"keywords": keywords}, ensure_ascii=False)
            }
        )

    # Insert tone (low, mid, high) - use affinity_level, level_range_min/max
    for tone_level, tone_data in char.get("tone", {}).items():
        level_min, level_max = tone_data.get("level_range", [0, 0])
        session.execute(
            text("""
                INSERT INTO content.character_tone
                (character_id, affinity_level, level_range_min, level_range_max, style, calling, suffix, samples)
                VALUES (:character_id, :affinity_level, :level_range_min, :level_range_max, :style, :calling, :suffix, :samples)
            """),
            {
                "character_id": character_id,
                "affinity_level": tone_level,
                "level_range_min": level_min,
                "level_range_max": level_max,
                "style": tone_data.get("style", ""),
                "calling": tone_data.get("calling", ""),
                "suffix": tone_data.get("suffix", ""),
                "samples": json.dumps(tone_data.get("samples", []), ensure_ascii=False)
            }
        )

    # Insert emotional triggers - use emotion_type instead of trigger_type
    for emotion_type, triggers in char.get("emotional_triggers", {}).items():
        for trigger in triggers:
            session.execute(
                text("""
                    INSERT INTO content.character_emotional_triggers
                    (character_id, emotion_type, trigger_text)
                    VALUES (:character_id, :emotion_type, :trigger_text)
                """),
                {
                    "character_id": character_id,
                    "emotion_type": emotion_type,
                    "trigger_text": trigger
                }
            )

    # Insert scenario-specific relationships
    for scenario_id, scenario_data in char.get("scenario_specific", {}).items():
        for target_char, rel_data in scenario_data.get("relationships", {}).items():
            # Skip if target_char is 'user'
            if target_char == "user":
                continue

            session.execute(
                text("""
                    INSERT INTO content.character_relationships
                    (scenario_id, character_id, target_character_id, relationship_type, description)
                    VALUES (:scenario_id, :character_id, :target_character_id, :relationship_type, :description)
                """),
                {
                    "scenario_id": scenario_id,
                    "character_id": character_id,
                    "target_character_id": target_char,
                    "relationship_type": rel_data.get("type", ""),
                    "description": rel_data.get("description", "")
                }
            )

    session.commit()
    print(f"  -> Character {character_id} imported successfully")


def import_image_mappings(session, mapping_data: dict, scenario_id: str, mapping_type: str):
    """Image mapping 데이터 import"""
    print(f"Importing image mappings for scenario: {scenario_id} (type: {mapping_type})")

    # Check if scenario exists
    result = session.execute(
        text("SELECT scenario_id FROM content.scenarios WHERE scenario_id = :scenario_id"),
        {"scenario_id": scenario_id}
    )
    if not result.fetchone():
        print(f"  -> Scenario {scenario_id} not found, skipping image mappings")
        return

    mappings = mapping_data.get("mappings", [])

    for mapping in mappings:
        # Prepare stage data
        stage = mapping.get("stage")
        if isinstance(stage, list):
            stage_list = json.dumps(stage, ensure_ascii=False)
            stage = None
        else:
            stage_list = None

        # Insert mapping
        session.execute(
            text("""
                INSERT INTO content.scenario_image_mappings
                (scenario_id, mapping_type, priority, stage, stage_list,
                 turn_min, turn_max, dialogue_count_min, dialogue_count_max,
                 flags, image, description)
                VALUES
                (:scenario_id, :mapping_type, :priority, :stage, :stage_list,
                 :turn_min, :turn_max, :dialogue_count_min, :dialogue_count_max,
                 :flags, :image, :description)
            """),
            {
                "scenario_id": scenario_id,
                "mapping_type": mapping_type,
                "priority": mapping.get("priority", 50),
                "stage": stage,
                "stage_list": stage_list,
                "turn_min": mapping.get("turn", [None, None])[0] if "turn" in mapping else None,
                "turn_max": mapping.get("turn", [None, None])[1] if "turn" in mapping else None,
                "dialogue_count_min": mapping.get("dialogue_count", [None, None])[0] if "dialogue_count" in mapping else None,
                "dialogue_count_max": mapping.get("dialogue_count", [None, None])[1] if "dialogue_count" in mapping else None,
                "flags": json.dumps(mapping.get("flags", []), ensure_ascii=False),
                "image": mapping.get("image", ""),
                "description": mapping.get("description", "")
            }
        )

    session.commit()
    print(f"  -> {len(mappings)} image mappings imported")


def import_image_metadata(session, metadata: dict, scenario_id: str):
    """Image metadata 데이터 import"""
    print(f"Importing image metadata for scenario: {scenario_id}")

    # Check if scenario exists
    result = session.execute(
        text("SELECT scenario_id FROM content.scenarios WHERE scenario_id = :scenario_id"),
        {"scenario_id": scenario_id}
    )
    if not result.fetchone():
        print(f"  -> Scenario {scenario_id} not found, skipping image metadata")
        return

    images = metadata.get("images", [])

    for image in images:
        session.execute(
            text("""
                INSERT INTO content.scenario_image_metadata
                (scenario_id, image_index, image_id, name, description, tags, keywords)
                VALUES
                (:scenario_id, :image_index, :image_id, :name, :description, :tags, :keywords)
            """),
            {
                "scenario_id": scenario_id,
                "image_index": image.get("index", ""),
                "image_id": image.get("id", ""),
                "name": image.get("name", ""),
                "description": image.get("description", ""),
                "tags": json.dumps(image.get("tags", []), ensure_ascii=False),
                "keywords": json.dumps(image.get("keywords", []), ensure_ascii=False)
            }
        )

    session.commit()
    print(f"  -> {len(images)} image metadata entries imported")


def main():
    """Main import function"""
    # Create database connection (replace asyncpg with psycopg2 for sync usage)
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get data directory (check if running in Docker or local)
        data_dir = Path("/app/data") if Path("/app/data").exists() else Path(__file__).parent.parent.parent / "data"

        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        print(f"Using data directory: {data_dir}")

        # Import worlds
        print("\n=== Importing Worlds ===")
        worlds_dir = data_dir / "worlds"
        if worlds_dir.exists():
            for world_file in worlds_dir.glob("*.yaml"):
                world_data = load_yaml(world_file)
                world_id = world_data.get("world_id", world_file.stem)
                import_world(session, world_data, world_id)
        else:
            print(f"  -> Worlds directory not found: {worlds_dir}")

        # Import characters
        print("\n=== Importing Characters ===")
        characters_dir = data_dir / "characters"
        if characters_dir.exists():
            for char_file in characters_dir.glob("*.json"):
                char_data = load_json(char_file)
                for character_id in char_data.get("characters", {}).keys():
                    import_character(session, char_data, character_id)
        else:
            print(f"  -> Characters directory not found: {characters_dir}")

        # Import image mappings
        print("\n=== Importing Image Mappings ===")
        image_mappings_dir = data_dir / "image_mappings"

        if image_mappings_dir.exists():
            # train_cutscenes.json - try both mugen-train and mugen_train
            train_cutscenes = image_mappings_dir / "train_cutscenes.json"
            if train_cutscenes.exists():
                mapping_data = load_json(train_cutscenes)
                import_image_mappings(session, mapping_data, "mugen-train", "cutscene")

            # cutscene5_llm_driven_cutscenes.json
            llm_cutscenes = image_mappings_dir / "cutscene5_llm_driven_cutscenes.json"
            if llm_cutscenes.exists():
                mapping_data = load_json(llm_cutscenes)
                import_image_mappings(session, mapping_data, "mugen-train", "llm_driven")

            # mugen_train_images.json (metadata)
            mugen_train_meta = image_mappings_dir / "mugen_train_images.json"
            if mugen_train_meta.exists():
                metadata = load_json(mugen_train_meta)
                import_image_metadata(session, metadata, "mugen-train")
        else:
            print(f"  -> Image mappings directory not found: {image_mappings_dir}")

        print("\n=== Import Complete ===")

    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
