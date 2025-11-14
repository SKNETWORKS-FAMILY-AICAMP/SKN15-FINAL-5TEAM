"""
ML Models - Decision Logs and Knowledge Graph
"""
from sqlalchemy import Column, String, Text, Integer, Float, BigInteger, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime
from app.core.db.base import Base


class DecisionLog(Base):
    """
    에이전트 의사결정 로그

    모든 에이전트(Parent, Children, Router, Guardrail 등)의 의사결정을 기록하여
    나중에 GraphRAG 시스템에서 패턴 학습 및 예측에 사용합니다.
    """
    __tablename__ = "decision_logs"
    __table_args__ = (
        Index('idx_decision_logs_session', 'session_id', 'turn_number'),
        Index('idx_decision_logs_agent', 'agent_name', 'decision_type'),
        Index('idx_decision_logs_created', 'created_at'),
        Index('idx_decision_logs_keywords', 'extracted_keywords', postgresql_using='gin'),
        Index('idx_decision_logs_context', 'context_state', postgresql_using='gin'),
        {"schema": "ml"}
    )

    # Primary Key
    decision_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Session & Turn Info
    session_id = Column(UUID(as_uuid=True), nullable=False)
    turn_number = Column(Integer)

    # Agent Info
    agent_name = Column(String(50), nullable=False)  # parent, children, router, guardrail, etc.
    decision_type = Column(String(50), nullable=False)  # stage_selection, dialogue_generation, routing, etc.

    # Input Data
    user_input = Column(Text)
    extracted_keywords = Column(JSONB)  # {verbs: [], targets: [], modifiers: []}
    context_state = Column(JSONB)  # {stage, affinity, turn_count, memories, etc.}

    # Decision Process
    llm_prompt = Column(Text)
    llm_parameters = Column(JSONB)  # {model, temperature, max_tokens}
    llm_model = Column(String(100))

    # Output Data
    decision_output = Column(JSONB, nullable=False)  # 실제 선택된 분기/결과
    reasoning = Column(Text)  # LLM이 제공한 reasoning
    confidence = Column(Float)

    # Performance Metrics
    execution_time_ms = Column(Integer)

    # Error Handling
    is_error = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text)

    # Timestamp
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<DecisionLog(id={self.decision_id}, agent={self.agent_name}, type={self.decision_type})>"


class GraphNode(Base):
    """
    지식 그래프 노드

    동사, 캐릭터, 스테이지, 상황 등을 노드로 저장합니다.
    예: "싸운다", "렌고쿠", "무한열차_보스전", "친밀도_높음"
    """
    __tablename__ = "graph_nodes"
    __table_args__ = (
        Index('idx_graph_nodes_type', 'node_type'),
        Index('idx_graph_nodes_value', 'node_value'),
        Index('idx_graph_nodes_frequency', 'frequency'),
        Index('idx_graph_nodes_properties', 'properties', postgresql_using='gin'),
        Index('uq_graph_nodes_type_value', 'node_type', 'normalized_value', unique=True),
        {"schema": "knowledge"}
    )

    # Primary Key
    node_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Node Info
    node_type = Column(String(50), nullable=False)  # verb, character, stage, context
    node_value = Column(Text, nullable=False)  # 실제 값
    normalized_value = Column(String(200))  # 정규화된 값 (검색용)

    # Properties
    properties = Column(JSONB)  # 추가 속성

    # Statistics
    frequency = Column(Integer, default=1, nullable=False)  # 출현 빈도
    success_rate = Column(Float)  # 성공률 (해당하는 경우)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<GraphNode(id={self.node_id}, type={self.node_type}, value={self.node_value})>"


class GraphEdge(Base):
    """
    지식 그래프 엣지 (관계)

    노드 간의 관계를 저장합니다.
    예: ("싸운다", "렌고쿠") -> "무한열차_보스전" (빈도: 120회, 성공: 96회)
    """
    __tablename__ = "graph_edges"
    __table_args__ = (
        Index('idx_graph_edges_source', 'source_node_id'),
        Index('idx_graph_edges_target', 'target_node_id'),
        Index('idx_graph_edges_type', 'edge_type'),
        Index('idx_graph_edges_weight', 'weight'),
        Index('idx_graph_edges_properties', 'properties', postgresql_using='gin'),
        Index('uq_graph_edges_source_target_type', 'source_node_id', 'target_node_id', 'edge_type', unique=True),
        {"schema": "knowledge"}
    )

    # Primary Key
    edge_id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Edge Info
    source_node_id = Column(BigInteger, ForeignKey('knowledge.graph_nodes.node_id', ondelete='CASCADE'), nullable=False)
    target_node_id = Column(BigInteger, ForeignKey('knowledge.graph_nodes.node_id', ondelete='CASCADE'), nullable=False)
    edge_type = Column(String(50), nullable=False)  # ACTION_WITH, IN_STAGE, LED_TO_BRANCH

    # Properties
    properties = Column(JSONB)  # 추가 속성

    # Statistics
    occurrence_count = Column(Integer, default=1, nullable=False)  # 발생 횟수
    success_count = Column(Integer, default=0, nullable=False)  # 성공 횟수
    avg_confidence = Column(Float)  # 평균 확신도
    weight = Column(Float, default=1.0, nullable=False)  # 가중치

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<GraphEdge(id={self.edge_id}, type={self.edge_type}, source={self.source_node_id}, target={self.target_node_id})>"
