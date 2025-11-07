"""
그래프 기반 관계 추출기

세 가지 기법을 조합하여 엔티티 관계를 찾아냅니다.
- 동시 등장 분석(60%): 등장 빈도와 패턴으로 관계를 추정
- 규칙 기반 분석(20%): 정의된 관계 유형(동료, 숙련도 등)을 탐지
- LLM 기반 분석(20%): 문맥을 고려해 추가 관계를 식별

지원 관계 예시:
- TRAINS_WITH: 인물이 다른 인물과 함께 훈련함
- HAS_AFFINITY: 인물 간 호감도 변화가 존재함
- LOCATED_IN: 대상이 특정 위치에 존재함
- USES_SKILL: 인물이 기술을 사용함
- OCCURRED_IN: 사건이 위치에서 발생함
- BELONGS_TO: 아이템이 인물에게 속함
"""

# ============================================================
# 🔗 관계 추출기 — 대화에서 캐릭터 관계 식별
# ============================================================
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import os

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - relationship extraction will use rule-based only")


@dataclass
class EntityRelationship:
    """Represents an extracted relationship between entities"""
    source_entity_id: int
    source_entity_name: str
    target_entity_id: int
    target_entity_name: str
    relationship_type: str
    strength: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    properties: Optional[Dict[str, Any]] = None
    provenance: Optional[str] = None


class RelationshipExtractor:
    """
    엔티티 간 관계를 추출하는 클래스

    하이브리드 방식 사용:
    1. 동시 등장 분석(60%): 함께 등장하는 엔티티의 패턴 분석
    2. 규칙 기반 패턴(20%): 키워드 기반 관계 탐지
    3. LLM 기반 추출(20%): 복잡한 문맥을 반영한 관계 식별
    """

    def __init__(
        self,
        enable_llm: bool = True,
        co_occurrence_window: int = 200  # Characters
    ):
        self.enable_llm = enable_llm and OPENAI_AVAILABLE
        self.co_occurrence_window = co_occurrence_window

        # LLM 클라이언트 초기화
        self.llm_client: Optional[OpenAI] = None
        if self.enable_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)
                logger.info("LLM-based relationship extraction enabled")
            else:
                logger.warning("OpenAI API key not found - LLM extraction disabled")
                self.enable_llm = False

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

    def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        turn_number: Optional[int] = None
    ) -> List[EntityRelationship]:
        """
        Extract all relationships from text given extracted entities

        Args:
            text: Source text
            entities: List of entities with entity_id, entity_name, canonical_name, entity_type
            session_id: Optional session identifier
            turn_number: Optional turn number

        Returns:
            List of extracted EntityRelationship objects
        """
        relationships: List[EntityRelationship] = []

        cooccurrence_rels = self._extract_cooccurrence_relationships(text, entities)
        relationships.extend(cooccurrence_rels)

        rule_rels = self._extract_rule_based_relationships(text, entities)
        relationships.extend(rule_rels)

        if self.enable_llm and len(entities) >= 2:
            llm_rels = self._extract_llm_based_relationships(text, entities)
            relationships.extend(llm_rels)

        #    
        relationships = self._merge_duplicate_relationships(relationships)

        #  
        provenance = f"session:{session_id}:turn:{turn_number}" if session_id else "extraction"
        for rel in relationships:
            rel.provenance = provenance

        return relationships

    def _extract_cooccurrence_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """
        Extract relationships based on entity co-occurrence

        Entities mentioned close together likely have a relationship
        """
        relationships: List[EntityRelationship] = []

        #     
        mentions = []
        for entity in entities:
            name = entity.get("entity_name", "")
            import re
            for match in re.finditer(re.escape(name), text):
                mentions.append({
                    "entity": entity,
                    "start": match.start(),
                    "end": match.end()
                })

        #   
        mentions.sort(key=lambda x: x["start"])

        #     
        for i, mention1 in enumerate(mentions):
            for mention2 in mentions[i + 1:]:
                #    
                distance = mention2["start"] - mention1["end"]
                if distance > self.co_occurrence_window:
                    break

                entity1 = mention1["entity"]
                entity2 = mention2["entity"]

                # '     
                if entity1.get("entity_id") == entity2.get("entity_id"):
                    continue

                max_dist = self.co_occurrence_window
                strength = max(0.3, 1.0 - (distance / max_dist))

                #       
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
                    confidence=0.7  # Medium confidence for co-occurrence
                ))

        return relationships

    def _infer_relationship_type(
        self,
        type1: str,
        type2: str,
        context: str
    ) -> str:
        """Infer relationship type based on entity types and context"""
        #    
        for rel_type, keywords in self.relationship_rules.items():
            if any(keyword in context for keyword in keywords):
                return rel_type

        #       
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
        elif type_pair == ("event", "character"):
            return "PARTICIPATED_IN"
        else:
            return "RELATED_TO"

    def _extract_rule_based_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """Extract relationships using keyword-based rules"""
        relationships: List[EntityRelationship] = []

        #     
        entity_by_name = {e.get("entity_name"): e for e in entities}

        #    
        for rel_type, keywords in self.relationship_rules.items():
            for keyword in keywords:
                if keyword not in text:
                    continue

                #     
                import re
                for match in re.finditer(re.escape(keyword), text):
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(text), match.end() + 100)
                    context = text[context_start:context_end]

                    #    
                    entities_in_context = []
                    for entity_name, entity in entity_by_name.items():
                        if entity_name in context:
                            entities_in_context.append(entity)

                    #      
                    for i, entity1 in enumerate(entities_in_context):
                        for entity2 in entities_in_context[i + 1:]:
                            relationships.append(EntityRelationship(
                                source_entity_id=entity1.get("entity_id"),
                                source_entity_name=entity1.get("entity_name"),
                                target_entity_id=entity2.get("entity_id"),
                                target_entity_name=entity2.get("entity_name"),
                                relationship_type=rel_type,
                                strength=0.8,  # High strength for keyword-based
                                confidence=0.9  # High confidence for explicit keywords
                            ))

        return relationships

    def _extract_llm_based_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]]
    ) -> List[EntityRelationship]:
        """Extract relationships using LLM for complex context understanding"""
        if not self.llm_client:
            return []

        try:
            #     
            entity_list = ", ".join([
                f"{e.get('entity_name')} ({e.get('entity_type')})"
                for e in entities
            ])

            prompt = f"""Given the following Korean text and entities, identify relationships between entities.

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

            response = self.llm_client.chat.completions.create(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are an expert at identifying relationships in narrative text. Return only valid JSON."},
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

            import json
            result = json.loads(result_text)

            #    
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
                        confidence=0.75,  # Medium-high confidence for LLM
                        properties={"explanation": rel_data.get("explanation", "")}
                    ))

            logger.info(f"LLM extracted {len(relationships)} relationships")
            return relationships

        except Exception as e:
            logger.error(f"LLM relationship extraction failed: {e}")
            return []

    def _merge_duplicate_relationships(
        self,
        relationships: List[EntityRelationship]
    ) -> List[EntityRelationship]:
        """Merge duplicate relationships and average their strengths"""
        rel_groups = defaultdict(list)

        for rel in relationships:
            if rel.source_entity_id > rel.target_entity_id:
                key = (rel.target_entity_id, rel.source_entity_id, rel.relationship_type)
            else:
                key = (rel.source_entity_id, rel.target_entity_id, rel.relationship_type)

            rel_groups[key].append(rel)

        #  
        merged = []
        for key, group in rel_groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                #    
                avg_strength = sum(r.strength for r in group) / len(group)
                avg_confidence = sum(r.confidence for r in group) / len(group)

                #     
                merged_rel = group[0]
                merged_rel.strength = avg_strength
                merged_rel.confidence = avg_confidence

                merged.append(merged_rel)

        return merged


if __name__ == "__main__":
    #    
    logging.basicConfig(level=logging.INFO)

    extractor = RelationshipExtractor()

    #  
    test_entities = [
        {"entity_id": 1, "entity_name": "렌고쿠", "entity_type": "character"},
        {"entity_id": 2, "entity_name": "탄지로", "entity_type": "character"},
        {"entity_id": 3, "entity_name": "무한열차", "entity_type": "location"},
        {"entity_id": 4, "entity_name": "염의 호흡", "entity_type": "skill"},
    ]

    test_text = """
    렌고쿠가 무한열차에서 탄지로를 만나 훈련시켰다.
    그는 염의 호흡을 사용하여 귀신과 싸웠다.
    탄지로는 렌고쿠를 존경하며 함께 수련했다.
    """

    relationships = extractor.extract_relationships(test_text, test_entities)

    print(f"\n추출된 관계: {len(relationships)}개")
    for rel in relationships:
        print(f"  - {rel.source_entity_name} --[{rel.relationship_type}]--> "
              f"{rel.target_entity_name} (강도: {rel.strength:.2f}, 신뢰도: {rel.confidence:.2f})")
