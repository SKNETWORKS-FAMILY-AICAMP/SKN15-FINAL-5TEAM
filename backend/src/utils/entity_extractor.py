#!/usr/bin/env python3
"""
Entity Extraction Pipeline for Graph RAG

Extracts entities (characters, locations, events, items, skills) from text
using a hybrid approach:
- Rule-based extraction (60%): Fast pattern matching for known entities
- LLM-based extraction (40%): Context-aware extraction for novel entities

Entity types:
- character: Named characters in the story
- location: Places, buildings, areas
- event: Significant occurrences, battles, encounters
- item: Objects, weapons, tools
- skill: Abilities, techniques, breathing styles
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

# Optional OpenAI import
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - entity extraction will use rule-based only")


@dataclass
class Entity:
    """Represents an extracted entity"""
    entity_type: str  # 'character', 'location', 'event', 'item', 'skill'
    entity_name: str
    canonical_name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 0.8  # Extraction confidence (0.0-1.0)
    extraction_method: str = "rule"  # 'rule' or 'llm'
    context: Optional[str] = None  # Surrounding text


class EntityExtractor:
    """
    Hybrid entity extraction system

    Rule-based (60%):
    - Character name patterns from character definitions
    - Location keywords from scenario data
    - Skill patterns (e.g., "염의 호흡", "물의 호흡")

    LLM-based (40%):
    - Novel character mentions
    - Implicit location references
    - Context-dependent event detection
    """

    def __init__(
        self,
        character_data_path: str = "/Users/jtm427/Desktop/workspace/backend/data/characters",
        scenario_data_path: str = "/Users/jtm427/Desktop/workspace/backend/data/scenarios",
        enable_llm: bool = True
    ):
        self.character_data_path = character_data_path
        self.scenario_data_path = scenario_data_path
        self.enable_llm = enable_llm and OPENAI_AVAILABLE

        # Initialize knowledge bases
        self.known_characters: Dict[str, Dict[str, Any]] = {}
        self.known_locations: Set[str] = set()
        self.known_skills: Set[str] = set()
        self.known_items: Set[str] = set()

        # Load reference data
        self._load_reference_data()

        # Initialize LLM client if available
        self.llm_client: Optional[OpenAI] = None
        if self.enable_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)
                logger.info("LLM-based entity extraction enabled")
            else:
                logger.warning("OpenAI API key not found - LLM extraction disabled")
                self.enable_llm = False

    def _load_reference_data(self) -> None:
        """Load known entities from character and scenario files"""
        import glob

        # Load characters
        character_files = glob.glob(f"{self.character_data_path}/*.json")
        for filepath in character_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "characters" in data:
                        for char_id, char_info in data["characters"].items():
                            name = char_info.get("name", char_id)
                            self.known_characters[name] = {
                                "id": char_id,
                                "name": name,
                                "description": char_info.get("personality", ""),
                                "properties": char_info
                            }

                            # Extract skills
                            if "breathing_style" in char_info:
                                self.known_skills.add(char_info["breathing_style"])

                            # Extract items (weapons, etc.)
                            if "weapon" in char_info:
                                self.known_items.add(char_info["weapon"])

            except Exception as e:
                logger.error(f"Failed to load character data from {filepath}: {e}")

        # Load scenarios for locations
        scenario_files = glob.glob(f"{self.scenario_data_path}/*.json")
        for filepath in scenario_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "location" in data:
                        self.known_locations.add(data["location"])
            except Exception as e:
                logger.error(f"Failed to load scenario data from {filepath}: {e}")

        logger.info(f"Loaded {len(self.known_characters)} characters, "
                   f"{len(self.known_locations)} locations, "
                   f"{len(self.known_skills)} skills, "
                   f"{len(self.known_items)} items")

    def extract_entities(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """
        Extract all entities from text using hybrid approach

        Args:
            text: Input text to extract entities from
            context: Optional context (session_id, turn_number, etc.)

        Returns:
            List of extracted Entity objects
        """
        entities: List[Entity] = []

        # Rule-based extraction (fast, high precision)
        rule_entities = self._extract_rule_based(text)
        entities.extend(rule_entities)

        # LLM-based extraction (slower, better recall)
        if self.enable_llm:
            llm_entities = self._extract_llm_based(text, context)
            # Deduplicate with rule-based results
            llm_entities = self._deduplicate_entities(llm_entities, rule_entities)
            entities.extend(llm_entities)

        # Post-processing: canonical names
        entities = self._assign_canonical_names(entities)

        return entities

    def _extract_rule_based(self, text: str) -> List[Entity]:
        """Rule-based entity extraction using pattern matching"""
        entities: List[Entity] = []

        # Extract known characters
        for char_name, char_data in self.known_characters.items():
            if char_name in text:
                # Find all occurrences with context
                pattern = re.escape(char_name)
                for match in re.finditer(pattern, text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]

                    entities.append(Entity(
                        entity_type="character",
                        entity_name=char_name,
                        canonical_name=char_name,
                        description=char_data.get("description", ""),
                        properties=char_data.get("properties", {}),
                        confidence=0.95,  # High confidence for exact matches
                        extraction_method="rule",
                        context=context
                    ))

        # Extract known locations
        for location in self.known_locations:
            if location in text:
                pattern = re.escape(location)
                for match in re.finditer(pattern, text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]

                    entities.append(Entity(
                        entity_type="location",
                        entity_name=location,
                        canonical_name=location,
                        confidence=0.95,
                        extraction_method="rule",
                        context=context
                    ))

        # Extract known skills
        for skill in self.known_skills:
            if skill in text:
                pattern = re.escape(skill)
                for match in re.finditer(pattern, text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]

                    entities.append(Entity(
                        entity_type="skill",
                        entity_name=skill,
                        canonical_name=skill,
                        confidence=0.95,
                        extraction_method="rule",
                        context=context
                    ))

        # Extract known items
        for item in self.known_items:
            if item in text:
                pattern = re.escape(item)
                for match in re.finditer(pattern, text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]

                    entities.append(Entity(
                        entity_type="item",
                        entity_name=item,
                        canonical_name=item,
                        confidence=0.95,
                        extraction_method="rule",
                        context=context
                    ))

        # Pattern-based event detection
        event_patterns = [
            r"전투|싸움|대결|공격",  # Battle
            r"만남|조우|발견",  # Encounter
            r"훈련|수련",  # Training
            r"치유|회복",  # Healing
            r"이동|출발|도착",  # Movement
        ]

        for pattern in event_patterns:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                entities.append(Entity(
                    entity_type="event",
                    entity_name=match.group(),
                    confidence=0.7,  # Lower confidence for pattern matches
                    extraction_method="rule",
                    context=context
                ))

        return entities

    def _extract_llm_based(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """LLM-based entity extraction for novel entities"""
        if not self.llm_client:
            return []

        try:
            prompt = f"""Extract entities from the following Korean text. Identify:
- Characters (characters): Named people or beings
- Locations (locations): Places, buildings, areas
- Events (events): Significant occurrences, battles, encounters
- Items (items): Objects, weapons, tools
- Skills (skills): Abilities, techniques

Text: {text}

Return ONLY a valid JSON object with this exact structure:
{{
  "characters": ["{{"name": "...", "description": "..."}}"],
  "locations": ["{{"name": "...", "description": "..."}}"],
  "events": ["{{"name": "...", "description": "..."}}"],
  "items": ["{{"name": "...", "description": "..."}}"],
  "skills": ["{{"name": "...", "description": "..."}}"]]
}}

Important:
- Each category should be an array of objects
- Each object must have "name" and "description" fields
- If a category has no entities, use an empty array []
- Do not include any text outside the JSON object"""

            response = self.llm_client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are an expert entity extractor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            entities: List[Entity] = []

            # Process each entity type
            for entity_type in ["characters", "locations", "events", "items", "skills"]:
                entity_list = result.get(entity_type, [])
                type_singular = entity_type.rstrip('s')  # Remove trailing 's'

                for entity_data in entity_list:
                    if isinstance(entity_data, dict):
                        name = entity_data.get("name", "")
                        description = entity_data.get("description", "")

                        if name:
                            entities.append(Entity(
                                entity_type=type_singular if type_singular != "event" else "event",
                                entity_name=name,
                                description=description,
                                confidence=0.75,  # Medium confidence for LLM extraction
                                extraction_method="llm",
                                context=text[:200]  # First 200 chars as context
                            ))

            logger.info(f"LLM extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []

    def _deduplicate_entities(
        self,
        new_entities: List[Entity],
        existing_entities: List[Entity]
    ) -> List[Entity]:
        """Remove duplicates between LLM and rule-based extractions"""
        existing_names = {(e.entity_type, e.entity_name.lower()) for e in existing_entities}

        deduplicated = []
        for entity in new_entities:
            key = (entity.entity_type, entity.entity_name.lower())
            if key not in existing_names:
                deduplicated.append(entity)

        return deduplicated

    def _assign_canonical_names(self, entities: List[Entity]) -> List[Entity]:
        """Assign canonical names for known entities"""
        for entity in entities:
            if entity.entity_type == "character" and entity.entity_name in self.known_characters:
                entity.canonical_name = entity.entity_name
            elif entity.canonical_name is None:
                # Default: use entity name as canonical
                entity.canonical_name = entity.entity_name

        return entities


if __name__ == "__main__":
    # Test the entity extractor
    logging.basicConfig(level=logging.INFO)

    extractor = EntityExtractor()

    test_text = """
    렌고쿠가 무한열차에서 탄지로와 젠이츠를 만났다.
    그는 염의 호흡을 사용하여 귀신들과 싸웠다.
    탄지로는 물의 호흡을 배우고 있었다.
    """

    entities = extractor.extract_entities(test_text)

    print(f"\n추출된 엔티티: {len(entities)}개")
    for entity in entities:
        print(f"  - [{entity.entity_type}] {entity.entity_name} "
              f"(신뢰도: {entity.confidence:.2f}, 방법: {entity.extraction_method})")
