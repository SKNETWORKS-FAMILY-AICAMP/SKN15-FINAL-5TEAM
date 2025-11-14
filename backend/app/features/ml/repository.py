"""
ML Repository - Decision Logs and Knowledge Graph DB Access
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from .models import DecisionLog, GraphNode, GraphEdge
from app.core.logging import get_repository_logger

logger = get_repository_logger("ML")


class DecisionLogRepository:
    """
    DecisionLog CRUD Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_decision(
        self,
        session_id: UUID,
        turn_number: Optional[int],
        agent_name: str,
        decision_type: str,
        decision_output: Dict[str, Any],
        user_input: Optional[str] = None,
        extracted_keywords: Optional[Dict[str, Any]] = None,
        context_state: Optional[Dict[str, Any]] = None,
        llm_prompt: Optional[str] = None,
        llm_parameters: Optional[Dict[str, Any]] = None,
        llm_model: Optional[str] = None,
        reasoning: Optional[str] = None,
        confidence: Optional[float] = None,
        execution_time_ms: Optional[int] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
    ) -> DecisionLog:
        """
        의사결정 로그 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            agent_name: 에이전트 이름 (parent, children, router, etc.)
            decision_type: 의사결정 타입 (stage_selection, dialogue_generation, etc.)
            decision_output: 의사결정 결과
            user_input: 사용자 입력
            extracted_keywords: 추출된 키워드
            context_state: 컨텍스트 상태
            llm_prompt: LLM 프롬프트
            llm_parameters: LLM 파라미터
            llm_model: LLM 모델명
            reasoning: 의사결정 이유
            confidence: 확신도
            execution_time_ms: 실행 시간 (ms)
            is_error: 에러 여부
            error_message: 에러 메시지

        Returns:
            저장된 DecisionLog
        """
        logger.info(
            "save_decision",
            f"Saving decision log: {agent_name}/{decision_type}",
            session_id=session_id,
            turn_number=turn_number,
        )

        decision_log = DecisionLog(
            session_id=session_id,
            turn_number=turn_number,
            agent_name=agent_name,
            decision_type=decision_type,
            user_input=user_input,
            extracted_keywords=extracted_keywords,
            context_state=context_state,
            llm_prompt=llm_prompt,
            llm_parameters=llm_parameters,
            llm_model=llm_model,
            decision_output=decision_output,
            reasoning=reasoning,
            confidence=confidence,
            execution_time_ms=execution_time_ms,
            is_error=is_error,
            error_message=error_message,
        )

        self.db.add(decision_log)
        await self.db.flush()

        logger.info("save_decision", f"Decision log saved: {decision_log.decision_id}")
        return decision_log

    async def get_recent_decisions(
        self,
        agent_name: Optional[str] = None,
        decision_type: Optional[str] = None,
        session_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[DecisionLog]:
        """
        최근 의사결정 로그 조회

        Args:
            agent_name: 필터링할 에이전트 이름
            decision_type: 필터링할 의사결정 타입
            session_id: 필터링할 세션 ID
            limit: 최대 개수

        Returns:
            DecisionLog 리스트
        """
        logger.debug(
            "get_recent_decisions",
            "Fetching recent decisions",
            agent_name=agent_name,
            decision_type=decision_type,
            limit=limit,
        )

        stmt = select(DecisionLog).order_by(desc(DecisionLog.created_at))

        if agent_name:
            stmt = stmt.where(DecisionLog.agent_name == agent_name)
        if decision_type:
            stmt = stmt.where(DecisionLog.decision_type == decision_type)
        if session_id:
            stmt = stmt.where(DecisionLog.session_id == session_id)

        stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        decisions = result.scalars().all()

        logger.debug("get_recent_decisions", f"Fetched {len(decisions)} decisions")
        return list(decisions)

    async def get_decisions_for_graph_building(
        self,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[DecisionLog]:
        """
        그래프 구축용 의사결정 로그 조회

        Args:
            since: 이 시간 이후의 로그만 가져오기
            limit: 최대 개수

        Returns:
            DecisionLog 리스트
        """
        logger.debug("get_decisions_for_graph_building", "Fetching decisions for graph building", limit=limit)

        stmt = select(DecisionLog).where(
            and_(
                DecisionLog.is_error == False,  # 에러 제외
                DecisionLog.extracted_keywords.isnot(None),  # 키워드가 있는 것만
            )
        ).order_by(desc(DecisionLog.created_at))

        if since:
            stmt = stmt.where(DecisionLog.created_at >= since)

        stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        decisions = result.scalars().all()

        logger.debug("get_decisions_for_graph_building", f"Fetched {len(decisions)} decisions for graph building")
        return list(decisions)


class GraphNodeRepository:
    """
    GraphNode CRUD Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_node(
        self,
        node_type: str,
        node_value: str,
        properties: Optional[Dict[str, Any]] = None,
        increment_frequency: bool = True,
    ) -> GraphNode:
        """
        노드 추가 또는 업데이트 (빈도 증가)

        Args:
            node_type: 노드 타입 (verb, character, stage, context)
            node_value: 노드 값
            properties: 추가 속성
            increment_frequency: 빈도 증가 여부

        Returns:
            GraphNode
        """
        normalized_value = node_value.lower().strip()

        # Upsert using INSERT ... ON CONFLICT
        stmt = insert(GraphNode).values(
            node_type=node_type,
            node_value=node_value,
            normalized_value=normalized_value,
            properties=properties,
            frequency=1,
        ).on_conflict_do_update(
            index_elements=['node_type', 'normalized_value'],
            set_={
                'frequency': GraphNode.frequency + (1 if increment_frequency else 0),
                'properties': properties if properties else GraphNode.properties,
                'updated_at': datetime.utcnow(),
            }
        ).returning(GraphNode)

        result = await self.db.execute(stmt)
        node = result.scalar_one()
        await self.db.flush()

        logger.debug("upsert_node", f"Upserted node: {node_type}/{node_value} (id={node.node_id})")
        return node

    async def get_node(
        self,
        node_type: str,
        node_value: str,
    ) -> Optional[GraphNode]:
        """
        노드 조회

        Args:
            node_type: 노드 타입
            node_value: 노드 값

        Returns:
            GraphNode or None
        """
        normalized_value = node_value.lower().strip()

        stmt = select(GraphNode).where(
            and_(
                GraphNode.node_type == node_type,
                GraphNode.normalized_value == normalized_value,
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_nodes(
        self,
        node_type: Optional[str] = None,
        search_query: Optional[str] = None,
        min_frequency: int = 1,
        limit: int = 100,
    ) -> List[GraphNode]:
        """
        노드 검색

        Args:
            node_type: 노드 타입 필터
            search_query: 검색 쿼리
            min_frequency: 최소 빈도
            limit: 최대 개수

        Returns:
            GraphNode 리스트
        """
        stmt = select(GraphNode).where(GraphNode.frequency >= min_frequency)

        if node_type:
            stmt = stmt.where(GraphNode.node_type == node_type)

        if search_query:
            stmt = stmt.where(GraphNode.node_value.ilike(f"%{search_query}%"))

        stmt = stmt.order_by(desc(GraphNode.frequency)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class GraphEdgeRepository:
    """
    GraphEdge CRUD Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_edge(
        self,
        source_node_id: int,
        target_node_id: int,
        edge_type: str,
        success: bool = True,
        confidence: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> GraphEdge:
        """
        엣지 추가 또는 업데이트 (통계 업데이트)

        Args:
            source_node_id: 소스 노드 ID
            target_node_id: 타겟 노드 ID
            edge_type: 엣지 타입
            success: 성공 여부
            confidence: 확신도
            properties: 추가 속성

        Returns:
            GraphEdge
        """
        # Upsert using INSERT ... ON CONFLICT
        stmt = insert(GraphEdge).values(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            occurrence_count=1,
            success_count=1 if success else 0,
            avg_confidence=confidence,
            properties=properties,
        ).on_conflict_do_update(
            index_elements=['source_node_id', 'target_node_id', 'edge_type'],
            set_={
                'occurrence_count': GraphEdge.occurrence_count + 1,
                'success_count': GraphEdge.success_count + (1 if success else 0),
                'avg_confidence': (
                    # 이동 평균 계산
                    func.coalesce(
                        (GraphEdge.avg_confidence * GraphEdge.occurrence_count + (confidence or 0)) / (GraphEdge.occurrence_count + 1),
                        confidence
                    ) if confidence else GraphEdge.avg_confidence
                ),
                'properties': properties if properties else GraphEdge.properties,
                'updated_at': datetime.utcnow(),
            }
        ).returning(GraphEdge)

        result = await self.db.execute(stmt)
        edge = result.scalar_one()
        await self.db.flush()

        logger.debug("upsert_edge", f"Upserted edge: {edge_type} ({source_node_id} -> {target_node_id}, id={edge.edge_id})")
        return edge

    async def get_edges_from_node(
        self,
        source_node_id: int,
        edge_type: Optional[str] = None,
        min_occurrence: int = 1,
        limit: int = 100,
    ) -> List[GraphEdge]:
        """
        특정 노드로부터 나가는 엣지 조회

        Args:
            source_node_id: 소스 노드 ID
            edge_type: 엣지 타입 필터
            min_occurrence: 최소 발생 횟수
            limit: 최대 개수

        Returns:
            GraphEdge 리스트
        """
        stmt = select(GraphEdge).where(
            and_(
                GraphEdge.source_node_id == source_node_id,
                GraphEdge.occurrence_count >= min_occurrence,
            )
        )

        if edge_type:
            stmt = stmt.where(GraphEdge.edge_type == edge_type)

        stmt = stmt.order_by(desc(GraphEdge.weight), desc(GraphEdge.occurrence_count)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_top_edges_by_success_rate(
        self,
        source_node_id: int,
        edge_type: str,
        min_occurrence: int = 5,
        limit: int = 10,
    ) -> List[GraphEdge]:
        """
        성공률이 높은 엣지 조회

        Args:
            source_node_id: 소스 노드 ID
            edge_type: 엣지 타입
            min_occurrence: 최소 발생 횟수 (신뢰도 확보)
            limit: 최대 개수

        Returns:
            GraphEdge 리스트 (성공률 순)
        """
        stmt = select(GraphEdge).where(
            and_(
                GraphEdge.source_node_id == source_node_id,
                GraphEdge.edge_type == edge_type,
                GraphEdge.occurrence_count >= min_occurrence,
            )
        ).order_by(
            desc(text("success_count::float / occurrence_count")),
            desc(GraphEdge.occurrence_count)
        ).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
