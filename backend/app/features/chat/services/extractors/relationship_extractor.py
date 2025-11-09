"""
Relationship Extraction Service
엔티티 간 관계 자동 추출 (Co-occurrence + Rule-based + LLM Hybrid)

Relationship Types:
- TRAINS_WITH: 함께 훈련
- HAS_AFFINITY: 친밀도/관계
- LOCATED_IN: 위치
- USES_SKILL: 스킬 사용
- OCCURRED_IN: 이벤트 발생
- BELONGS_TO: 소유
- BATTLES_WITH: 전투
- PROTECTS: 보호
- INTERACTS_WITH: 상호작용
"""
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient

settings = get_settings()
logger = get_parent_logger("RelationshipExtractor")


@dataclass
class EntityRelationship:
    """엔티티 간 관계"""
    source_entity_id: int
    source_entity_name: str
    target_entity_id: int
    target_entity_name: str
    relationship_type: str
    strength: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    properties: Optional[Dict[str, Any]] = None
    provenance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class RelationshipExtractor:
    """
    엔티티 간 관계 추출 시스템

    Hybrid approach:
    1. Co-occurrence analysis (60%): 함께 등장하는 엔티티
    2. Rule-based patterns (20%): 키워드 기반 관계 탐지
    3. LLM-based extraction (20%): 복잡한 컨텍스트 이해
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True,
        co_occurrence_window: int = 200  # Characters
    ):
        """
        Args:
            llm_client: LLM 클라이언트
            enable_llm: LLM 기반 추출 활성화
            co_occurrence_window: Co-occurrence 윈도우 크기
        """
        self.llm_client = llm_client
        self.enable_llm = enable_llm
        self.co_occurrence_window = co_occurrence_window

        # 관계 타입 규칙 (키워드 패턴)
        self.relationship_rules = {
            "TRAINS_WITH": ["훈련", "수련", "함께", "배우다", "가르치다"],
            "HAS_AFFINITY": ["친구", "동료", "좋아", "싫어", "신뢰", "믿음"],
            "LOCATED_IN": ["에서", "안에서", "위치", "있다"],
            "USES_SKILL": ["사용", "호흡", "기술", "능력"],
            "OCCURRED_IN": ["발생", "일어나다", "벌어지다"],
            "BELONGS_TO": ["가지다", "소유", "소지"],
            "BATTLES_WITH": ["싸우다", "전투", "대결", "공격"],
            "PROTECTS": ["보호", "지키다", "방어"],
        }

        logger.info("__init__", "RelationshipExtractor initialized",
                   window=co_occurrence_window)

    async def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> List[EntityRelationship]:
        """
        텍스트와 엔티티로부터 관계 추출

        Args:
            text: 소스 텍스트
            entities: 추출된 엔티티 리스트
                      [{entity_id, entity_name, canonical_name, entity_type}, ...]
            session_id: 세션 ID
            turn_number: 턴 번호

        Returns:
            추출된 EntityRelationship 리스트
        """
        relationships: List[EntityRelationship] = []

        # 1. Co-occurrence based relationships (60%)
        cooccurrence_rels = self._extract_cooccurrence_relationships(text, entities)
        relationships.extend(cooccurrence_rels)

        # 2. Rule-based relationships (20%)
        rule_rels = self._extract_rule_based_relationships(text, entities)
        relationships.extend(rule_rels)

        # 3. LLM-based relationships (20%)
        if self.enable_llm and len(entities) >= 2:
            llm_rels = await self._extract_llm_based_relationships(text, entities)
            relationships.extend(llm_rels)

        # Deduplicate and merge
        relationships = self._merge_duplicate_relationships(relationships)

        # Add provenance
        provenance = f"session:{session_id}:turn:{turn_number}" if session_id else "extraction"
        for rel in relationships:
            rel.provenance = provenance

        logger.info("extract_relationships", f"Extracted {len(relationships)} relationships",
                   cooccurrence=len(cooccurrence_rels),
                   rule=len(rule_rels),
                   total=len(relationships))

        return relationships

    def _extract_cooccurrence_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """Co-occurrence 기반 관계 추출"""
        relationships: List[EntityRelationship] = []

        # Find entity mentions in text
        mentions = []
        for entity in entities:
            name = entity.get("entity_name", "")
            for match in re.finditer(re.escape(name), text):
                mentions.append({
                    "entity": entity,
                    "start": match.start(),
                    "end": match.end()
                })

        # Sort by position
        mentions.sort(key=lambda x: x["start"])

        # Find co-occurring entities within window
        for i, mention1 in enumerate(mentions):
            for mention2 in mentions[i + 1:]:
                # Check if within window
                distance = mention2["start"] - mention1["end"]
                if distance > self.co_occurrence_window:
                    break

                entity1 = mention1["entity"]
                entity2 = mention2["entity"]

                # Don't create relationships between same entity
                if entity1.get("entity_id") == entity2.get("entity_id"):
                    continue

                # Calculate strength based on distance
                max_dist = self.co_occurrence_window
                strength = max(0.3, 1.0 - (distance / max_dist))

                # Infer relationship type
                rel_type = self._infer_relationship_type(
                    entity1.get("entity_type"),
                    entity2.get("entity_type"),
                    text[mention1["start"]:mention2["end"]]
                )

                relationships.append(EntityRelationship(
                    source_entity_id=entity1.get("entity_id"),
                    source_entity_name=entity1.get("entity_name"),
                    target_entity_id=entity2.get("entity_id"),
                    target_entity_name=entity2.get("entity_name"),
                    relationship_type=rel_type,
                    strength=strength,
                    confidence=0.7
                ))

        return relationships

    def _infer_relationship_type(
        self,
        type1: str,
        type2: str,
        context: str
    ) -> str:
        """엔티티 타입과 컨텍스트로부터 관계 타입 추론"""
        # Check rule-based patterns first
        for rel_type, keywords in self.relationship_rules.items():
            if any(keyword in context for keyword in keywords):
                return rel_type

        # Default type based on entity type combinations
        type_pair = tuple(sorted([type1, type2]))

        if type_pair == ("character", "character"):
            return "INTERACTS_WITH"
        elif type_pair == ("character", "location"):
            return "LOCATED_IN"
        elif type_pair == ("character", "skill"):
            return "USES_SKILL"
        elif type_pair == ("character", "item"):
            return "HAS_ITEM"
        elif type_pair == ("event", "location"):
            return "OCCURRED_IN"
        elif type_pair == ("character", "event"):
            return "PARTICIPATED_IN"
        else:
            return "RELATED_TO"

    def _extract_rule_based_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """키워드 규칙 기반 관계 추출"""
        relationships: List[EntityRelationship] = []

        # Create entity lookup
        entity_by_name = {e.get("entity_name"): e for e in entities}

        # Check each relationship rule
        for rel_type, keywords in self.relationship_rules.items():
            for keyword in keywords:
                if keyword not in text:
                    continue

                # Find entities near this keyword
                for match in re.finditer(re.escape(keyword), text):
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(text), match.end() + 100)
                    context = text[context_start:context_end]

                    # Find entities in context
                    entities_in_context = []
                    for entity_name, entity in entity_by_name.items():
                        if entity_name in context:
                            entities_in_context.append(entity)

                    # Create relationships between entities in context
                    for i, entity1 in enumerate(entities_in_context):
                        for entity2 in entities_in_context[i + 1:]:
                            relationships.append(EntityRelationship(
                                source_entity_id=entity1.get("entity_id"),
                                source_entity_name=entity1.get("entity_name"),
                                target_entity_id=entity2.get("entity_id"),
                                target_entity_name=entity2.get("entity_name"),
                                relationship_type=rel_type,
                                strength=0.8,
                                confidence=0.9
                            ))

        return relationships

    async def _extract_llm_based_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """LLM 기반 복잡한 관계 추출"""
        if not self.llm_client:
            return []

        try:
            # Prepare entity list for prompt
            entity_list = ", ".join([
                f"{e.get('entity_name')} ({e.get('entity_type')})"
                for e in entities
            ])

            system_prompt = "You are an expert at identifying relationships in narrative text. Return only valid JSON."

            user_prompt = f"""Given the following Korean text and entities, identify relationships between entities.

Text: {text}

Entities: {entity_list}

For each relationship you find, return JSON in this format:
{{
  "source": "entity_name",
  "target": "entity_name",
  "type": "relationship_type",
  "strength": 0.0-1.0,
  "explanation": "why this relationship exists"
}}

Relationship types: TRAINS_WITH, HAS_AFFINITY, LOCATED_IN, USES_SKILL, OCCURRED_IN, BELONGS_TO, BATTLES_WITH, PROTECTS, INTERACTS_WITH

Return ONLY a valid JSON array of relationships. If no relationships exist, return [].
"""

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

            # Convert to EntityRelationship objects
            entity_by_name = {e.get("entity_name"): e for e in entities}
            relationships = []

            for rel_data in result:
                source_name = rel_data.get("source", "")
                target_name = rel_data.get("target", "")

                source_entity = entity_by_name.get(source_name)
                target_entity = entity_by_name.get(target_name)

                if source_entity and target_entity:
                    relationships.append(EntityRelationship(
                        source_entity_id=source_entity.get("entity_id"),
                        source_entity_name=source_name,
                        target_entity_id=target_entity.get("entity_id"),
                        target_entity_name=target_name,
                        relationship_type=rel_data.get("type", "RELATED_TO"),
                        strength=float(rel_data.get("strength", 0.7)),
                        confidence=0.75,
                        properties={"explanation": rel_data.get("explanation", "")}
                    ))

            logger.info("_extract_llm_based_relationships", f"LLM extracted {len(relationships)} relationships")
            return relationships

        except Exception as e:
            logger.error("_extract_llm_based_relationships", f"LLM extraction failed: {e}")
            return []

    def _merge_duplicate_relationships(
        self,
        relationships: List[EntityRelationship]
    ) -> List[EntityRelationship]:
        """중복 관계 병합 및 strength 평균화"""
        # Group by (source, target, type)
        rel_groups = defaultdict(list)

        for rel in relationships:
            # Normalize direction (lower ID first)
            if rel.source_entity_id > rel.target_entity_id:
                key = (rel.target_entity_id, rel.source_entity_id, rel.relationship_type)
            else:
                key = (rel.source_entity_id, rel.target_entity_id, rel.relationship_type)

            rel_groups[key].append(rel)

        # Merge duplicates
        merged = []
        for key, group in rel_groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Average strength and confidence
                avg_strength = sum(r.strength for r in group) / len(group)
                avg_confidence = sum(r.confidence for r in group) / len(group)

                # Use first relationship as template
                merged_rel = group[0]
                merged_rel.strength = avg_strength
                merged_rel.confidence = avg_confidence

                merged.append(merged_rel)

        return merged
