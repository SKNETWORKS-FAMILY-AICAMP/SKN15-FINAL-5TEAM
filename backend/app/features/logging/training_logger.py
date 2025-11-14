"""
TrainingLogger - Auto-labeling System for AI Training Logs

에이전트 실행 로그를 수집하고 자동으로 success/failure/partial 라벨을 부여합니다.
SLLM LoRA 파인튜닝 데이터셋 생성에 사용됩니다.

참고 문서: taemin_record/20_jwt_and_autolabeling_deep_dive.md
"""
import time
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import LoggingRepository
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("TrainingLogger")


class TrainingLogger:
    """
    AI 훈련 로그 자동 수집 및 라벨링 시스템

    책임:
    - 에이전트 실행 로그 저장
    - Auto-labeling (success/failure/partial)
    - 품질 점수 (feedback_score) 자동 계산
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = LoggingRepository(db)

    async def log_agent_execution(
        self,
        session_id: UUID,
        turn_count: int,
        agent_name: str,
        user_input: Optional[str],
        context: Dict[str, Any],
        model_output: Dict[str, Any],
        latency_ms: Optional[int] = None,
        llm_model: Optional[str] = None,
        token_count: Optional[int] = None,
        scenario_id: Optional[str] = None,
        current_stage: Optional[str] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
    ) -> int:
        """
        에이전트 실행 로그 저장 및 자동 라벨링

        Args:
            session_id: 세션 ID
            turn_count: 턴 번호
            agent_name: 에이전트 이름 (router, parent, children, dialogue)
            user_input: 사용자 입력
            context: 입력 컨텍스트 (scenario, stage, history 등)
            model_output: 모델 출력 (classification, next_node, dialogues 등)
            latency_ms: 레이턴시 (밀리초)
            llm_model: LLM 모델명
            token_count: 토큰 수
            scenario_id: 시나리오 ID
            current_stage: 현재 스테이지
            is_error: 에러 발생 여부
            error_message: 에러 메시지

        Returns:
            생성된 로그 ID
        """
        logger.info(
            "log_agent_execution",
            f"Logging {agent_name} execution",
            session_id=session_id,
            turn=turn_count,
            is_error=is_error,
        )

        # 🔥 Auto-labeling: 자동으로 outcome, reason, score 계산
        outcome, outcome_reason, feedback_score = self._auto_label(
            agent_name=agent_name,
            context=context,
            model_output=model_output,
            is_error=is_error,
        )

        try:
            training_log = await self.repository.create_training_log(
                session_id=session_id,
                turn_count=turn_count,
                scenario_id=scenario_id,
                current_stage=current_stage,
                agent_name=agent_name,
                user_input=user_input,
                context=context,
                model_output=model_output,
                latency_ms=latency_ms,
                token_count=token_count,
                llm_model=llm_model,
                outcome=outcome,
                outcome_reason=outcome_reason,
                feedback_score=feedback_score,
                is_error=is_error,
                error_message=error_message,
            )

            logger.info(
                "log_agent_execution",
                f"Training log created: {training_log.id}",
                outcome=outcome,
                score=feedback_score,
            )

            return training_log.id

        except Exception as e:
            logger.error(
                "log_agent_execution",
                f"Failed to create training log: {e}",
                exc_info=True,
            )
            return -1

    def _auto_label(
        self,
        agent_name: str,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
        is_error: bool,
    ) -> Tuple[str, str, float]:
        """
        자동 라벨링 분기

        Args:
            agent_name: 에이전트 이름
            context: 입력 컨텍스트
            model_output: 모델 출력
            is_error: 에러 여부

        Returns:
            (outcome, outcome_reason, feedback_score)
        """
        # 에러 발생 시 즉시 failure 반환
        if is_error:
            return ("failure", "Error occurred during execution", 0.1)

        # 에이전트별 라벨링 로직
        if agent_name == "router" or agent_name == "router_agent":
            return self._label_router(context, model_output)
        elif agent_name == "parent" or agent_name == "parent_agent":
            return self._label_parent(context, model_output)
        elif agent_name == "children" or agent_name == "children_agent":
            return self._label_children(context, model_output)
        elif agent_name == "dialogue" or agent_name == "dialogue_agent":
            return self._label_dialogue(context, model_output)
        else:
            # Unknown agent: 기본 라벨
            return ("partial", f"Unknown agent: {agent_name}", 0.5)

    def _label_router(
        self,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """
        Router Agent 자동 라벨링

        성공 조건:
        - 토픽 분류가 정확함 (on_topic → parent, off_topic → warning)
        - Confidence 점수가 높음 (> 0.8)

        실패 조건:
        - 분류와 라우팅이 불일치
        - Confidence 점수가 낮음 (< 0.3)
        """
        next_node = model_output.get("next_node", "")
        classification = model_output.get("classification", "")
        confidence = model_output.get("confidence", 0.5)

        score = 0.7  # 기본 점수

        # 1. 토픽 분류와 라우팅 일치 여부 확인
        if classification == "off_topic" and ("warning" in next_node.lower() or "fallback" in next_node.lower()):
            score += 0.15
            reason = "Correctly identified off-topic and routed to warning/fallback"

        elif classification == "on_topic" and "parent" in next_node.lower():
            score += 0.15
            reason = "Correctly identified on-topic and routed to parent"

        else:
            # 분류와 라우팅 불일치 → 심각한 오류
            score -= 0.3
            reason = f"Mismatch: classification={classification}, next_node={next_node}"

        # 2. Confidence 점수 반영
        if confidence > 0.8:
            score += 0.1
            reason += f" (high confidence: {confidence:.2f})"
        elif confidence < 0.3:
            score -= 0.1
            reason += f" (low confidence: {confidence:.2f})"

        # 3. 최종 점수로 outcome 결정
        score = max(0.0, min(1.0, score))  # 0.0 ~ 1.0 범위로 클램핑

        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

    def _label_parent(
        self,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """
        Parent Agent 자동 라벨링

        성공 조건:
        - beats가 정상적으로 생성됨
        - stage_complete가 적절하게 설정됨
        - next_stage가 논리적으로 타당함

        실패 조건:
        - beats가 비어있음
        - next_stage가 없는데 stage_complete=True
        """
        beats = model_output.get("beats", [])
        stage_complete = model_output.get("stage_complete", False)
        next_stage = model_output.get("next_stage")

        score = 0.7  # 기본 점수

        # 1. beats 생성 여부
        if beats and len(beats) > 0:
            score += 0.15
            reason = f"Successfully generated {len(beats)} beats"
        else:
            score -= 0.3
            reason = "No beats generated"

        # 2. stage_complete와 next_stage 일관성
        if stage_complete and next_stage:
            score += 0.1
            reason += " | Stage completed with next_stage defined"
        elif not stage_complete and not next_stage:
            score += 0.05
            reason += " | Stage ongoing (no next_stage)"
        else:
            score -= 0.1
            reason += f" | Inconsistent: stage_complete={stage_complete}, next_stage={next_stage}"

        # 3. 최종 점수로 outcome 결정
        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

    def _label_children(
        self,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """
        Children Agent 자동 라벨링

        성공 조건:
        - dialogues가 beats 수와 일치하거나 적절함
        - dialogues가 비어있지 않음

        실패 조건:
        - dialogues가 비어있음
        - dialogues 수가 beats와 크게 차이남
        """
        dialogues = model_output.get("dialogues", [])
        beats = context.get("beats", [])

        score = 0.7  # 기본 점수

        # 1. dialogues 생성 여부
        if dialogues and len(dialogues) > 0:
            score += 0.15
            reason = f"Generated {len(dialogues)} dialogues"
        else:
            score -= 0.3
            reason = "No dialogues generated"
            return ("failure", reason, 0.2)

        # 2. dialogues와 beats 수 일치 여부
        expected_beats = len(beats)
        actual_dialogues = len(dialogues)

        if expected_beats > 0:
            if actual_dialogues == expected_beats:
                score += 0.15
                reason += f" | Perfect match with {expected_beats} beats"
            elif abs(actual_dialogues - expected_beats) <= 2:
                score += 0.05
                reason += f" | Close to expected ({expected_beats} beats)"
            else:
                score -= 0.1
                reason += f" | Mismatch: expected ~{expected_beats}, got {actual_dialogues}"

        # 3. 최종 점수로 outcome 결정
        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

    def _label_dialogue(
        self,
        context: Dict[str, Any],
        model_output: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """
        Dialogue Agent 자동 라벨링

        성공 조건:
        - validated_dialogues가 원본과 크게 다르지 않음
        - 검증 통과

        실패 조건:
        - 대부분의 대사가 삭제됨
        - 검증 실패
        """
        validated_dialogues = model_output.get("validated_dialogues", [])
        original_dialogues = context.get("dialogues", [])
        validation_passed = model_output.get("validation_passed", True)

        score = 0.7  # 기본 점수

        # 1. 검증 통과 여부
        if validation_passed:
            score += 0.15
            reason = "Validation passed"
        else:
            score -= 0.2
            reason = "Validation failed"

        # 2. 대사 유지율
        if original_dialogues and validated_dialogues:
            retention_rate = len(validated_dialogues) / len(original_dialogues)
            if retention_rate >= 0.8:
                score += 0.15
                reason += f" | High retention: {retention_rate:.0%}"
            elif retention_rate >= 0.5:
                score += 0.05
                reason += f" | Medium retention: {retention_rate:.0%}"
            else:
                score -= 0.1
                reason += f" | Low retention: {retention_rate:.0%}"

        # 3. 최종 점수로 outcome 결정
        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            outcome = "success"
        elif score >= 0.5:
            outcome = "partial"
        else:
            outcome = "failure"

        return (outcome, reason, score)

    async def get_training_statistics(
        self,
        agent_name: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        훈련 로그 통계 조회

        Args:
            agent_name: 특정 에이전트 필터 (None이면 전체)
            hours: 시간 범위

        Returns:
            통계 딕셔너리
        """
        logs = await self.repository.get_training_logs(
            agent_name=agent_name,
            hours=hours,
            limit=10000,
        )

        if not logs:
            return {
                "total_logs": 0,
                "by_outcome": {},
                "avg_feedback_score": 0.0,
                "avg_latency_ms": 0.0,
            }

        # 통계 계산
        total = len(logs)
        by_outcome = {}
        total_score = 0.0
        total_latency = 0

        for log in logs:
            # outcome별 카운트
            outcome = log.outcome or "unknown"
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

            # 점수 및 레이턴시 합산
            total_score += log.feedback_score or 0.0
            total_latency += log.latency_ms or 0

        return {
            "total_logs": total,
            "by_outcome": by_outcome,
            "success_rate": by_outcome.get("success", 0) / total if total > 0 else 0,
            "avg_feedback_score": total_score / total if total > 0 else 0,
            "avg_latency_ms": total_latency / total if total > 0 else 0,
        }
