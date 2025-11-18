"""
HierarchicalSummarizer - 계층적 요약 서비스 (5턴 기반)

Memory System v2의 핵심 요약 전략:
1. 5턴마다 Chunk Summary 생성 (LLM 1회)
2. Chunk + 기존 LTM → Hierarchical Re-summary (LLM 1회)
3. 세션 종료 시: 전체 Chunk → Session Summary
"""
from typing import List, Dict, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class HierarchicalSummarizer:
    """계층적 요약 서비스

    v2 요약 전략:
    - 5턴마다 요약 트리거
    - Chunk Summary → LTM Merge

    Note: LLMClient를 내부에서 직접 생성하여 사용
    """

    SUMMARY_TRIGGER_TURN_COUNT = 5  # 5턴마다 요약

    def __init__(self):
        """HierarchicalSummarizer 초기화

        LLMClient는 메서드 호출 시마다 생성하여 사용
        """
        pass

    async def should_trigger_summary(self, message_history: List[Dict[str, Any]]) -> bool:
        """요약 트리거 조건: 5턴 누적

        Args:
            message_history: 전체 메시지 히스토리

        Returns:
            bool: 요약이 필요하면 True
        """
        turn_count = len(message_history)
        should_trigger = turn_count > 0 and turn_count % self.SUMMARY_TRIGGER_TURN_COUNT == 0

        if should_trigger:
            logger.info("should_trigger_summary", f"Summary triggered at {turn_count} turns")

        return should_trigger

    async def create_chunk_summary(
        self,
        recent_turns: List[Dict[str, Any]],
        scenario_context: Optional[str] = None
    ) -> str:
        """5턴 → Chunk Summary (LLM 1회)

        Args:
            recent_turns: 최근 5턴 데이터
            scenario_context: 시나리오 맥락 (선택적)

        Returns:
            chunk_summary: 100-150 단어 요약
        """
        # 대화 포맷팅
        conversations = []
        for turn in recent_turns:
            user_input = turn.get("user_input", "")
            agent_responses = turn.get("agent_responses", [])

            if user_input:
                conversations.append(f"[사용자] {user_input}")

            for resp in agent_responses:
                speaker = resp.get("speaker", "NPC")
                text = resp.get("text", "")
                conversations.append(f"[{speaker}] {text}")

        conversation_text = "\n".join(conversations)

        system_prompt = """당신은 대화 내용을 간결하게 요약하는 AI입니다.

주어진 5턴의 대화를 다음 관점에서 요약하세요:
1. 주요 사건과 대화 흐름
2. 캐릭터 간 상호작용 (감정, 관계 변화)
3. 중요한 결정이나 선택
4. 게임 진행 상황 (미션, 목표 등)

요약은 100-150 단어 이내로 간결하게 작성하세요."""

        user_prompt = f"""다음 대화를 요약하세요:

{conversation_text}
"""

        if scenario_context:
            user_prompt = f"[시나리오 맥락]\n{scenario_context}\n\n{user_prompt}"

        try:
            # LLMClient 직접 사용 (text 응답)
            from app.core.llm import LLMClient
            llm_client = LLMClient()

            chunk_summary = await llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300
            )

            logger.info("create_chunk_summary", f"Created chunk summary for {len(recent_turns)} turns")
            return chunk_summary.strip()
        except Exception as e:
            logger.error("create_chunk_summary", f"Failed to create chunk summary: {e}", exc_info=True)
            return f"[요약 실패] {len(recent_turns)}턴 대화"

    async def merge_with_ltm(
        self,
        chunk_summary: str,
        existing_ltm: Optional[str] = None
    ) -> str:
        """Chunk + 기존 LTM → Hierarchical Re-summary (LLM 1회)

        Args:
            chunk_summary: 새로운 chunk 요약
            existing_ltm: 기존 LTM 요약

        Returns:
            merged_ltm: 통합된 LTM 요약
        """
        if not existing_ltm:
            # 첫 LTM
            logger.info("merge_with_ltm", "First LTM created from chunk")
            return chunk_summary

        system_prompt = """당신은 대화 기록을 계층적으로 요약하는 AI입니다.

기존 장기 기억(LTM)과 새로운 대화 요약을 통합하여 업데이트된 LTM을 생성하세요.

규칙:
1. 중요한 정보는 유지하되, 중복은 제거
2. 시간 순서 유지
3. 관계 변화, 주요 사건 중심으로 요약
4. 최대 200-250 단어 이내"""

        user_prompt = f"""[기존 LTM]
{existing_ltm}

[새로운 대화 요약]
{chunk_summary}

위 두 가지를 통합하여 업데이트된 LTM을 생성하세요."""

        try:
            # LLMClient 직접 사용
            from app.core.llm import LLMClient
            llm_client = LLMClient()

            merged_ltm = await llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=400
            )

            logger.info("merge_with_ltm", "Merged chunk with existing LTM")
            return merged_ltm.strip()
        except Exception as e:
            logger.error("merge_with_ltm", f"Failed to merge with LTM: {e}", exc_info=True)
            # Fallback: 단순 결합
            return f"{existing_ltm}\n\n[최근 업데이트]\n{chunk_summary}"

    async def summarize_full_session(
        self,
        chunk_summaries: List[Dict[str, Any]]
    ) -> str:
        """세션 종료 시: 전체 chunk를 하나의 세션 요약으로 압축

        Args:
            chunk_summaries: chunk 요약 배열

        Returns:
            session_summary: 세션 전체 요약
        """
        if not chunk_summaries:
            logger.warning("summarize_full_session", "No chunk summaries provided")
            return ""

        chunks_text = "\n\n".join([
            f"[{chunk.get('turn_range', 'N/A')}턴]\n{chunk.get('summary', '')}"
            for chunk in chunk_summaries
        ])

        system_prompt = """당신은 세션 전체를 요약하는 AI입니다.

여러 chunk 요약을 하나의 세션 요약으로 통합하세요.

요약 시 포함 사항:
1. 세션 전체의 주요 흐름
2. 중요한 결정과 사건
3. 캐릭터 관계 변화
4. 최종 상태

최대 150-200 단어 이내로 작성하세요."""

        user_prompt = f"""다음 chunk 요약들을 하나의 세션 요약으로 통합하세요:

{chunks_text}
"""

        try:
            # LLMClient 직접 사용
            from app.core.llm import LLMClient
            llm_client = LLMClient()

            session_summary = await llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=350
            )

            logger.info("summarize_full_session",
                       f"Created session summary from {len(chunk_summaries)} chunks")
            return session_summary.strip()
        except Exception as e:
            logger.error("summarize_full_session", f"Failed to summarize session: {e}", exc_info=True)
            # Fallback: 첫 chunk와 마지막 chunk만 사용
            if len(chunk_summaries) == 1:
                return chunk_summaries[0].get('summary', '')
            else:
                first = chunk_summaries[0].get('summary', '')
                last = chunk_summaries[-1].get('summary', '')
                return f"{first}\n\n...\n\n{last}"
