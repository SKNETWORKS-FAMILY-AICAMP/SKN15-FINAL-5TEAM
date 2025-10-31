"""
Training Logger for AI Model Fine-tuning

Phase 4: SLLM LoRA 훈련을 위한 로그 수집 시스템
- 최소 전처리로 의미 있는 로그 생성
- 자동 라벨링 (success/failure/partial)
- 비동기 로깅으로 성능 영향 최소화
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import psycopg2
from psycopg2.extras import Json


class TrainingLogger:
    """에이전트 실행 로그를 LogDB에 수집하는 클래스"""

    def __init__(self):
        """LogDB 연결 초기화"""
        self.logdb_url = os.getenv(
            "LOGDB_URL",
            os.getenv("DATABASE_URL"),  # Fallback to DATABASE_URL
        )
        self.connection = None
        self.enabled = os.getenv("TRAINING_LOGGER_ENABLED", "true").lower() == "true"

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

            # 대화 이력 (최근 5개만)
            "history": (state.get("history", []))[-5:] if state.get("history") else [],

            # 현재 참여 캐릭터
            "participants": state.get("participants", []),

            # 분위기 (선택지, 미션 등)
            "atmosphere": state.get("atmosphere"),

            # 친밀도 (있는 경우)
            "affinity_scores": state.get("affinity_scores", {}),

            # 이전 대사 (Children/Dialogue 에이전트용)
            "output": state.get("output", {}).get("dialogues", []),

            # Parent Agent용: children_ctx (open_narrative 등에서 생성된 대사)
            "children_ctx": state.get("children_ctx"),
        }

        # None 값 제거 (JSON 크기 최소화)
        return {k: v for k, v in context.items() if v is not None}

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
        elif agent_name == "guardrail":
            return self._label_guardrail(state, model_output)

        return (None, None, None)

    def _label_router(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        classification = model_output.get("classification") or model_output.get("classification")
        if classification == "off_topic":
            return ("partial", "User input handled by fallback", 0.5)
        return ("success", "User routed to parent agent", 0.9)

    def _label_parent(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        next_stage = model_output.get("next_stage") or state.get("next_stage")
        if next_stage:
            return ("success", f"Transition to stage {next_stage}", 0.9)
        return ("partial", "Stage pending or unchanged", 0.6)

    def _label_children(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        responses = model_output.get("agent_responses", [])
        if responses:
            return ("success", f"{len(responses)} dialogues generated", 0.95)
        return ("failure", "No dialogue generated", 0.2)

    def _label_dialogue(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        validated_count = model_output.get("validated_count", 0)
        validation_results = model_output.get("validation_results", [])
        if validated_count and all(result.get("passed", False) for result in validation_results):
            return ("success", "All dialogues passed validation", 0.95)
        elif validated_count:
            return ("partial", "Dialogues adjusted after validation", 0.7)
        return ("failure", "No dialogues validated", 0.3)

    def _label_guardrail(
        self,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[str], Optional[float]]:
        status = model_output.get("status")
        if status == "passed":
            return ("success", "Input passed guardrail", 0.9)
        elif status == "warning":
            return ("partial", "User warned for prohibited content", 0.5)
        elif status == "blocked":
            return ("failure", "User blocked by guardrail", 0.2)
        return (None, None, None)

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


def log_agent(
    agent_name: str,
    state: Dict[str, Any],
    model_output: Dict[str, Any],
    start_time: float,
    token_count: Optional[int] = None,
    llm_model: Optional[str] = None,
    is_error: bool = False,
    error_message: Optional[str] = None,
) -> Optional[int]:
    """
    에이전트 실행 로그 기록 (편의 함수)

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
        int: 로그 ID (실패 시 None)

    Example:
        ```python
        start = time.perf_counter()
        result = run_router_agent(state, user_input)
        latency_ms = int((time.perf_counter() - start) * 1000)

        log_agent(
            agent_name="router",
            state=state,
            model_output=result,
            start_time=start,
            token_count=result.get("token_count"),
            llm_model="gpt-4o-mini"
        )
        ```
    """
    latency_ms = int((time.perf_counter() - start_time) * 1000)

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
