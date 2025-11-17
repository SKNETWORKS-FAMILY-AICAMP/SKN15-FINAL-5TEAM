"""
Scenario Buffer Manager - 시나리오 진행 정보 관리 서비스
"""
from typing import Dict, Any, Optional

from ..repositories.scenario_buffer_repository import ScenarioBufferRepository
from ..middleware.mode_guard import ModeGuard
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScenarioBufferManager:
    """Scenario Buffer 관리 서비스

    목적:
    - 시나리오 진행 정보 업데이트
    - 프롬프트용 Buffer 텍스트 생성
    - 시나리오 완료 시 삭제
    """

    def __init__(self, scenario_buffer_repository: ScenarioBufferRepository):
        self.scenario_buffer_repository = scenario_buffer_repository

    async def update_buffer(
        self,
        user_id: str,
        scenario_id: str,
        buffer_summary: Optional[str] = None,
        progress_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """시나리오 진행 정보 업데이트

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            buffer_summary: 시나리오 연속성 요약
            progress_data: 진행 상황 데이터

        Raises:
            ValueError: free-talk 모드에서 호출 시
        """
        # Guard: free-talk에서 호출 금지
        ModeGuard.ensure_no_scenario_buffer_in_freechat(scenario_id, "update")

        await self.scenario_buffer_repository.update_buffer(
            user_id=user_id,
            scenario_id=scenario_id,
            buffer_summary=buffer_summary,
            progress_data=progress_data
        )

        logger.info("update_buffer", f"Updated buffer for {scenario_id}")

    async def get_buffer_for_prompt(
        self,
        user_id: str,
        scenario_id: str
    ) -> Optional[str]:
        """프롬프트용 Scenario Buffer 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID

        Returns:
            Buffer 텍스트 (포맷팅된 문자열)
        """
        buffer = await self.scenario_buffer_repository.get_buffer(user_id, scenario_id)

        if not buffer:
            return None

        lines = []

        if buffer.buffer_summary:
            lines.append(f"[시나리오 요약]\n{buffer.buffer_summary}")

        if buffer.progress_data:
            progress = buffer.progress_data

            if progress.get("current_stage"):
                lines.append(f"\n[현재 스테이지]\n{progress['current_stage']}")

            if progress.get("choices_made"):
                choices = ", ".join(progress["choices_made"])
                lines.append(f"\n[선택 기록]\n{choices}")

            if progress.get("npc_states"):
                npc_lines = []
                for npc, state in progress["npc_states"].items():
                    state_str = ", ".join([f"{k}: {v}" for k, v in state.items()])
                    npc_lines.append(f"- {npc}: {state_str}")
                lines.append(f"\n[NPC 상태]\n" + "\n".join(npc_lines))

        return "\n".join(lines) if lines else None

    async def clear_buffer_on_scenario_end(
        self,
        user_id: str,
        scenario_id: str
    ) -> None:
        """시나리오 종료 시 삭제

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
        """
        await self.scenario_buffer_repository.delete_buffer(user_id, scenario_id)
        logger.info("clear_buffer_on_scenario_end",
                   f"Cleared buffer for scenario: {scenario_id}")
