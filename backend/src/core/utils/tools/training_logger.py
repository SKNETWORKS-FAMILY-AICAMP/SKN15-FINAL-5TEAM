"""
Training Logger for AI Model Fine-tuning

Phase 4: SLLM LoRA 훈련을 위한 로그 수집 시스템
- 최소 전처리로 의미 있는 로그 생성
- 맥락 중심 하이브리드 자동 라벨링 (Rule 40% + LLM 60%)
- 최근 5개 대화 기반 맥락 분석
- 세계관/캐릭터 톤/관계성 평가
- 비동기 로깅으로 성능 영향 최소화
"""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import psycopg2
from psycopg2.extras import Json

# OpenAI for LLM-based labeling
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[TrainingLogger] Warning: openai package not installed. LLM-based labeling will be disabled.")

# Entity extraction and embedding generation
try:
    from src.core.utils.entity_extractor import EntityExtractor
    from src.core.utils.embedding_matcher import EmbeddingClient
    from src.core.utils.relationship_extractor import RelationshipExtractor
    from src.infrastructure.database.db_manager import DatabaseManager
    ENTITY_EXTRACTION_AVAILABLE = True
except ImportError as e:
    ENTITY_EXTRACTION_AVAILABLE = False
    print(f"[TrainingLogger] Warning: Entity extraction not available: {e}")


class TrainingLogger:
    """에이전트 실행 로그를 LogDB에 수집하는 클래스 (맥락 중심 하이브리드 평가)"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """LogDB 연결 및 LLM 설정 초기화"""
        self.logdb_url = os.getenv(
            "LOGDB_URL",
            os.getenv("DATABASE_URL"),  # Fallback to DATABASE_URL
        )
        self.connection = None
        self.enabled = os.getenv("TRAINING_LOGGER_ENABLED", "true").lower() == "true"

        # LLM-based Auto-labeling 설정
        self.llm_labeling_enabled = (
            OPENAI_AVAILABLE and
            os.getenv("LLM_LABELING_ENABLED", "false").lower() == "true"
        )
        self.llm_model = os.getenv("LLM_LABELING_MODEL", "gpt-4o-mini")

        # OpenAI API 설정
        if self.llm_labeling_enabled:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                openai.api_key = openai_api_key
                print(f"[TrainingLogger] LLM-based labeling enabled with {self.llm_model}")
            else:
                self.llm_labeling_enabled = False
                print("[TrainingLogger] Warning: OPENAI_API_KEY not found. LLM labeling disabled.")

        # 평가 캐시 (비용 절감) - TTL 지원
        self.evaluation_cache = {}  # {hash: {"score": float, "reason": str, "timestamp": float}}
        self.cache_ttl = 3600  # 1시간 (초 단위)

        # A/B 테스트 설정
        self.ab_test_enabled = os.getenv("AB_TEST_ENABLED", "false").lower() == "true"
        self.ab_test_ratio = float(os.getenv("AB_TEST_RATIO", "0.1"))  # 10%만 하이브리드

        # Graph RAG: Entity extraction and embedding generation
        self.entity_extraction_enabled = (
            ENTITY_EXTRACTION_AVAILABLE and
            os.getenv("ENTITY_EXTRACTION_ENABLED", "true").lower() == "true"
        )

        if self.entity_extraction_enabled:
            try:
                self.entity_extractor = EntityExtractor()
                self.embedding_client = EmbeddingClient()
                self.relationship_extractor = RelationshipExtractor(
                    enable_llm=os.getenv("RELATIONSHIP_LLM_ENABLED", "false").lower() == "true"
                )
                self.db_manager = db_manager or DatabaseManager(
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", "5433")),
                    dbname=os.getenv("DB_NAME", "kimedb"),
                    user=os.getenv("DB_USER", "kime"),
                    password=os.getenv("DB_PASSWORD", "dev123")
                )
                print("[TrainingLogger] Entity extraction, relationship extraction, and embedding generation enabled")
            except Exception as e:
                self.entity_extraction_enabled = False
                print(f"[TrainingLogger] Failed to initialize entity extraction: {e}")

    def get_connection(self):
        """LogDB 연결 가져오기 (lazy loading)"""
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg2.connect(self.logdb_url)
            except Exception as e:
                print(f"[TrainingLogger] Failed to connect to LogDB: {e}")
                self.enabled = False
        return self.connection

    def log_agent_execution(
        self,
        agent_name: str,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
        latency_ms: int,
        token_count: Optional[int] = None,
        llm_model: Optional[str] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """
        에이전트 실행 로그 저장 (동기)

        Args:
            agent_name: 에이전트 이름 ('router', 'parent', 'children', 'dialogue')
            state: GraphState 스냅샷 (context)
            model_output: 에이전트 출력 (next_node, agent_inputs 등)
            latency_ms: 실행 시간 (밀리초)
            token_count: 사용된 토큰 수
            llm_model: 사용된 LLM 모델
            is_error: 에러 발생 여부
            error_message: 에러 메시지

        Returns:
            int: training_logs 테이블의 id (실패 시 None)
        """
        if not self.enabled:
            return None

        try:
            # Context 추출 (state에서 핵심 정보만)
            context = self._extract_context(state)

            # 자동 라벨링
            outcome, outcome_reason, feedback_score = self._auto_label(
                agent_name, state, model_output, is_error
            )

            # 데이터 준비
            insert_data = {
                "session_id": str(state.get("session_id", "")),
                "turn_count": state.get("turn_count", 0),
                "scenario_id": state.get("scenario_id", ""),
                "current_stage": state.get("current_stage", ""),
                "agent_name": agent_name,
                "user_input": state.get("user_input", ""),
                "context": Json(context),
                "model_output": Json(model_output),
                "latency_ms": latency_ms,
                "token_count": token_count,
                "llm_model": llm_model,
                "outcome": outcome,
                "outcome_reason": outcome_reason,
                "feedback_score": feedback_score,
                "is_error": is_error,
                "error_message": error_message,
                "labeled_at": datetime.now() if outcome else None,
            }

            # DB에 삽입
            conn = self.get_connection()
            if conn is None:
                return None

            cursor = conn.cursor()
            insert_query = """
                INSERT INTO training_logs (
                    session_id, turn_count, scenario_id, current_stage,
                    agent_name, user_input, context, model_output,
                    latency_ms, token_count, llm_model,
                    outcome, outcome_reason, feedback_score,
                    is_error, error_message, labeled_at
                ) VALUES (
                    %(session_id)s, %(turn_count)s, %(scenario_id)s, %(current_stage)s,
                    %(agent_name)s, %(user_input)s, %(context)s, %(model_output)s,
                    %(latency_ms)s, %(token_count)s, %(llm_model)s,
                    %(outcome)s, %(outcome_reason)s, %(feedback_score)s,
                    %(is_error)s, %(error_message)s, %(labeled_at)s
                )
                RETURNING id;
            """

            cursor.execute(insert_query, insert_data)
            log_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

            # Graph RAG: Extract entities and generate embeddings
            if self.entity_extraction_enabled and log_id:
                try:
                    self._process_entities_and_embeddings(
                        log_id=log_id,
                        session_id=str(state.get("session_id", "")),
                        turn_count=state.get("turn_count", 0),
                        user_input=state.get("user_input", ""),
                        model_output=model_output,
                        context=context
                    )
                except Exception as e:
                    print(f"[TrainingLogger] Entity extraction failed for log {log_id}: {e}")

            return log_id

        except Exception as e:
            print(f"[TrainingLogger] Error logging {agent_name}: {e}")
            if self.connection and not self.connection.closed:
                self.connection.rollback()
            return None

    def _extract_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        State에서 학습에 필요한 핵심 정보만 추출

        목표: 최소 전처리로도 의미 있는 컨텍스트 제공
        """
        context = {
            # 기본 정보
            "scenario_id": state.get("scenario_id"),
            "current_stage": state.get("current_stage"),
            "turn_count": state.get("turn_count"),
            "user_input": state.get("user_input"),

            # 대화 이력 (최근 5개만) - LLM 평가용
            "history": (state.get("history", []))[-5:] if state.get("history") else [],
            "short_term_memory": (state.get("short_term_memory", []))[-5:] if state.get("short_term_memory") else [],

            # 현재 참여 캐릭터
            "participants": state.get("participants", []),

            # 분위기 (선택지, 미션 등)
            "atmosphere": state.get("atmosphere"),

            # 친밀도 (LLM 평가용 - 관계성 반영)
            "affinity": state.get("affinity", {}),
            "affinity_scores": state.get("affinity_scores", {}),

            # 캐릭터 정보 (LLM 평가용 - 톤 평가)
            "characters": state.get("characters", {}),

            # 이전 대사 (Children/Dialogue 에이전트용)
            "output": state.get("output", {}).get("dialogues", []),

            # Parent Agent용: children_ctx (open_narrative 등에서 생성된 대사)
            "children_ctx": state.get("children_ctx"),
        }

        # None 값 제거 (JSON 크기 최소화)
        return {k: v for k, v in context.items() if v is not None}

    def _process_entities_and_embeddings(
        self,
        log_id: int,
        session_id: str,
        turn_count: int,
        user_input: str,
        model_output: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """
        Extract entities and generate embeddings for training log

        Processes:
        1. Extract entities from user_input and model_output
        2. Generate embedding for the log text
        3. Save entities to database
        4. Link entities to training log via entity_mentions
        5. Update training_logs with embedding and entity IDs
        """
        # Combine relevant text for entity extraction
        extraction_text = user_input

        # Add model output dialogues if present
        if "dialogues" in model_output:
            dialogues = model_output["dialogues"]
            if isinstance(dialogues, list):
                dialogue_text = " ".join([d.get("dialogue", "") for d in dialogues if isinstance(d, dict)])
                extraction_text += f" {dialogue_text}"
        elif "dialogue" in model_output:
            extraction_text += f" {model_output['dialogue']}"

        # Extract entities
        entities = self.entity_extractor.extract_entities(
            text=extraction_text,
            context={"session_id": session_id, "turn_number": turn_count}
        )

        # Generate embedding for the entire log context
        embedding_text = f"{user_input}"
        if context.get("history"):
            # Include recent history for better context
            recent_history = context["history"][-2:]  # Last 2 turns
            history_text = " ".join([h for h in recent_history if isinstance(h, str)])
            embedding_text = f"{history_text} {embedding_text}"

        embedding = self.embedding_client.embed(embedding_text)

        # Save entities and collect entity IDs
        entity_ids = []
        for entity in entities:
            # Generate entity embedding if not exists
            entity_embedding_text = f"{entity.entity_type}: {entity.entity_name}"
            if entity.description:
                entity_embedding_text += f" - {entity.description}"

            entity_embedding = self.embedding_client.embed(entity_embedding_text)

            # Save entity (upsert)
            entity_id = self.db_manager.save_entity(
                entity_type=entity.entity_type,
                entity_name=entity.entity_name,
                canonical_name=entity.canonical_name,
                description=entity.description,
                properties=entity.properties,
                embedding=entity_embedding,
                importance_score=entity.confidence  # Use extraction confidence as importance
            )

            if entity_id:
                entity_ids.append(entity_id)

                # Save entity mention (link to training log)
                self.db_manager.save_entity_mention(
                    entity_id=entity_id,
                    source_type="training_log",
                    source_id=log_id,
                    session_id=session_id,
                    turn_number=turn_count,
                    mention_context=entity.context,
                    extraction_method=entity.extraction_method,
                    confidence=entity.confidence
                )

        # Update training_logs with embedding and mentioned entity IDs
        if embedding or entity_ids:
            try:
                conn = self.get_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE training_logs
                        SET embedding = %s,
                            mentioned_entity_ids = %s
                        WHERE id = %s
                    """, (embedding, entity_ids, log_id))
                    conn.commit()
                    cursor.close()

                    print(f"[TrainingLogger] Processed {len(entities)} entities for log {log_id}")
            except Exception as e:
                print(f"[TrainingLogger] Failed to update log {log_id} with entities/embedding: {e}")

        # Extract and save relationships between entities
        if len(entity_ids) >= 2:
            try:
                relationships_saved = self._extract_and_save_relationships(
                    extraction_text=extraction_text,
                    entities=entities,
                    session_id=session_id,
                    turn_count=turn_count
                )
                if relationships_saved > 0:
                    print(f"[TrainingLogger] Saved {relationships_saved} relationships for log {log_id}")
            except Exception as e:
                print(f"[TrainingLogger] Failed to extract relationships for log {log_id}: {e}")

    def _extract_and_save_relationships(
        self,
        extraction_text: str,
        entities: List[Any],
        session_id: str,
        turn_count: int
    ) -> int:
        """
        Extract and save relationships between entities

        Args:
            extraction_text: Combined text for relationship extraction
            entities: List of extracted Entity objects
            session_id: Session ID
            turn_count: Turn number

        Returns:
            Number of relationships saved
        """
        # Convert entities to the format expected by RelationshipExtractor
        entity_dicts = []
        for entity in entities:
            entity_dicts.append({
                "entity_id": getattr(entity, "entity_id", None),
                "entity_name": entity.entity_name,
                "canonical_name": entity.canonical_name,
                "entity_type": entity.entity_type,
                "confidence": entity.confidence
            })

        # Extract relationships using RelationshipExtractor
        relationships = self.relationship_extractor.extract_relationships(
            text=extraction_text,
            entities=entity_dicts,
            session_id=session_id,
            turn_number=turn_count
        )

        # Save relationships to database
        relationships_saved = 0
        for rel in relationships:
            try:
                # Get entity IDs from database if not present
                source_id = rel.source_entity_id
                target_id = rel.target_entity_id

                # If entity IDs are missing, look them up by name
                if not source_id or not target_id:
                    with self.db_manager.get_connection() as conn:
                        with conn.cursor() as cur:
                            if not source_id:
                                cur.execute(
                                    "SELECT id FROM entities WHERE entity_name = %s LIMIT 1",
                                    (rel.source_entity_name,)
                                )
                                row = cur.fetchone()
                                source_id = row[0] if row else None

                            if not target_id:
                                cur.execute(
                                    "SELECT id FROM entities WHERE entity_name = %s LIMIT 1",
                                    (rel.target_entity_name,)
                                )
                                row = cur.fetchone()
                                target_id = row[0] if row else None

                # Skip if we couldn't find entity IDs
                if not source_id or not target_id:
                    continue

                # Save relationship (upsert to avoid duplicates)
                success = self._upsert_relationship(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=rel.relationship_type,
                    strength=rel.strength,
                    confidence=rel.confidence,
                    metadata={
                        "provenance": rel.provenance,
                        "properties": rel.properties,
                        "extraction_method": "training_logger",
                        "session_id": session_id,
                        "turn_number": turn_count
                    }
                )

                if success:
                    relationships_saved += 1

            except Exception as e:
                print(f"[TrainingLogger] Failed to save relationship {rel.source_entity_name} -> {rel.target_entity_name}: {e}")
                continue

        return relationships_saved

    def _upsert_relationship(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        strength: float,
        confidence: float,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Insert or update a relationship in the database

        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            strength: Relationship strength (0.0-1.0)
            confidence: Confidence score (0.0-1.0)
            metadata: Additional metadata

        Returns:
            Success status
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Upsert relationship
                    cur.execute("""
                        INSERT INTO entity_relationships (
                            source_entity_id,
                            target_entity_id,
                            relationship_type,
                            strength,
                            confidence,
                            metadata,
                            created_at,
                            updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                        ON CONFLICT (source_entity_id, target_entity_id, relationship_type)
                        DO UPDATE SET
                            strength = GREATEST(entity_relationships.strength, EXCLUDED.strength),
                            confidence = (entity_relationships.confidence + EXCLUDED.confidence) / 2.0,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """, (
                        source_entity_id,
                        target_entity_id,
                        relationship_type,
                        strength,
                        confidence,
                        Json(metadata) if metadata else None
                    ))
                    conn.commit()
                    return True

        except Exception as e:
            print(f"[TrainingLogger] Error upserting relationship: {e}")
            return False

    def _auto_label(
        self,
        agent_name: str,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
        is_error: bool,
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        """
        자동 라벨링 로직

        Returns:
            (outcome, outcome_reason, feedback_score)
            - outcome: 'success', 'failure', 'partial', None (unlabeled)
            - outcome_reason: 라벨링 이유
            - feedback_score: 0.0 ~ 1.0 (품질 점수)
        """
        # 에러 발생 시 무조건 failure
        if is_error:
            return ("failure", "Error occurred during execution", 0.1)

        # Agent별 라벨링 로직
        if agent_name == "router":
            return self._label_router(state, model_output)
        elif agent_name == "parent":
            return self._label_parent(state, model_output)
        elif agent_name == "children":
            return self._label_children(state, model_output)
        elif agent_name == "dialogue":
            return self._label_dialogue(state, model_output)
        else:
            # 알 수 없는 에이전트는 라벨 없이 저장
            return (None, None, None)

    def _label_router(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Router Agent 자동 라벨링 (하이브리드: Rule 40% + LLM 60%)

        하이브리드 평가를 시도하고, LLM이 비활성화된 경우 Rule-based만 사용
        """
        # 하이브리드 평가 시도 (async)
        if self.llm_labeling_enabled:
            try:
                # asyncio.run을 사용하여 async 함수 호출
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 이벤트 루프가 있으면 create_task 사용
                    # 하지만 동기 함수에서 호출되므로 run_until_complete 사용 불가
                    # 대신 동기적으로 Rule-based 사용 (비동기 호출 불가 상황)
                    return self._label_router_rules(state, model_output)
                else:
                    # 새로운 이벤트 루프에서 실행
                    return loop.run_until_complete(
                        self._label_router_with_hybrid(state, model_output)
                    )
            except Exception as e:
                print(f"[TrainingLogger] Hybrid labeling failed, fallback to rule-based: {e}")
                return self._label_router_rules(state, model_output)
        else:
            # LLM 비활성화 시 Rule-based만 사용
            return self._label_router_rules(state, model_output)

    def _label_router_rules(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Router Agent Rule-based 평가 (기술적 완성도만)
        """
        next_node = model_output.get("next_node", "")
        classification = model_output.get("classification", "")
        confidence = model_output.get("confidence", 0.5)

        score = 0.7
        reasons = []

        # 1. 필수 필드 존재 검증
        if not next_node or not classification:
            score -= 0.4
            reasons.append("Missing required fields")
            return ("failure", "; ".join(reasons), max(0.0, score))

        # 2. 라우팅 논리 일관성
        if classification == "off_topic" and "warning" in next_node.lower():
            score += 0.2
            reasons.append("Logical routing: off_topic→warning")
        elif classification == "on_topic" and "parent" in next_node.lower():
            score += 0.2
            reasons.append("Logical routing: on_topic→parent")
        else:
            score -= 0.2
            reasons.append(f"Inconsistent routing: {classification}→{next_node}")

        # 3. Confidence 검증
        if confidence > 0.8:
            score += 0.1
            reasons.append("High confidence")
        elif confidence < 0.3:
            score -= 0.1
            reasons.append("Low confidence")

        score = max(0.0, min(1.0, score))

        # Outcome 결정
        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, "; ".join(reasons), score)

    async def _label_router_with_hybrid(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        하이브리드 Router 평가: Rule 40% + LLM 60%
        """
        # 1. Rule 평가
        rule_outcome, rule_reason, rule_score = self._label_router_rules(
            state, model_output
        )

        # 2. 캐시 확인 (TTL 포함)
        cache_key = self._get_cache_key(state, model_output, "router")
        cached_result = self._get_cached_evaluation(cache_key)

        if cached_result:
            llm_score, llm_reason = cached_result
        else:
            # 3. LLM 평가
            llm_score, llm_reason = await self._evaluate_router_with_llm(
                state, model_output
            )
            # 캐시 저장 (TTL 포함)
            self._set_cached_evaluation(cache_key, llm_score, llm_reason)

        # 4. 하이브리드 점수 (Rule 40% + LLM 60%)
        final_score = 0.4 * rule_score + 0.6 * llm_score

        # 5. Outcome 결정
        if final_score >= 0.8:
            outcome = "success"
        elif final_score >= 0.6:
            outcome = "partial"
        else:
            outcome = "failure"

        # 6. 상세 이유
        combined_reason = (
            f"[Rule({rule_score:.2f}): {rule_reason}] "
            f"[LLM({llm_score:.2f}): {llm_reason}] "
            f"→ Final: {final_score:.2f}"
        )

        # 7. A/B 테스트 결과 저장 (활성화된 경우)
        if self.ab_test_enabled:
            await self._save_ab_test_result(
                state, model_output, "router",
                (rule_outcome, rule_score),
                (outcome, final_score)
            )

        return (outcome, combined_reason, final_score)

    def _label_parent(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Parent Agent 자동 라벨링

        성공 조건:
        - open_narrative: dialogues 생성 여부 및 품질
        - 일반 스테이지: agent_inputs가 비어있지 않음, beats 생성
        - 스테이지 전환 로직이 올바름
        """
        agent_inputs = model_output.get("agent_inputs", {})
        current_stage = state.get("current_stage", "")
        stage_tag = model_output.get("stage_tag", "")

        score = 0.7

        # 1. open_narrative 스테이지 체크 (dialogues 직접 생성)
        # open_narrative에서는 agent_inputs가 null이고 dialogues를 직접 생성함
        if agent_inputs is None or (isinstance(agent_inputs, dict) and not agent_inputs):
            # open_narrative 또는 특수 스테이지 처리
            # state의 children_ctx에 fallback.dialogues가 있는지 확인
            children_ctx = state.get("children_ctx", {})

            # 타입 안전 체크
            if not isinstance(children_ctx, dict):
                return ("failure", "Invalid children_ctx type", 0.2)

            fallback = children_ctx.get("fallback", {})

            # fallback이 dict인지 확인
            if isinstance(fallback, dict):
                dialogues = fallback.get("dialogues", [])
            else:
                dialogues = []

            if dialogues and len(dialogues) > 0:
                # open_narrative 성공: 대사 생성됨
                score = 0.75
                if len(dialogues) >= 3:
                    score += 0.1
                reason = f"Open narrative: generated {len(dialogues)} dialogues"
            else:
                # agent_inputs도 없고 dialogues도 없음 → 진짜 failure
                return ("failure", f"No agent_inputs and no dialogues (ctx_type={type(children_ctx).__name__}, fallback_type={type(fallback).__name__})", 0.2)
        else:
            # 2. 일반 스테이지: agent_inputs 유효성
            if "children" not in agent_inputs:
                return ("failure", "agent_inputs missing 'children' key", 0.2)

            children_ctx = agent_inputs.get("children", {})
            beats = children_ctx.get("beats", [])

            # 3. Beats 품질 체크
            if not beats or len(beats) == 0:
                score -= 0.3
                reason = "No beats generated"
            elif len(beats) >= 3:  # 적절한 beats 수 (3~5개)
                score += 0.15
                reason = f"Good beats count: {len(beats)}"
            else:
                reason = f"Low beats count: {len(beats)}"

        # 4. 스테이지 전환 체크
        next_stage = model_output.get("next_stage")
        if next_stage and next_stage != current_stage:
            score += 0.1  # 스테이지 전환 발생 (긍정적)

        # 5. 점수 기반 outcome
        score = max(0.0, min(1.0, score))
        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

    def _label_children(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Children Agent 자동 라벨링 (하이브리드: Rule 40% + LLM 60%)

        하이브리드 평가를 시도하고, LLM이 비활성화된 경우 Rule-based만 사용
        """
        # 하이브리드 평가 시도 (async)
        if self.llm_labeling_enabled:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 동기적으로 Rule-based 사용 (비동기 호출 불가 상황)
                    return self._label_children_rules(state, model_output)
                else:
                    # 새로운 이벤트 루프에서 실행
                    return loop.run_until_complete(
                        self._label_children_with_hybrid(state, model_output)
                    )
            except Exception as e:
                print(f"[TrainingLogger] Hybrid labeling failed, fallback to rule-based: {e}")
                return self._label_children_rules(state, model_output)
        else:
            # LLM 비활성화 시 Rule-based만 사용
            return self._label_children_rules(state, model_output)

    def _label_children_rules(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Children Agent Rule-based 평가 (기술적 완성도만, Beat 수 제거)
        """
        agent_responses = model_output.get("agent_responses", [])

        score = 0.8  # 기본 점수
        reasons = []

        # 1. 대사 생성 여부
        if not agent_responses or len(agent_responses) == 0:
            return ("failure", "No dialogues generated", 0.1)

        reasons.append(f"Generated {len(agent_responses)} dialogues")

        # 2. 대사 길이 체크 (너무 짧거나 길면 감점)
        avg_length = sum(len(r.get("text", "")) for r in agent_responses) / len(agent_responses)
        if 20 <= avg_length <= 200:
            score += 0.1
            reasons.append("Appropriate dialogue length")
        elif avg_length < 10:
            score -= 0.1
            reasons.append("Dialogues too short")
        elif avg_length > 300:
            score -= 0.1
            reasons.append("Dialogues too long")

        # 3. 필수 필드 존재 (character, text)
        missing_fields = []
        for r in agent_responses:
            if not r.get("character"):
                missing_fields.append("character")
            if not r.get("text"):
                missing_fields.append("text")

        if missing_fields:
            score -= 0.2
            reasons.append(f"Missing fields: {', '.join(set(missing_fields))}")

        score = max(0.0, min(1.0, score))

        # Outcome 결정
        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, "; ".join(reasons), score)

    async def _label_children_with_hybrid(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        하이브리드 Children 평가: Rule 40% + LLM 60%
        """
        # 1. Rule 평가
        rule_outcome, rule_reason, rule_score = self._label_children_rules(
            state, model_output
        )

        # 2. 캐시 확인 (TTL 포함)
        cache_key = self._get_cache_key(state, model_output, "children")
        cached_result = self._get_cached_evaluation(cache_key)

        if cached_result:
            llm_score, llm_reason = cached_result
        else:
            # 3. LLM 평가
            llm_score, llm_reason = await self._evaluate_children_with_llm(
                state, model_output
            )
            # 캐시 저장 (TTL 포함)
            self._set_cached_evaluation(cache_key, llm_score, llm_reason)

        # 4. 하이브리드 점수 (Rule 40% + LLM 60%)
        final_score = 0.4 * rule_score + 0.6 * llm_score

        # 5. Outcome 결정
        if final_score >= 0.8:
            outcome = "success"
        elif final_score >= 0.6:
            outcome = "partial"
        else:
            outcome = "failure"

        # 6. 상세 이유
        combined_reason = (
            f"[Rule({rule_score:.2f}): {rule_reason}] "
            f"[LLM({llm_score:.2f}): {llm_reason}] "
            f"→ Final: {final_score:.2f}"
        )

        # 7. A/B 테스트 결과 저장 (활성화된 경우)
        if self.ab_test_enabled:
            await self._save_ab_test_result(
                state, model_output, "children",
                (rule_outcome, rule_score),
                (outcome, final_score)
            )

        return (outcome, combined_reason, final_score)

    def _label_dialogue(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        """
        Dialogue Agent 자동 라벨링

        현재는 라벨 없이 저장 (향후 validation 로직 추가 시 개선 가능)
        """
        # Dialogue Agent는 검증 로직이 복잡하므로 일단 unlabeled로 저장
        # 향후 user_feedback과 연계하여 라벨링 가능
        return (None, "Dialogue agent - pending validation", None)

    # ========================================================================
    # Helper Functions (맥락 중심 평가)
    # ========================================================================

    def _format_recent_dialogues(self, short_term_memory: List[Dict]) -> str:
        """최근 대화를 읽기 좋은 형식으로 변환 (LLM 프롬프트용)"""
        if not short_term_memory:
            return "(대화 기록 없음)"

        formatted = []
        for i, msg in enumerate(short_term_memory, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{i}. {role}: {content}")

        return "\n".join(formatted)

    def _format_character_relationships(
        self,
        characters_info: Dict,
        affinity: Dict
    ) -> str:
        """캐릭터 관계 정보 포맷팅 (LLM 프롬프트용)"""
        if not characters_info and not affinity:
            return "(관계 정보 없음)"

        formatted = []

        # affinity 기반으로 포맷팅
        for char_name, aff_score in affinity.items():
            if isinstance(aff_score, (int, float)):
                if aff_score >= 700:
                    relationship = "친밀"
                elif aff_score >= 400:
                    relationship = "보통"
                else:
                    relationship = "낯설음"
                formatted.append(f"- {char_name}: 친밀도 {aff_score} ({relationship})")

        return "\n".join(formatted) if formatted else "(친밀도 정보 없음)"

    def _get_cache_key(self, state: Dict, model_output: Dict, eval_type: str) -> str:
        """평가 대상을 hash로 변환 (캐시용)"""
        key_data = {
            "eval_type": eval_type,
            "user_input": state.get("user_input"),
            "classification": model_output.get("classification"),
            "next_node": model_output.get("next_node"),
            "recent_context": str(state.get("short_term_memory", [])[-5:]),
            "agent_responses": str(model_output.get("agent_responses", []))[:200]  # 일부만
        }
        return hashlib.md5(str(key_data).encode()).hexdigest()

    def _get_cached_evaluation(self, cache_key: str) -> Optional[tuple[float, str]]:
        """캐시에서 평가 결과 가져오기 (TTL 체크)"""
        if cache_key not in self.evaluation_cache:
            return None

        cached_data = self.evaluation_cache[cache_key]
        timestamp = cached_data.get("timestamp", 0)

        # TTL 체크
        if time.time() - timestamp > self.cache_ttl:
            # 만료된 캐시 제거
            del self.evaluation_cache[cache_key]
            return None

        score = cached_data.get("score", 0.5)
        reason = cached_data.get("reason", "")
        return (score, f"{reason} (cached)")

    def _set_cached_evaluation(self, cache_key: str, score: float, reason: str):
        """평가 결과를 캐시에 저장 (TTL 포함)"""
        self.evaluation_cache[cache_key] = {
            "score": score,
            "reason": reason,
            "timestamp": time.time()
        }

    async def _save_ab_test_result(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
        agent_name: str,
        rule_result: tuple[str, float],
        hybrid_result: tuple[str, float]
    ):
        """A/B 테스트 결과를 DB에 저장"""
        try:
            conn = self.get_connection()
            if conn is None:
                return

            cursor = conn.cursor()

            # A/B 테스트 결과 테이블이 없으면 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_test_results (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT,
                    turn_number INTEGER,
                    agent_name TEXT,
                    rule_outcome TEXT,
                    rule_score FLOAT,
                    hybrid_outcome TEXT,
                    hybrid_score FLOAT,
                    score_difference FLOAT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # 데이터 삽입
            cursor.execute("""
                INSERT INTO ab_test_results (
                    session_id, turn_number, agent_name,
                    rule_outcome, rule_score,
                    hybrid_outcome, hybrid_score,
                    score_difference
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                state.get("session_id", ""),
                state.get("turn_count", 0),
                agent_name,
                rule_result[0],
                rule_result[1],
                hybrid_result[0],
                hybrid_result[1],
                abs(hybrid_result[1] - rule_result[1])
            ))

            conn.commit()
            cursor.close()

        except Exception as e:
            print(f"[TrainingLogger] Failed to save A/B test result: {e}")
            if conn and not conn.closed:
                conn.rollback()

    # ========================================================================
    # LLM-based Evaluation Functions
    # ========================================================================

    async def _evaluate_router_with_llm(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any]
    ) -> tuple[float, str]:
        """
        LLM으로 Router 맥락 평가 (최근 5개 대화 기반)

        Returns:
            (score, reason)
        """
        user_input = state.get("user_input", "")
        classification = model_output.get("classification", "")
        next_node = model_output.get("next_node", "")

        # 최근 5개 대화 (단기 기억)
        short_term_memory = state.get("short_term_memory", [])[-5:]
        recent_context = self._format_recent_dialogues(short_term_memory)

        # 현재 스테이지/이벤트
        current_stage = state.get("current_stage", "unknown")
        scenario_id = state.get("scenario_id", "")

        # 세계관 정보 (간단한 요약)
        world_context = "귀멸의 칼날 세계관: 다이쇼 시대, 귀살대, 호흡법 수련"

        prompt = f"""당신은 대화형 게임 품질 평가자입니다.

**세계관**: {world_context}
**시나리오**: {scenario_id}
**현재 스테이지**: {current_stage}

**최근 5개 대화 맥락**:
{recent_context}

**현재 사용자 입력**: "{user_input}"
**Router 분류**: {classification}
**라우팅 결정**: {next_node}

**평가 기준** (중요도 순):
1. **맥락 연결성** (40점): 최근 5개 대화 흐름에서 자연스러운 질문인가?
   - 갑작스러운 주제 전환은 off_topic
   - 이전 대화와 연관된 질문은 on_topic

2. **스토리 일관성** (30점): 현재 스테이지/이벤트와 관련있는 입력인가?
   - 스토리 진행과 무관한 질문은 off_topic
   - 게임 외부 정보 요청은 off_topic

3. **세계관 준수** (20점): 귀멸의 칼날 세계관 내의 질문인가?
   - 캐릭터 외모, 키, 나이 등은 off_topic
   - 호흡법, 훈련, 미션은 on_topic

4. **라우팅 적절성** (10점): 분류에 맞게 라우팅되었는가?

**점수 산정**:
- 0.9~1.0: 완벽한 맥락 이해, 정확한 분류
- 0.7~0.8: 대체로 적절, 작은 문제
- 0.5~0.6: 애매함, 판단 어려움
- 0.3~0.4: 부적절한 분류
- 0.0~0.2: 완전히 잘못됨

**출력 형식** (JSON):
{{
  "score": 0.0-1.0,
  "reason": "평가 이유 (맥락/스토리/세계관 관점에서)"
}}

JSON만 출력하세요."""

        try:
            response = await openai.ChatCompletion.acreate(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are an expert game dialogue quality evaluator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            score = float(result.get("score", 0.5))
            reason = result.get("reason", "No reason provided")

            return (score, reason)

        except Exception as e:
            print(f"[TrainingLogger] LLM evaluation error (router): {e}")
            return (0.5, f"LLM evaluation failed: {str(e)}")

    async def _evaluate_parent_with_llm(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any]
    ) -> tuple[float, str]:
        """
        LLM으로 Parent Agent 품질 평가 (Beat 생성 + 스토리 진행)

        Returns:
            (score, reason)
        """
        agent_inputs = model_output.get("agent_inputs", {})
        beats = agent_inputs.get("children", {}).get("beats", []) if agent_inputs else []
        user_input = state.get("user_input", "")
        current_stage = state.get("current_stage", "unknown")
        stage_transition = model_output.get("stage_transition")

        # 최근 5개 대화
        short_term_memory = state.get("short_term_memory", [])[-5:]
        recent_context = self._format_recent_dialogues(short_term_memory)

        # Beats 텍스트
        beats_text = "\n".join([
            f"- {b.get('character', 'Unknown')}: {b.get('action', '')} (감정: {b.get('emotion', 'neutral')})"
            for b in beats
        ]) if beats else "(Beats 없음)"

        prompt = f"""당신은 스토리 진행 품질 평가자입니다.

**현재 스테이지**: {current_stage}
**최근 5개 대화 맥락**:
{recent_context}

**사용자 입력**: "{user_input}"

**Parent Agent의 역할**:
1. 사용자 입력 분석
2. 스토리 진행 계획 (Beats 생성)
3. 스테이지 전환 판단

**생성된 Beats**:
{beats_text}
(총 {len(beats)}개)

**스테이지 전환**: {stage_transition if stage_transition else "없음"}

**평가 기준**:
1. **Beat 품질** (40점):
   - Beat가 스토리 진행에 적합한가?
   - 캐릭터 action/emotion이 명확한가?
   - 사용자 입력에 맞는 반응인가?

2. **스토리 진행** (30점):
   - 현재 스테이지 목표와 일치하는가?
   - 자연스러운 스토리 흐름인가?

3. **Beat 수 적절성** (20점):
   - 3~5개가 적절 (너무 많거나 적으면 감점)

4. **스테이지 전환 판단** (10점):
   - 전환 시점이 적절한가?

**점수 산정**:
- 0.9~1.0: 완벽한 스토리 진행
- 0.7~0.8: 대체로 좋음
- 0.5~0.6: 보통
- 0.3~0.4: 부적절한 Beat 생성
- 0.0~0.2: 스토리 진행 실패

**출력 형식** (JSON):
{{
  "score": 0.0-1.0,
  "reason": "평가 이유 (Beat/스토리 관점)"
}}

JSON만 출력하세요."""

        try:
            response = await openai.ChatCompletion.acreate(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a story progression quality expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            score = float(result.get("score", 0.5))
            reason = result.get("reason", "No reason provided")

            return (score, reason)

        except Exception as e:
            print(f"[TrainingLogger] LLM evaluation error (parent): {e}")
            return (0.5, f"LLM evaluation failed: {str(e)}")

    async def _evaluate_children_with_llm(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any]
    ) -> tuple[float, str]:
        """
        LLM으로 Children 대사 품질 평가 (세계관/톤/관계성)

        Returns:
            (score, reason)
        """
        agent_responses = model_output.get("agent_responses", [])
        beats = state.get("agent_inputs", {}).get("children", {}).get("beats", [])
        user_input = state.get("user_input", "")

        # 최근 5개 대화
        short_term_memory = state.get("short_term_memory", [])[-5:]
        recent_context = self._format_recent_dialogues(short_term_memory)

        # 캐릭터 정보 (관계성, 친밀도)
        characters_info = state.get("characters", {})
        affinity = state.get("affinity", {})

        # 대사 텍스트 추출
        dialogues_text = "\n".join([
            f"- {r.get('character', 'Unknown')}: \"{r.get('text', '')}\""
            for r in agent_responses
        ])

        # Beats 텍스트
        beats_text = "\n".join([
            f"- {b.get('character', 'Unknown')}: {b.get('action', '')} (감정: {b.get('emotion', 'neutral')})"
            for b in beats
        ])

        # 캐릭터 관계 정보
        characters_context = self._format_character_relationships(
            characters_info, affinity
        )

        prompt = f"""당신은 귀멸의 칼날 대화 품질 평가자입니다.

**세계관**: 다이쇼 시대, 귀살대, 호흡법 중심 세계
**캐릭터 특징**:
- 렌고쿠: 열정적, 크고 당당한 말투, "우마이!"
- 탄지로: 친절, 진지, 공손한 말투
- 이노스케: 거칠고 시끄러운 말투, 이름 자주 틀림

**캐릭터 관계 & 친밀도**:
{characters_context}

**최근 5개 대화 맥락**:
{recent_context}

**현재 사용자 입력**: "{user_input}"

**의도된 Beats**:
{beats_text}

**생성된 대사**:
{dialogues_text}

**평가 기준** (중요도 순):
1. **세계관 & 캐릭터 톤 일치** (35점):
   - 캐릭터의 고유한 말투, 성격이 잘 표현되었는가?
   - 귀멸의 칼날 세계관에 어울리는 대사인가?

2. **관계성 반영** (25점):
   - 현재 친밀도/관계에 맞는 대사 톤인가?
   - 캐릭터 간 관계가 대사에 드러나는가?

3. **맥락 연결성** (20점):
   - 최근 5개 대화 흐름과 자연스럽게 이어지는가?
   - 사용자 입력에 적절히 반응하는가?

4. **Beat 의도 표현** (20점):
   - Beats의 action/emotion이 대사에 잘 드러나는가?
   - 예: "격려" beat → 실제로 격려하는 내용인가?

**점수 산정**:
- 0.9~1.0: 완벽한 캐릭터 연기, 세계관 준수, 자연스러운 대화
- 0.7~0.8: 대체로 좋음, 사소한 톤 문제
- 0.5~0.6: 보통, 일부 beat 의도 누락
- 0.3~0.4: 톤 불일치 또는 맥락 이탈
- 0.0~0.2: 캐릭터 붕괴, 세계관 위배

**출력 형식** (JSON):
{{
  "score": 0.0-1.0,
  "reason": "평가 이유 (톤/관계/맥락 관점)"
}}

JSON만 출력하세요."""

        try:
            response = await openai.ChatCompletion.acreate(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a Demon Slayer dialogue quality expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            score = float(result.get("score", 0.5))
            reason = result.get("reason", "No reason provided")

            return (score, reason)

        except Exception as e:
            print(f"[TrainingLogger] LLM evaluation error (children): {e}")
            return (0.5, f"LLM evaluation failed: {str(e)}")

    def close(self):
        """연결 종료"""
        if self.connection and not self.connection.closed:
            self.connection.close()

    def __del__(self):
        """소멸자"""
        self.close()


# Singleton 인스턴스
_training_logger: Optional[TrainingLogger] = None


def get_training_logger() -> TrainingLogger:
    """TrainingLogger 싱글톤 인스턴스 가져오기"""
    global _training_logger
    if _training_logger is None:
        _training_logger = TrainingLogger()
    return _training_logger


def _log_agent_sync(
    agent_name: str,
    state: Dict[str, Any],
    model_output: Dict[str, Any],
    latency_ms: int,
    token_count: Optional[int] = None,
    llm_model: Optional[str] = None,
    is_error: bool = False,
    error_message: Optional[str] = None,
) -> Optional[int]:
    """
    내부 함수: 실제 로깅 작업 수행 (동기)
    """
    try:
        logger = get_training_logger()
        return logger.log_agent_execution(
            agent_name=agent_name,
            state=state,
            model_output=model_output,
            latency_ms=latency_ms,
            token_count=token_count,
            llm_model=llm_model,
            is_error=is_error,
            error_message=error_message,
        )
    except Exception as e:
        print(f"[TrainingLogger] Logging failed for {agent_name}: {e}")
        return None


def log_agent(
    agent_name: str,
    state: Dict[str, Any],
    model_output: Dict[str, Any],
    start_time: float,
    token_count: Optional[int] = None,
    llm_model: Optional[str] = None,
    is_error: bool = False,
    error_message: Optional[str] = None,
) -> None:
    """
    에이전트 실행 로그 기록 (백그라운드 실행)

    ⚡ 성능 최적화: 로깅을 백그라운드 스레드에서 실행하여 응답 지연 방지

    이 함수는 호출 즉시 반환되며, 실제 로깅은 백그라운드에서 비동기적으로 수행됩니다.
    따라서 에이전트 실행 시간에 로깅 시간이 포함되지 않습니다.

    Args:
        agent_name: 에이전트 이름
        state: GraphState
        model_output: 에이전트 출력
        start_time: time.perf_counter() 시작 시간
        token_count: 사용된 토큰 수
        llm_model: LLM 모델명
        is_error: 에러 발생 여부
        error_message: 에러 메시지

    Returns:
        None (백그라운드 실행이므로 결과 반환 안함)

    Example:
        ```python
        start = time.perf_counter()
        result = run_router_agent(state, user_input)

        # 백그라운드에서 로깅 (즉시 반환)
        log_agent(
            agent_name="router",
            state=state,
            model_output=result,
            start_time=start,
            token_count=result.get("token_count"),
            llm_model="gpt-4o-mini"
        )
        # 여기서는 이미 로깅이 완료되지 않았을 수 있지만 괜찮습니다
        ```
    """
    from concurrent.futures import ThreadPoolExecutor
    import threading

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # 백그라운드 스레드 풀 (싱글톤 패턴)
    global _logging_executor
    if '_logging_executor' not in globals():
        _logging_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="training_logger"
        )

    # 백그라운드에서 로깅 실행 (fire-and-forget)
    _logging_executor.submit(
        _log_agent_sync,
        agent_name,
        state.copy() if isinstance(state, dict) else state,  # state 복사로 thread safety 확보
        model_output.copy() if isinstance(model_output, dict) else model_output,
        latency_ms,
        token_count,
        llm_model,
        is_error,
        error_message
    )


async def log_agent_async(
    agent_name: str,
    state: Dict[str, Any],
    model_output: Dict[str, Any],
    start_time: float,
    token_count: Optional[int] = None,
    llm_model: Optional[str] = None,
    is_error: bool = False,
    error_message: Optional[str] = None,
) -> None:
    """
    에이전트 실행 로그 기록 (비동기, 백그라운드 실행)

    응답 지연을 방지하기 위해 백그라운드 스레드에서 로깅을 수행합니다.
    이 함수는 결과를 기다리지 않고 즉시 반환됩니다.

    Args:
        agent_name: 에이전트 이름
        state: GraphState
        model_output: 에이전트 출력
        start_time: time.perf_counter() 시작 시간
        token_count: 사용된 토큰 수
        llm_model: LLM 모델명
        is_error: 에러 발생 여부
        error_message: 에러 메시지

    Example:
        ```python
        start = time.perf_counter()
        result = run_router_agent(state, user_input)

        # 백그라운드에서 로깅 (응답에 영향 없음)
        asyncio.create_task(log_agent_async(
            agent_name="router",
            state=state,
            model_output=result,
            start_time=start
        ))
        ```
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # ThreadPoolExecutor를 사용하여 동기 함수를 백그라운드에서 실행
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    try:
        # 동기 log_agent 함수를 별도 스레드에서 실행
        await loop.run_in_executor(
            executor,
            log_agent,
            agent_name,
            state,
            model_output,
            start_time,
            token_count,
            llm_model,
            is_error,
            error_message
        )
    except Exception as e:
        # 로깅 실패해도 에러를 발생시키지 않음 (백그라운드 작업)
        print(f"[TrainingLogger] Background logging failed for {agent_name}: {e}")
    finally:
        executor.shutdown(wait=False)
