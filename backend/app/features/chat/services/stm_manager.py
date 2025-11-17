"""
STM Manager - Short-term Memory 관리 서비스
"""
from typing import Dict, Any, Optional
from datetime import datetime

from ..repositories.stm_repository import STMRepository
from .extractors.hierarchical_summarizer import HierarchicalSummarizer
from app.core.logging import get_logger

logger = get_logger(__name__)


class STMManager:
    """Short-term Memory 관리 서비스

    목적:
    - 대화 즉시 STM에 기록
    - 5턴마다 chunk 요약 생성
    - 프롬프트용 STM 텍스트 생성
    - 세션 종료 시 전체 요약
    """

    def __init__(
        self,
        stm_repository: STMRepository,
        hierarchical_summarizer: HierarchicalSummarizer
    ):
        self.stm_repository = stm_repository
        self.hierarchical_summarizer = hierarchical_summarizer

    async def update_stm(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str,
        new_turn_data: Dict[str, Any],
        message_history: list
    ) -> None:
        """대화 즉시 STM에 기록

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID
            new_turn_data: 새 턴 데이터
            message_history: 전체 메시지 히스토리
        """
        # 기존 STM 조회
        stm = await self.stm_repository.get_stm(user_id, scenario_id, session_id)

        turn_count = len(message_history)

        # 5턴마다 chunk 요약 생성
        if await self.hierarchical_summarizer.should_trigger_summary(message_history):
            recent_5_turns = message_history[-5:] if len(message_history) >= 5 else message_history

            chunk_summary = await self.hierarchical_summarizer.create_chunk_summary(
                recent_turns=recent_5_turns
            )

            # Chunk 추가
            chunk_data = {
                "chunk_id": (turn_count // 5),
                "turn_range": f"{max(1, turn_count - 4)}-{turn_count}",
                "summary": chunk_summary,
                "created_at": datetime.utcnow().isoformat()
            }

            if stm:
                await self.stm_repository.append_chunk(stm.id, chunk_data)
            else:
                # 첫 STM 생성
                await self.stm_repository.create_or_update_stm(
                    user_id=user_id,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    chunk_summaries=[chunk_data],
                    turn_count=turn_count
                )

            logger.info("update_stm", f"Created chunk summary for turns {chunk_data['turn_range']}")
        else:
            # Turn count만 업데이트
            if stm:
                stm.turn_count = turn_count
                stm.last_turn_timestamp = datetime.utcnow()
                await self.stm_repository.create_or_update_stm(
                    user_id=user_id,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    turn_count=turn_count
                )
            else:
                await self.stm_repository.create_or_update_stm(
                    user_id=user_id,
                    scenario_id=scenario_id,
                    session_id=session_id,
                    turn_count=turn_count
                )

    async def get_stm_for_prompt(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str
    ) -> Optional[str]:
        """프롬프트용 STM 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID

        Returns:
            STM 텍스트 (포맷팅된 문자열)
        """
        stm = await self.stm_repository.get_stm(user_id, scenario_id, session_id)

        if not stm or not stm.chunk_summaries:
            return None

        # 모든 chunk를 시간순으로 포맷팅
        chunks_text = "\n\n".join([
            f"[{chunk['turn_range']}턴] {chunk['summary']}"
            for chunk in stm.chunk_summaries
        ])

        return chunks_text

    async def finalize_session_to_ltm(
        self,
        user_id: str,
        scenario_id: str,
        session_id: str,
        is_freechat: bool
    ) -> Optional[str]:
        """세션 종료 시: STM → 세션 요약 생성

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            session_id: 세션 ID
            is_freechat: 자유대화 모드 여부

        Returns:
            session_summary: 세션 전체 요약
        """
        stm = await self.stm_repository.get_stm(user_id, scenario_id, session_id)

        if not stm or not stm.chunk_summaries:
            logger.warning("finalize_session_to_ltm", f"No STM found for session {session_id}")
            return None

        # 전체 세션 요약
        session_summary = await self.hierarchical_summarizer.summarize_full_session(
            stm.chunk_summaries
        )

        logger.info("finalize_session_to_ltm",
                   f"Session finalized: {session_id}, is_freechat={is_freechat}")

        return session_summary
