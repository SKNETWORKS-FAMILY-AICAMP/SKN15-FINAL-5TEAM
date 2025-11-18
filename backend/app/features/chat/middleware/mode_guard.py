"""
ModeGuard - 모드별 메모리 접근 제어 안전장치

Memory System v2의 핵심 규칙:
1. LTM (Long-term Memory)은 free-talk 모드에서만 읽기/쓰기 가능
2. Scenario Buffer는 시나리오 모드에서만 읽기/쓰기 가능
3. 위 규칙을 위반하면 강제 에러 발생 (시스템 무결성 보장)
"""
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModeGuard:
    """모드별 메모리 접근 제어 안전장치

    v2 Memory System의 핵심 규칙을 강제합니다:
    - LTM: free-talk 전용
    - Scenario Buffer: 시나리오 전용
    """

    @staticmethod
    def ensure_no_ltm_in_scenario(scenario_id: str, operation: str) -> None:
        """시나리오 모드에서 LTM 접근 시 강제 에러

        Args:
            scenario_id: 시나리오 ID
            operation: 작업 종류 (예: "create", "read", "update")

        Raises:
            ValueError: 시나리오 모드에서 LTM 접근 시
        """
        if scenario_id and scenario_id != "free-talk":
            error_msg = (
                f"[ModeGuard] LTM {operation} is FORBIDDEN in scenario mode: {scenario_id}. "
                f"Use Scenario Buffer instead. "
                f"LTM should only be accessed in free-talk mode."
            )
            logger.error("ModeGuard", error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def ensure_no_scenario_buffer_in_freechat(scenario_id: str, operation: str) -> None:
        """자유대화에서 Scenario Buffer 접근 시 강제 에러

        Args:
            scenario_id: 시나리오 ID
            operation: 작업 종류 (예: "update", "read")

        Raises:
            ValueError: free-talk 모드에서 Scenario Buffer 접근 시
        """
        if scenario_id == "free-talk":
            error_msg = (
                f"[ModeGuard] Scenario Buffer {operation} is FORBIDDEN in free-talk mode. "
                f"Use LTM instead. "
                f"Scenario Buffer should only be used in scenario modes."
            )
            logger.error("ModeGuard", error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def is_freechat(scenario_id: str) -> bool:
        """자유대화 모드 체크

        Args:
            scenario_id: 시나리오 ID

        Returns:
            bool: free-talk 모드이면 True
        """
        return scenario_id == "free-talk"

    @staticmethod
    def validate_scenario_mode(scenario_id: str) -> dict:
        """시나리오 모드 검증 및 정보 반환

        Args:
            scenario_id: 시나리오 ID

        Returns:
            dict: {
                "is_freechat": bool,
                "can_use_ltm": bool,
                "can_use_scenario_buffer": bool,
                "mode_name": str
            }
        """
        is_freechat = ModeGuard.is_freechat(scenario_id)

        return {
            "is_freechat": is_freechat,
            "can_use_ltm": is_freechat,
            "can_use_scenario_buffer": not is_freechat,
            "mode_name": "free-talk" if is_freechat else "scenario",
            "scenario_id": scenario_id
        }
