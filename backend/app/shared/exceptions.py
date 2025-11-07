"""
Shared Exceptions
공통 도메인 예외
"""
from app.core.errors import BusinessException, NotFoundException


# ============================================================
# 도메인 예외
# ============================================================

class DailyLimitExceededException(BusinessException):
    """일일 한도 초과"""
    def __init__(self, limit: int):
        super().__init__(
            message=f"Daily limit exceeded: {limit}",
            error_code="DAILY_LIMIT_EXCEEDED"
        )


class SessionNotFoundException(NotFoundException):
    """세션을 찾을 수 없음"""
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            error_code="SESSION_NOT_FOUND"
        )


class ScenarioNotFoundException(NotFoundException):
    """시나리오를 찾을 수 없음"""
    def __init__(self, scenario_id: str):
        super().__init__(
            message=f"Scenario not found: {scenario_id}",
            error_code="SCENARIO_NOT_FOUND"
        )


class UnsafeInputException(BusinessException):
    """안전하지 않은 입력"""
    def __init__(self, reason: str):
        super().__init__(
            message=f"Unsafe input: {reason}",
            error_code="UNSAFE_INPUT"
        )
