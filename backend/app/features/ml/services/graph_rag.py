"""
GraphRAG Service

지식 그래프 기반 의사결정 예측 및 검색 서비스
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..repository import DecisionLogRepository, GraphNodeRepository, GraphEdgeRepository
from .keyword_extractor import KeywordExtractor
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("GraphRAG")


class GraphRAG:
    """
    GraphRAG - 그래프 기반 의사결정 예측 서비스

    지식 그래프를 활용하여 과거의 유사한 의사결정 패턴을 찾고,
    LLM 없이 또는 LLM과 함께 더 정확한 의사결정을 수행합니다.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.decision_repo = DecisionLogRepository(db)
        self.node_repo = GraphNodeRepository(db)
        self.edge_repo = GraphEdgeRepository(db)
        self.keyword_extractor = KeywordExtractor()

    async def query_similar_decisions(
        self,
        user_input: str,
        context_state: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        유사한 과거 의사결정 검색

        Args:
            user_input: 사용자 입력
            context_state: 현재 컨텍스트 상태
            top_k: 반환할 최대 개수

        Returns:
            유사한 의사결정 리스트
        """
        logger.info(
            "query_similar_decisions",
            f"Querying similar decisions for: {user_input[:50]}...",
            top_k=top_k,
        )

        # 1. 키워드 추출
        keywords = await self.keyword_extractor.extract(user_input, context_state)

        # 2. 그래프에서 유사한 패턴 찾기
        similar_patterns = await self._find_similar_patterns(keywords, context_state)

        # 3. 패턴에 해당하는 의사결정 로그 조회
        similar_decisions = []
        for pattern in similar_patterns[:top_k]:
            decision_info = {
                "pattern": pattern,
                "keywords": keywords,
                "confidence": pattern.get("confidence", 0.0),
                "success_rate": pattern.get("success_rate", 0.0),
                "occurrence_count": pattern.get("occurrence_count", 0),
            }
            similar_decisions.append(decision_info)

        logger.info(
            "query_similar_decisions",
            f"Found {len(similar_decisions)} similar decisions",
        )

        return similar_decisions

    async def predict_decision(
        self,
        user_input: str,
        context_state: Dict[str, Any],
        decision_type: str = "routing",
        threshold: float = 0.75,
    ) -> Dict[str, Any]:
        """
        그래프 기반 의사결정 예측

        Args:
            user_input: 사용자 입력
            context_state: 현재 컨텍스트 상태
            decision_type: 의사결정 타입
            threshold: LLM 생략 확신도 임계값

        Returns:
            {
                "use_llm": bool,  # LLM 호출 필요 여부
                "decision": dict,  # 예측된 의사결정 (use_llm=False일 때만)
                "confidence": float,  # 확신도
                "reasoning": str,  # 예측 근거
                "similar_cases": list,  # 유사 사례들
            }
        """
        logger.info(
            "predict_decision",
            f"Predicting decision for: {user_input[:50]}...",
            decision_type=decision_type,
            threshold=threshold,
        )

        # 1. 유사한 의사결정 검색
        similar_decisions = await self.query_similar_decisions(
            user_input=user_input,
            context_state=context_state,
            top_k=10,
        )

        if not similar_decisions:
            logger.info("predict_decision", "No similar decisions found, using LLM")
            return {
                "use_llm": True,
                "decision": None,
                "confidence": 0.0,
                "reasoning": "그래프에서 유사한 패턴을 찾지 못했습니다. LLM 호출이 필요합니다.",
                "similar_cases": [],
            }

        # 2. 패턴 집계 및 신뢰도 계산
        aggregated = self._aggregate_patterns(similar_decisions)

        # 3. 최고 신뢰도 패턴 선택
        best_pattern = aggregated[0] if aggregated else None

        if not best_pattern:
            return {
                "use_llm": True,
                "decision": None,
                "confidence": 0.0,
                "reasoning": "신뢰할 만한 패턴을 찾지 못했습니다.",
                "similar_cases": similar_decisions,
            }

        confidence = best_pattern["confidence"]
        success_rate = best_pattern["success_rate"]
        occurrence_count = best_pattern["occurrence_count"]

        # 4. 확신도 기반 결정
        if confidence >= threshold and occurrence_count >= 5:
            # 그래프만으로 결정
            logger.info(
                "predict_decision",
                f"High confidence decision: {confidence:.2f} (threshold: {threshold})",
                pattern=best_pattern,
            )

            return {
                "use_llm": False,
                "decision": best_pattern.get("decision", {}),
                "confidence": confidence,
                "reasoning": (
                    f"과거 {occurrence_count}회 중 {int(success_rate * 100)}%의 성공률을 보인 패턴입니다. "
                    f"확신도 {confidence:.1%}로 LLM 없이 결정합니다."
                ),
                "similar_cases": similar_decisions[:5],
            }
        else:
            # LLM과 함께 사용
            logger.info(
                "predict_decision",
                f"Low confidence: {confidence:.2f}, using LLM with context",
            )

            return {
                "use_llm": True,
                "decision": None,
                "confidence": confidence,
                "reasoning": (
                    f"유사 패턴이 있지만 확신도({confidence:.1%})가 낮거나 "
                    f"발생 횟수({occurrence_count}회)가 적어 LLM과 함께 판단합니다."
                ),
                "similar_cases": similar_decisions[:5],
            }

    async def _find_similar_patterns(
        self,
        keywords: Dict[str, List[str]],
        context_state: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        키워드를 바탕으로 그래프에서 유사한 패턴 찾기

        Args:
            keywords: 추출된 키워드
            context_state: 컨텍스트 상태

        Returns:
            유사 패턴 리스트
        """
        patterns = []

        # 1. 동사 노드 찾기
        verb_nodes = []
        for verb in keywords.get("verbs", []):
            node = await self.node_repo.get_node("verb", verb)
            if node:
                verb_nodes.append(node)

        # 2. 캐릭터 노드 찾기
        character_nodes = []
        for character in keywords.get("targets", []):
            node = await self.node_repo.get_node("character", character)
            if node:
                character_nodes.append(node)

        # 3. 스테이지 노드 찾기
        stage_node = None
        if context_state:
            stage_value = context_state.get("stage") or context_state.get("current_stage")
            if stage_value:
                stage_node = await self.node_repo.get_node("stage", str(stage_value))

        # 4. 동사 -> 캐릭터 엣지 찾기 (ACTION_WITH)
        for verb_node in verb_nodes:
            for char_node in character_nodes:
                edges = await self.edge_repo.get_edges_from_node(
                    source_node_id=verb_node.node_id,
                    edge_type="ACTION_WITH",
                    min_occurrence=1,
                    limit=10,
                )

                for edge in edges:
                    if edge.target_node_id == char_node.node_id:
                        success_rate = (
                            edge.success_count / edge.occurrence_count
                            if edge.occurrence_count > 0
                            else 0.0
                        )

                        patterns.append({
                            "type": "action_with_character",
                            "verb": verb_node.node_value,
                            "character": char_node.node_value,
                            "success_rate": success_rate,
                            "occurrence_count": edge.occurrence_count,
                            "confidence": edge.avg_confidence or 0.5,
                            "decision": {
                                "action": verb_node.node_value,
                                "target": char_node.node_value,
                            },
                        })

        # 5. 스테이지별 패턴 찾기
        if stage_node:
            for verb_node in verb_nodes:
                edges = await self.edge_repo.get_edges_from_node(
                    source_node_id=verb_node.node_id,
                    edge_type="IN_STAGE",
                    min_occurrence=1,
                    limit=10,
                )

                for edge in edges:
                    if edge.target_node_id == stage_node.node_id:
                        success_rate = (
                            edge.success_count / edge.occurrence_count
                            if edge.occurrence_count > 0
                            else 0.0
                        )

                        patterns.append({
                            "type": "action_in_stage",
                            "verb": verb_node.node_value,
                            "stage": stage_node.node_value,
                            "success_rate": success_rate,
                            "occurrence_count": edge.occurrence_count,
                            "confidence": edge.avg_confidence or 0.5,
                            "decision": {
                                "action": verb_node.node_value,
                                "stage": stage_node.node_value,
                            },
                        })

        # 6. 성공률과 발생 횟수로 정렬
        patterns.sort(
            key=lambda p: (p["success_rate"], p["occurrence_count"]),
            reverse=True,
        )

        return patterns

    def _aggregate_patterns(
        self,
        similar_decisions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        유사한 의사결정들을 집계하여 최적 패턴 추출

        Args:
            similar_decisions: 유사 의사결정 리스트

        Returns:
            집계된 패턴 리스트
        """
        if not similar_decisions:
            return []

        # 패턴별로 그룹화
        pattern_groups: Dict[str, List[Dict[str, Any]]] = {}

        for decision in similar_decisions:
            pattern = decision.get("pattern", {})
            pattern_type = pattern.get("type", "unknown")

            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []

            pattern_groups[pattern_type].append(decision)

        # 각 그룹별로 집계
        aggregated = []

        for pattern_type, group in pattern_groups.items():
            if not group:
                continue

            # 평균 계산
            avg_confidence = sum(d.get("confidence", 0.0) for d in group) / len(group)
            avg_success_rate = sum(d.get("success_rate", 0.0) for d in group) / len(group)
            total_occurrence = sum(d.get("occurrence_count", 0) for d in group)

            # 대표 패턴 선택 (첫 번째)
            representative = group[0]

            aggregated.append({
                "type": pattern_type,
                "confidence": avg_confidence,
                "success_rate": avg_success_rate,
                "occurrence_count": total_occurrence,
                "group_size": len(group),
                "decision": representative["pattern"].get("decision", {}),
                "patterns": [d["pattern"] for d in group],
            })

        # 확신도와 성공률로 정렬
        aggregated.sort(
            key=lambda p: (p["confidence"] * 0.6 + p["success_rate"] * 0.4),
            reverse=True,
        )

        return aggregated

    async def get_context_for_llm(
        self,
        user_input: str,
        context_state: Dict[str, Any],
        top_k: int = 3,
    ) -> str:
        """
        LLM에 제공할 컨텍스트 생성

        Args:
            user_input: 사용자 입력
            context_state: 현재 컨텍스트
            top_k: 포함할 유사 사례 개수

        Returns:
            컨텍스트 문자열
        """
        similar_decisions = await self.query_similar_decisions(
            user_input=user_input,
            context_state=context_state,
            top_k=top_k,
        )

        if not similar_decisions:
            return ""

        context_parts = ["**과거 유사 상황:**"]

        for i, decision in enumerate(similar_decisions, 1):
            pattern = decision.get("pattern", {})
            success_rate = decision.get("success_rate", 0.0)
            occurrence = decision.get("occurrence_count", 0)

            context_parts.append(
                f"{i}. {pattern.get('verb', '')} + {pattern.get('character', '')} "
                f"(발생: {occurrence}회, 성공률: {success_rate:.0%})"
            )

        return "\n".join(context_parts)
