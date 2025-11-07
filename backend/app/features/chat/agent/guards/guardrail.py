"""
Guardrail Agent - 입력 검증
부적절한 입력 차단 및 안전성 검사
"""
import re
from typing import Dict, Any, List, Optional
from app.core.logging import get_parent_logger

logger = get_parent_logger("GuardrailAgent")


class ValidationResult:
    """검증 결과"""
    def __init__(
        self,
        is_valid: bool,
        reason: Optional[str] = None,
        severity: str = "low",
        message: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.reason = reason
        self.severity = severity  # low, medium, high
        self.message = message


class GuardrailAgent:
    """
    입력 검증 Agent

    책임:
    - 부적절한 내용 차단 (욕설, 폭력, 차별 등)
    - 의미 없는 입력 필터링
    - 시스템 명령어 차단
    - 입력 길이 검증

    Phase 3: 키워드 기반 간소화 버전
    TODO: 향후 임베딩 기반 검증 추가
    """

    # 금지 키워드 (간소화 버전)
    PROHIBITED_KEYWORDS = {
        "self_harm": ["자살", "자해", "죽고싶"],
        "sexual": ["sex", "섹스"],
        "violence": ["죽여", "때려", "폭력"],
        "hate": ["혐오", "차별"],
        "system": ["system:", "관리자:", "__", "override"]
    }

    def __init__(self):
        """GuardrailAgent 초기화"""
        self.max_input_length = 500  # 최대 입력 길이
        self.min_input_length = 1    # 최소 입력 길이
        logger.info("__init__", "GuardrailAgent initialized")

    def validate(self, user_input: str, state: Dict[str, Any]) -> ValidationResult:
        """
        입력 검증

        Args:
            user_input: 사용자 입력
            state: 세션 상태

        Returns:
            ValidationResult
        """
        user_input = user_input.strip()

        # 1. 길이 검증
        if len(user_input) < self.min_input_length:
            logger.warning("validate", "Input too short", length=len(user_input))
            return ValidationResult(
                is_valid=False,
                reason="input_too_short",
                severity="low",
                message="메시지를 입력해주세요."
            )

        if len(user_input) > self.max_input_length:
            logger.warning("validate", "Input too long", length=len(user_input))
            return ValidationResult(
                is_valid=False,
                reason="input_too_long",
                severity="medium",
                message=f"메시지가 너무 깁니다. ({self.max_input_length}자 이내로 입력해주세요)"
            )

        # 2. 시스템 명령어 차단
        if self._contains_system_command(user_input):
            logger.warning("validate", "System command detected", input_preview=user_input[:50])
            return ValidationResult(
                is_valid=False,
                reason="system_command",
                severity="high",
                message="시스템 명령어는 사용할 수 없습니다."
            )

        # 3. 금지 키워드 검사
        prohibited_category = self._check_prohibited_keywords(user_input)
        if prohibited_category:
            logger.warning("validate", f"Prohibited content: {prohibited_category}", input_preview=user_input[:50])

            # 경고 횟수 증가
            warnings = state.get("prohibited_warning_count", 0)
            warnings += 1
            state["prohibited_warning_count"] = warnings

            if warnings >= 2:
                # 2회 경고 시 차단
                return ValidationResult(
                    is_valid=False,
                    reason=f"prohibited_{prohibited_category}",
                    severity="high",
                    message="⛔️ 부적절한 발언으로 대화가 제한됩니다."
                )
            else:
                # 1회 경고
                return ValidationResult(
                    is_valid=False,
                    reason=f"prohibited_{prohibited_category}",
                    severity="medium",
                    message="🚨 부적절한 표현입니다. 이번만 경고합니다."
                )

        # 4. 의미 없는 입력 필터링
        if self._is_meaningless(user_input):
            logger.warning("validate", "Meaningless input", input_preview=user_input[:50])
            return ValidationResult(
                is_valid=False,
                reason="meaningless_input",
                severity="low",
                message="의미 있는 메시지를 입력해주세요."
            )

        # 5. 검증 통과
        logger.info("validate", "✅ Input validated", input_len=len(user_input))
        return ValidationResult(is_valid=True)

    def _contains_system_command(self, text: str) -> bool:
        """
        시스템 명령어 포함 여부 확인

        Args:
            text: 입력 텍스트

        Returns:
            시스템 명령어 포함 여부
        """
        text_lower = text.lower()

        # 시스템 명령어 패턴
        patterns = [
            r"system\s*:",
            r"관리자\s*:",
            r"__\w+__",
            r"override",
            r"admin\s*:",
            r"<script",
            r"javascript:",
        ]

        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _check_prohibited_keywords(self, text: str) -> Optional[str]:
        """
        금지 키워드 검사

        Args:
            text: 입력 텍스트

        Returns:
            금지된 카테고리 이름 또는 None
        """
        text_lower = text.lower()

        for category, keywords in self.PROHIBITED_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category

        return None

    def _is_meaningless(self, text: str) -> bool:
        """
        의미 없는 입력 판단

        Args:
            text: 입력 텍스트

        Returns:
            의미 없는지 여부
        """
        # 1. 같은 문자 반복 (5회 이상)
        if re.search(r"(.)\1{4,}", text):
            return True

        # 2. 공백만 있는 경우
        if not text.strip():
            return True

        # 3. 특수문자만 있는 경우 (3개 이상)
        if len(re.findall(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", text)) >= 3:
            text_without_special = re.sub(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", "", text)
            if len(text_without_special.strip()) < 2:
                return True

        return False

    def reset_warnings(self, state: Dict[str, Any]):
        """
        경고 횟수 초기화

        Args:
            state: 세션 상태
        """
        state["prohibited_warning_count"] = 0
        logger.info("reset_warnings", "Warnings reset")
