"""
그래프 RAG용 엔티티 추출 파이프라인

텍스트에서 인물, 장소, 사건, 아이템, 기술 등의 엔티티를 추출하기 위해
다음과 같은 하이브리드 방식을 사용한다.
- 규칙 기반 추출(60%): 이미 알려진 엔티티 패턴을 빠르게 탐지
- LLM 기반 추출(40%): 문맥을 고려해 새로운 엔티티를 식별

지원하는 엔티티 유형
- character: 스토리의 등장인물
- location: 장소·건물·지역
- event: 중요한 사건이나 전투
- item: 무기·도구와 같은 물품
- skill: 호흡법 등 능력·기술
"""

# ============================================================
# 🧾 엔티티 추출기 — 문장에서 핵심 개체 탐지
# ============================================================
import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - entity extraction will use rule-based only")


@dataclass
class Entity:
    """Represents an extracted entity"""
    entity_type: str  # 'character', 'location', 'event', 'item', 'skill' 유형
    entity_name: str
    canonical_name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: float = 0.8  # 추출 신뢰도 (0.0-1.0)
    extraction_method: str = "rule"  # 'rule' 또는 'llm'
    context: Optional[str] = None  # 주변 문맥 텍스트


class EntityExtractor:
    """
    하이브리드 엔티티 추출기

    규칙 기반 추출(60%):
    - 캐릭터 정의에서 이름 패턴을 사용
    - 시나리오 데이터의 위치 키워드를 참조
    - 호흡법 등 기술 패턴을 인식

    LLM 기반 추출(40%):
    - 새롭게 등장한 인물 탐지
    - 암시적인 위치 정보를 추론
    - 문맥 의존 사건을 감지
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

        # 기초 데이터 초기화
        self.known_characters: Dict[str, Dict[str, Any]] = {}
        self.known_locations: Set[str] = set()
        self.known_skills: Set[str] = set()
        self.known_items: Set[str] = set()

        self._load_reference_data()

        # LLM 클라이언트 초기화
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

                            #  
                            if "breathing_style" in char_info:
                                self.known_skills.add(char_info["breathing_style"])

                            if "weapon" in char_info:
                                self.known_items.add(char_info["weapon"])

            except Exception as e:
                logger.error(f"Failed to load character data from {filepath}: {e}")

        #    
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

        rule_entities = self._extract_rule_based(text)
        entities.extend(rule_entities)

        if self.enable_llm:
            llm_entities = self._extract_llm_based(text, context)
            #    
            llm_entities = self._deduplicate_entities(llm_entities, rule_entities)
            entities.extend(llm_entities)

        # :  
        entities = self._assign_canonical_names(entities)

        return entities

    def _extract_rule_based(self, text: str) -> List[Entity]:
        """Rule-based entity extraction using pattern matching"""
        entities: List[Entity] = []

        #   
        for char_name, char_data in self.known_characters.items():
            if char_name in text:
                #     
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

        #   
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

        #   
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

        #   
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

        #   
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

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)

            entities: List[Entity] = []

            #    
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
                # :     
                entity.canonical_name = entity.entity_name

        return entities


if __name__ == "__main__":
    #    
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
