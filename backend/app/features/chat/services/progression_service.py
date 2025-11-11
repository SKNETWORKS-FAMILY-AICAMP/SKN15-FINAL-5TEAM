"""
ProgressionService - XP 진행도 계산
"""


class ProgressionService:
    """
    XP 진행도 계산 서비스 (Stateless)

    역할:
    - XP 계산 로직 (DB 접근 없음)
    - 레벨 계산
    """

    def calculate_message_xp(self, message_length: int) -> int:
        """
        메시지 길이 기반 XP 계산

        Args:
            message_length: 메시지 길이

        Returns:
            XP 양
        """
        base_xp = 5

        # 길이에 따른 보너스
        if message_length > 50:
            base_xp += 5
        if message_length > 100:
            base_xp += 5
        if message_length > 200:
            base_xp += 10

        return base_xp

    def calculate_scenario_complete_xp(self, difficulty: str) -> int:
        """
        시나리오 완료 XP

        Args:
            difficulty: 난이도 (easy, normal, hard)

        Returns:
            XP 양
        """
        xp_map = {
            "easy": 100,
            "normal": 200,
            "hard": 300,
        }
        return xp_map.get(difficulty, 100)

    def calculate_level_from_xp(self, xp: int) -> int:
        """
        XP로부터 레벨 계산

        공식: level = floor(sqrt(XP / 100))

        Args:
            xp: 총 XP

        Returns:
            레벨
        """
        import math
        return math.floor(math.sqrt(xp / 100))

    def get_xp_for_next_level(self, current_level: int) -> int:
        """
        다음 레벨까지 필요한 총 XP

        Args:
            current_level: 현재 레벨

        Returns:
            다음 레벨까지 필요한 총 XP
        """
        next_level = current_level + 1
        return (next_level ** 2) * 100

    def get_xp_progress_to_next_level(
        self,
        current_xp: int,
        current_level: int
    ) -> dict:
        """
        다음 레벨까지 진행도

        Args:
            current_xp: 현재 XP
            current_level: 현재 레벨

        Returns:
            {
                "current_level": int,
                "next_level": int,
                "current_xp": int,
                "xp_for_current_level": int,
                "xp_for_next_level": int,
                "xp_needed": int,
                "progress_percentage": float
            }
        """
        xp_for_current = (current_level ** 2) * 100
        xp_for_next = ((current_level + 1) ** 2) * 100
        xp_needed = xp_for_next - current_xp

        xp_in_current_level = current_xp - xp_for_current
        xp_range = xp_for_next - xp_for_current
        progress = (xp_in_current_level / xp_range) * 100 if xp_range > 0 else 0

        return {
            "current_level": current_level,
            "next_level": current_level + 1,
            "current_xp": current_xp,
            "xp_for_current_level": xp_for_current,
            "xp_for_next_level": xp_for_next,
            "xp_needed": xp_needed,
            "progress_percentage": round(progress, 2)
        }


# 싱글톤
_progression_service = None


def get_progression_service() -> ProgressionService:
    """ProgressionService 싱글톤"""
    global _progression_service
    if _progression_service is None:
        _progression_service = ProgressionService()
    return _progression_service
