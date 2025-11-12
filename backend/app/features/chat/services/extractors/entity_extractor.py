"""
Entity Extraction Service
엔티티 자동 추출 (Rule-based + LLM Hybrid)

Extract entities from text:
- Character: 캐릭터 이름
- Location: 장소, 지역
- Event: 사건, 이벤트
- Item: 아이템, 무기
- Skill: 스킬, 기술
"""
import re
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union
from dataclasses import dataclass, asdict

from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient

settings = get_settings()
logger = get_parent_logger("EntityExtractor")


@dataclass
class Entity:
    """추출된 엔티티"""
    entity_type: str  # 'character', 'location', 'event', 'item', 'skill'
    entity_name: str
    canonical_name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 0.8  # 추출 신뢰도 (0.0-1.0)
    extraction_method: str = "rule"  # 'rule' or 'llm'
    context: Optional[str] = None  # 주변 텍스트

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class EntityExtractor:
    """
    Hybrid Entity Extraction System

    Rule-based (60%): 알려진 엔티티 패턴 매칭
    LLM-based (40%): 새로운 엔티티 추출
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True,
        data_dir: Optional[Union[str, Path]] = None
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            enable_llm: LLM 기반 추출 활성화
        """
        self.llm_client = llm_client
        self.enable_llm = enable_llm

        if data_dir is None:
            data_dir = settings.DATA_DIR
        if isinstance(data_dir, str):
            data_dir = Path(data_dir)
        self.data_dir: Path = data_dir
        self.character_dir = self.data_dir / "characters"
        self.scenario_dir = self.data_dir / "scenarios"

        # Knowledge bases
        self.known_characters: Dict[str, Dict[str, Any]] = {}
        self.known_locations: Set[str] = set()
        self.known_skills: Set[str] = set()
        self.known_items: Set[str] = set()

        # Load reference data
        self._load_reference_data()

        logger.info("__init__", "EntityExtractor initialized",
                   characters=len(self.known_characters),
                   locations=len(self.known_locations),
                   skills=len(self.known_skills),
                   items=len(self.known_items))

    def _load_reference_data(self) -> None:
        """시나리오/캐릭터 데이터에서 알려진 엔티티 로드"""
        try:
            # Load characters
            if self.character_dir.exists():
                character_files = glob.glob(str(self.character_dir / "*.json"))
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

                                    # Extract items
                                    if "weapon" in char_info:
                                        self.known_items.add(char_info["weapon"])

                    except Exception as e:
                        logger.error("_load_reference_data", f"Failed to load {filepath}: {e}")

            # Load scenarios for locations
            if self.scenario_dir.exists():
                scenario_files = glob.glob(str(self.scenario_dir / "*.json"))
                for filepath in scenario_files:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "location" in data:
                                self.known_locations.add(data["location"])
                    except Exception as e:
                        logger.error("_load_reference_data", f"Failed to load {filepath}: {e}")

        except Exception as e:
            logger.error("_load_reference_data", f"Failed to load reference data: {e}")

    async def extract_entities(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """
        텍스트에서 모든 엔티티 추출 (Hybrid)

        Args:
            text: 입력 텍스트
            context: 추가 컨텍스트 (session_id, turn_number 등)

        Returns:
            추출된 Entity 리스트
        """
        entities: List[Entity] = []

        # 1. Rule-based extraction (fast, high precision)
        rule_entities = self._extract_rule_based(text)
        entities.extend(rule_entities)

        # 2. LLM-based extraction (slower, better recall)
        if self.enable_llm:
            llm_entities = await self._extract_llm_based(text, context)
            # Deduplicate
            llm_entities = self._deduplicate_entities(llm_entities, rule_entities)
            entities.extend(llm_entities)

        # 3. Post-processing: assign canonical names
        entities = self._assign_canonical_names(entities)

        logger.info("extract_entities", f"Extracted {len(entities)} entities",
                   rule=len(rule_entities),
                   llm=len(entities) - len(rule_entities))

        return entities

    def _extract_rule_based(self, text: str) -> List[Entity]:
        """Rule-based 엔티티 추출"""
        entities: List[Entity] = []

        # Extract known characters
        for char_name, char_data in self.known_characters.items():
            if char_name in text:
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
                        confidence=0.95,
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
                    confidence=0.7,
                    extraction_method="rule",
                    context=context
                ))

        return entities

    async def _extract_llm_based(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Entity]:
        """LLM 기반 새로운 엔티티 추출"""
        if not self.llm_client:
            return []

        try:
            system_prompt = "You are an expert entity extractor. Return only valid JSON."

            user_prompt = f"""Extract entities from the following Korean text. Identify:
- Characters (characters): Named people or beings
- Locations (locations): Places, buildings, areas
- Events (events): Significant occurrences, battles, encounters
- Items (items): Objects, weapons, tools
- Skills (skills): Abilities, techniques

Text: {text}

Return ONLY a valid JSON object with this structure:
{{
  "characters": [{{"name": "...", "description": "..."}}],
  "locations": [{{"name": "...", "description": "..."}}],
  "events": [{{"name": "...", "description": "..."}}],
  "items": [{{"name": "...", "description": "..."}}],
  "skills": [{{"name": "...", "description": "..."}}"]]
}}

If a category has no entities, use an empty array [].
Do not include any text outside the JSON object."""

            result_text = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1000,
                use_cache=False
            )

            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            entities: List[Entity] = []

            # Process each entity type
            for entity_type in ["characters", "locations", "events", "items", "skills"]:
                entity_list = result.get(entity_type, [])
                type_singular = entity_type.rstrip('s')

                for entity_data in entity_list:
                    if isinstance(entity_data, dict):
                        name = entity_data.get("name", "")
                        description = entity_data.get("description", "")

                        if name:
                            entities.append(Entity(
                                entity_type=type_singular if type_singular != "event" else "event",
                                entity_name=name,
                                description=description,
                                confidence=0.75,
                                extraction_method="llm",
                                context=text[:200]
                            ))

            logger.info("_extract_llm_based", f"LLM extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error("_extract_llm_based", f"LLM extraction failed: {e}")
            return []

    def _deduplicate_entities(
        self,
        new_entities: List[Entity],
        existing_entities: List[Entity]
    ) -> List[Entity]:
        """LLM과 Rule-based 중복 제거"""
        existing_names = {(e.entity_type, e.entity_name.lower()) for e in existing_entities}

        deduplicated = []
        for entity in new_entities:
            key = (entity.entity_type, entity.entity_name.lower())
            if key not in existing_names:
                deduplicated.append(entity)

        return deduplicated

    def _assign_canonical_names(self, entities: List[Entity]) -> List[Entity]:
        """알려진 엔티티에 대해 표준 이름 할당"""
        for entity in entities:
            if entity.entity_type == "character" and entity.entity_name in self.known_characters:
                entity.canonical_name = entity.entity_name
            elif entity.canonical_name is None:
                entity.canonical_name = entity.entity_name

        return entities
