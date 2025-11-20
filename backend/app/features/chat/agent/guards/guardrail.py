"""
Guardrail Agent
가드레일 검증 에이전트
"""
from typing import Dict, Any, List
from ..graph_state import GraphState
from app.core.logging import get_parent_logger as get_service_logger

logger = get_service_logger("GuardrailAgent")


class GuardrailAgent:
    """Guardrail Agent - 입출력 안전성 검증"""

    def __init__(self):
        # 금지 키워드 (폭력, 혐오, 차별, 성적인 표현)
        self.forbidden_keywords = [
            "자살", "섹스", "자지", "보지"
        ]

        # 메타 발언 키워드 (게임 시스템 관련)
        self.meta_keywords = [
            "게임", "캐릭터", "NPC", "스토리", "시나리오", "대본",
            "버그", "오류", "다시", "리셋", "재시작", "세이브", "로드", "친밀도"
        ]

    def check_input(self, state: GraphState) -> GraphState:
        """
        입력 검증 (Hard Block만 처리)

        - 금지된 주제 (폭력, 혐오, 차별)
        - 메타 발언 (게임, NPC, 버그 등)
        - 세계관 위반은 Router Agent에서 처리
        """
        logger.info("check_input", "Checking input safety")

        user_input = state.get("user_input", "")
        warnings = []
        violation_type = None

        # 1. 금지 키워드 검사 (폭력, 혐오, 차별)
        for keyword in self.forbidden_keywords:
            if keyword in user_input:
                warnings.append(f"Forbidden keyword detected: {keyword}")
                violation_type = "forbidden"
                logger.warning("check_input", f"Forbidden keyword detected: '{keyword}'")
                break

        # 2. 메타 발언 검사 (게임 시스템 관련)
        if not violation_type:
            for keyword in self.meta_keywords:
                if keyword in user_input:
                    warnings.append(f"Meta talk detected: {keyword}")
                    violation_type = "meta_talk"
                    logger.warning("check_input", f"Meta talk detected: '{keyword}'")
                    break

        state["is_safe"] = len(warnings) == 0
        state["guardrail_warnings"] = warnings
        state["violation_type"] = violation_type

        if not state["is_safe"]:
            logger.warning("check_input", f"Unsafe input detected: {violation_type}", warnings=warnings)
        else:
            logger.debug("check_input", "Input passed guardrail checks")

        return state

    def check_output(self, state: GraphState) -> GraphState:
        """출력 검증"""
        logger.info("check_output", "Checking output safety")

        ai_response = state.get("ai_response") or ""
        warnings = []

        # ✅ None 체크 추가
        if not ai_response:
            logger.debug("check_output", "No ai_response to check, treating as safe")
            state["is_safe"] = True
            return state

        # 간단한 키워드 검사
        for keyword in self.forbidden_keywords:
            if keyword in ai_response:
                warnings.append(f"Forbidden keyword in output: {keyword}")
        
        state["is_safe"] = len(warnings) == 0
        
        if warnings:
            state["guardrail_warnings"].extend(warnings)
            logger.warning("check_output", "Unsafe output detected", warnings=warnings)
        
        return state
