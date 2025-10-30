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
        else:
            # 알 수 없는 에이전트는 라벨 없이 저장
            return (None, None, None)

    def _label_router(
        self, state: Dict[str, Any], model_output: Dict[str, Any]
    ) -> tuple[str, str, float]:
        """
        Router Agent 자동 라벨링

        성공 조건:
        - on_topic 판단이 정확함
        - 다음 노드(next_node) 선택이 적절함
        - 빠른 응답 시간 (< 2초)
        """
        next_node = model_output.get("next_node", "")
        classification = model_output.get("classification", "")

        # 기본 점수
        score = 0.7

        # 1. Topic classification 정확도 (추론)
        # off_topic이면서 warning_handler로 보낸 경우 → good
        if classification == "off_topic" and "warning" in next_node.lower():
            score += 0.15
            reason = "Correctly identified off-topic and routed to warning"
        # on_topic이면서 parent_agent로 보낸 경우 → good
        elif classification == "on_topic" and "parent" in next_node.lower():
            score += 0.15
            reason = "Correctly identified on-topic and routed to parent"
        # 분류와 라우팅이 불일치 → bad
        else:
            score -= 0.3
            reason = f"Mismatch: classification={classification}, next_node={next_node}"

        # 2. Confidence 점수가 있으면 반영
        confidence = model_output.get("confidence", 0.5)
        if confidence > 0.8:
            score += 0.1
        elif confidence < 0.3:
            score -= 0.1

        # 3. 점수 기반 outcome 결정
        score = max(0.0, min(1.0, score))  # 0.0 ~ 1.0 범위로 클램핑
        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

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
        Children Agent 자동 라벨링

        성공 조건:
        - agent_responses에 대사가 생성됨
        - 대사 수가 beats 수와 유사함
        - 대사 길이가 적절함 (너무 길거나 짧지 않음)
        """
        agent_responses = model_output.get("agent_responses", [])
        agent_inputs = state.get("agent_inputs", {}).get("children", {})
        beats = agent_inputs.get("beats", [])

        score = 0.7

        # 1. 대사 생성 여부
        if not agent_responses or len(agent_responses) == 0:
            return ("failure", "No dialogues generated", 0.1)

        # 2. 대사 수와 beats 수 비교
        if len(agent_responses) == len(beats):
            score += 0.15
            reason = f"Dialogue count matches beats count: {len(agent_responses)}"
        elif abs(len(agent_responses) - len(beats)) <= 1:
            score += 0.05
            reason = f"Dialogue count close to beats: {len(agent_responses)} vs {len(beats)}"
        else:
            score -= 0.1
            reason = f"Dialogue count mismatch: {len(agent_responses)} vs {len(beats)} beats"

        # 3. 대사 길이 체크
        avg_length = sum(len(r.get("text", "")) for r in agent_responses) / len(
            agent_responses
        )
        if 20 <= avg_length <= 200:  # 적절한 대사 길이
            score += 0.1
        elif avg_length < 10 or avg_length > 300:  # 너무 짧거나 김
            score -= 0.1

        # 4. 점수 기반 outcome
        score = max(0.0, min(1.0, score))
        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

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
