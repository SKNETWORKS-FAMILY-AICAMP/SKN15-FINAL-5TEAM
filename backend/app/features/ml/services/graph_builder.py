"""
GraphBuilder Service

의사결정 로그로부터 지식 그래프를 구축하는 서비스
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ..repository import DecisionLogRepository, GraphNodeRepository, GraphEdgeRepository
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("GraphBuilder")


class GraphBuilder:
    """
    지식 그래프 구축 서비스

    DecisionLog 데이터를 분석하여 지식 그래프(노드 & 엣지)를 구축합니다.

    노드 타입:
    - verb: 동사 (싸운다, 설득한다 등)
    - character: 캐릭터 (렌고쿠, 이노스케 등)
    - stage: 스테이지 (무한열차_보스전 등)
    - context: 상황 (친밀도_높음, 위기상황 등)

    엣지 타입:
    - ACTION_WITH: (verb) ---> (character)
    - IN_STAGE: (verb + character) ---> (stage)
    - LED_TO_BRANCH: (조합) ---> (분기 결과)
    - HAS_CONTEXT: (action) ---> (context)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.decision_repo = DecisionLogRepository(db)
        self.node_repo = GraphNodeRepository(db)
        self.edge_repo = GraphEdgeRepository(db)

    async def build_from_recent_decisions(
        self,
        hours: int = 24,
        limit: int = 1000,
    ) -> Dict[str, int]:
        """
        최근 의사결정 로그로부터 그래프 구축

        Args:
            hours: 최근 N시간 이내의 로그
            limit: 최대 로그 개수

        Returns:
            통계: {nodes_created: int, edges_created: int}
        """
        logger.info("build_from_recent_decisions", f"Building graph from recent {hours}h decisions")

        since = datetime.utcnow() - timedelta(hours=hours)
        decisions = await self.decision_repo.get_decisions_for_graph_building(
            since=since,
            limit=limit,
        )

        logger.info("build_from_recent_decisions", f"Fetched {len(decisions)} decisions")

        nodes_created = 0
        edges_created = 0

        for decision in decisions:
            try:
                result = await self._process_decision(decision)
                nodes_created += result["nodes"]
                edges_created += result["edges"]
            except Exception as e:
                logger.error(
                    "build_from_recent_decisions",
                    f"Failed to process decision {decision.decision_id}: {e}",
                    exc_info=True,
                )

        logger.info(
            "build_from_recent_decisions",
            f"Graph building completed: {nodes_created} nodes, {edges_created} edges",
        )

        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "decisions_processed": len(decisions),
        }

    async def _process_decision(self, decision) -> Dict[str, int]:
        """
        단일 의사결정 로그 처리

        Args:
            decision: DecisionLog 인스턴스

        Returns:
            {nodes: int, edges: int}
        """
        nodes_count = 0
        edges_count = 0

        # 키워드가 없으면 스킵
        if not decision.extracted_keywords:
            return {"nodes": 0, "edges": 0}

        keywords = decision.extracted_keywords
        context = decision.context_state or {}
        decision_output = decision.decision_output or {}

        # 1. 노드 생성: 동사 (verbs)
        verb_nodes = []
        for verb in keywords.get("verbs", []):
            node = await self.node_repo.upsert_node(
                node_type="verb",
                node_value=verb,
                properties={"agent": decision.agent_name},
            )
            verb_nodes.append(node)
            nodes_count += 1

        # 2. 노드 생성: 캐릭터 (targets)
        character_nodes = []
        for target in keywords.get("targets", []):
            node = await self.node_repo.upsert_node(
                node_type="character",
                node_value=target,
            )
            character_nodes.append(node)
            nodes_count += 1

        # 3. 노드 생성: 스테이지
        stage_node = None
        if "stage" in context or "current_stage" in context:
            stage_value = context.get("stage") or context.get("current_stage")
            if stage_value:
                stage_node = await self.node_repo.upsert_node(
                    node_type="stage",
                    node_value=str(stage_value),
                )
                nodes_count += 1

        # 4. 노드 생성: 감정 (emotions)
        emotion_nodes = []
        for emotion in keywords.get("emotions", []):
            node = await self.node_repo.upsert_node(
                node_type="context",
                node_value=f"emotion_{emotion}",
                properties={"category": "emotion"},
            )
            emotion_nodes.append(node)
            nodes_count += 1

        # 5. 엣지 생성: ACTION_WITH (verb -> character)
        for verb_node in verb_nodes:
            for char_node in character_nodes:
                success = self._is_successful_decision(decision)
                confidence = decision.confidence

                edge = await self.edge_repo.upsert_edge(
                    source_node_id=verb_node.node_id,
                    target_node_id=char_node.node_id,
                    edge_type="ACTION_WITH",
                    success=success,
                    confidence=confidence,
                    properties={
                        "agent": decision.agent_name,
                        "decision_type": decision.decision_type,
                    },
                )
                edges_count += 1

        # 6. 엣지 생성: IN_STAGE (character -> stage)
        if stage_node:
            for char_node in character_nodes:
                edge = await self.edge_repo.upsert_edge(
                    source_node_id=char_node.node_id,
                    target_node_id=stage_node.node_id,
                    edge_type="IN_STAGE",
                    success=self._is_successful_decision(decision),
                    confidence=decision.confidence,
                )
                edges_count += 1

            # 동사 -> 스테이지
            for verb_node in verb_nodes:
                edge = await self.edge_repo.upsert_edge(
                    source_node_id=verb_node.node_id,
                    target_node_id=stage_node.node_id,
                    edge_type="IN_STAGE",
                    success=self._is_successful_decision(decision),
                    confidence=decision.confidence,
                )
                edges_count += 1

        # 7. 엣지 생성: HAS_EMOTION (verb -> emotion)
        for verb_node in verb_nodes:
            for emotion_node in emotion_nodes:
                edge = await self.edge_repo.upsert_edge(
                    source_node_id=verb_node.node_id,
                    target_node_id=emotion_node.node_id,
                    edge_type="HAS_EMOTION",
                    success=self._is_successful_decision(decision),
                    confidence=decision.confidence,
                )
                edges_count += 1

        return {"nodes": nodes_count, "edges": edges_count}

    def _is_successful_decision(self, decision) -> bool:
        """
        의사결정이 성공적이었는지 판단

        Args:
            decision: DecisionLog 인스턴스

        Returns:
            성공 여부
        """
        # 에러가 없으면 일단 성공으로 간주
        if decision.is_error:
            return False

        # confidence가 높으면 성공
        if decision.confidence and decision.confidence > 0.7:
            return True

        # decision_output에 success 필드가 있으면 사용
        if decision.decision_output:
            if "success" in decision.decision_output:
                return bool(decision.decision_output["success"])

        # 기본값: True (일단 성공으로 간주)
        return True

    async def build_full_graph(self, limit: int = 10000) -> Dict[str, int]:
        """
        전체 의사결정 로그로부터 그래프 재구축

        Args:
            limit: 최대 로그 개수

        Returns:
            통계
        """
        logger.info("build_full_graph", f"Building full graph from up to {limit} decisions")

        decisions = await self.decision_repo.get_decisions_for_graph_building(
            since=None,
            limit=limit,
        )

        logger.info("build_full_graph", f"Fetched {len(decisions)} decisions")

        nodes_created = 0
        edges_created = 0

        for decision in decisions:
            try:
                result = await self._process_decision(decision)
                nodes_created += result["nodes"]
                edges_created += result["edges"]
            except Exception as e:
                logger.error(
                    "build_full_graph",
                    f"Failed to process decision {decision.decision_id}: {e}",
                    exc_info=True,
                )

        logger.info(
            "build_full_graph",
            f"Full graph building completed: {nodes_created} nodes, {edges_created} edges",
        )

        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "decisions_processed": len(decisions),
        }

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        그래프 통계 조회

        Returns:
            통계 정보
        """
        logger.info("get_graph_statistics", "Fetching graph statistics")

        # 노드 타입별 개수
        verb_nodes = await self.node_repo.search_nodes(node_type="verb", limit=10000)
        character_nodes = await self.node_repo.search_nodes(node_type="character", limit=10000)
        stage_nodes = await self.node_repo.search_nodes(node_type="stage", limit=10000)
        context_nodes = await self.node_repo.search_nodes(node_type="context", limit=10000)

        stats = {
            "nodes": {
                "total": len(verb_nodes) + len(character_nodes) + len(stage_nodes) + len(context_nodes),
                "by_type": {
                    "verb": len(verb_nodes),
                    "character": len(character_nodes),
                    "stage": len(stage_nodes),
                    "context": len(context_nodes),
                },
            },
            "top_verbs": [
                {"value": n.node_value, "frequency": n.frequency}
                for n in sorted(verb_nodes, key=lambda x: x.frequency, reverse=True)[:10]
            ],
            "top_characters": [
                {"value": n.node_value, "frequency": n.frequency}
                for n in sorted(character_nodes, key=lambda x: x.frequency, reverse=True)[:10]
            ],
        }

        logger.info("get_graph_statistics", "Graph statistics fetched", stats=stats)
        return stats
