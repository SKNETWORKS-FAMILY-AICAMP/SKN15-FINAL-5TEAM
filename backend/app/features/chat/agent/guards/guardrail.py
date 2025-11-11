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
        # 금지 키워드 (예시)
        self.forbidden_keywords = [
            "폭력", "혐오", "차별"
        ]

    def check_input(self, state: GraphState) -> GraphState:
        """입력 검증"""
        logger.info("check_input", "Checking input safety")
        
        user_input = state.get("user_input", "")
        warnings = []
        
        # 간단한 키워드 검사
        for keyword in self.forbidden_keywords:
            if keyword in user_input:
                warnings.append(f"Forbidden keyword detected: {keyword}")
        
        state["is_safe"] = len(warnings) == 0
        state["guardrail_warnings"] = warnings
        
        if not state["is_safe"]:
            logger.warning("check_input", "Unsafe input detected", warnings=warnings)
        
        return state

    def check_output(self, state: GraphState) -> GraphState:
        """출력 검증"""
        logger.info("check_output", "Checking output safety")
        
        ai_response = state.get("ai_response", "")
        warnings = []
        
        # 간단한 키워드 검사
        for keyword in self.forbidden_keywords:
            if keyword in ai_response:
                warnings.append(f"Forbidden keyword in output: {keyword}")
        
        state["is_safe"] = len(warnings) == 0
        
        if warnings:
            state["guardrail_warnings"].extend(warnings)
            logger.warning("check_output", "Unsafe output detected", warnings=warnings)
        
        return state
