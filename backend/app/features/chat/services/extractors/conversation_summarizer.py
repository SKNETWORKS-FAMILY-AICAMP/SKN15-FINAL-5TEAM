"""
Conversation Summarization Service
대화 요약 자동 생성 (장기 기억 시스템)

Features:
- 10턴마다 자동 요약 생성
- 임베딩 생성 (OpenAI)
- 중요 정보 추출 및 Memory 저장
- 컨텍스트 윈도우 관리
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient
from app.core.embeddings import get_embeddings

settings = get_settings()
logger = get_parent_logger("ConversationSummarizer")

# 요약 설정
SUMMARY_TRIGGER_TURN_COUNT = 10  # 10턴마다 요약
KEEP_RECENT_TURNS = 5  # 최근 5턴은 전문 유지


class ConversationSummarizer:
    """
    대화 요약 생성 시스템

    Features:
    - 대화 히스토리 요약
    - 임베딩 생성
    - 중요 정보 추출
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self.llm_client = llm_client
        self.embeddings_service = get_embeddings()

        logger.info("__init__", "ConversationSummarizer initialized")

    def should_create_summary(
        self,
        current_turn_count: int,
        last_summary_turn_count: int
    ) -> bool:
        """
        요약 생성 필요 여부 판단

        Args:
            current_turn_count: 현재 턴 수
            last_summary_turn_count: 마지막 요약 시점 턴 수

        Returns:
            요약 생성 필요 여부
        """
        return (current_turn_count - last_summary_turn_count) >= SUMMARY_TRIGGER_TURN_COUNT

    def extract_conversations_to_summarize(
        self,
        message_history: List[Dict[str, Any]],
        last_summary_turn_count: int,
        current_turn_count: int
    ) -> List[Dict[str, Any]]:
        """
        요약할 대화 추출 (오래된 대화만)

        Args:
            message_history: 전체 메시지 히스토리
            last_summary_turn_count: 마지막 요약 시점 턴 수
            current_turn_count: 현재 턴 수

        Returns:
            요약할 대화 리스트
        """
        summarize_until_turn = current_turn_count - KEEP_RECENT_TURNS

        conversations_to_summarize = []

        for msg in message_history:
            turn = msg.get("turn", 0)

            # 이미 요약된 턴 제외, 최근 턴도 제외
            if turn > last_summary_turn_count and turn <= summarize_until_turn:
                conversations_to_summarize.append(msg)

        return conversations_to_summarize

    def format_conversations_for_summary(
        self,
        conversations: List[Dict[str, Any]]
    ) -> str:
        """
        대화를 요약용 포맷으로 변환

        Args:
            conversations: 대화 리스트

        Returns:
            포맷팅된 문자열
        """
        formatted = []

        for conv in conversations:
            turn = conv.get("turn", "?")
            user_input = conv.get("user_input", "")

            # Agent 응답들
            agent_responses = conv.get("agent_responses", [])

            formatted.append(f"[Turn {turn}]")
            formatted.append(f"사용자: {user_input}")

            for resp in agent_responses:
                speaker = resp.get("speaker", "Unknown")
                text = resp.get("text", "")
                formatted.append(f"{speaker}: {text}")

            formatted.append("")  # 빈 줄

        return "\n".join(formatted)

    async def generate_summary(
        self,
        conversations: List[Dict[str, Any]],
        existing_summary: Optional[str] = None,
        scenario_context: Optional[str] = None
    ) -> str:
        """
        LLM을 사용하여 대화 요약 생성

        Args:
            conversations: 요약할 대화 리스트
            existing_summary: 기존 요약 (있으면 통합)
            scenario_context: 시나리오 컨텍스트

        Returns:
            생성된 요약
        """
        if not conversations:
            return existing_summary or ""

        if not self.llm_client:
            logger.warning("generate_summary", "LLM client not available")
            return existing_summary or ""

        # 대화 포맷팅
        conversation_text = self.format_conversations_for_summary(conversations)

        # 프롬프트 구성
        system_prompt = """당신은 대화 내용을 간결하고 정확하게 요약하는 AI입니다.

요약 시 다음 사항을 포함해주세요:
1. 주요 사건과 대화 내용
2. 캐릭터 간 상호작용 (감정, 관계 변화)
3. 중요한 결정이나 선택
4. 게임 진행 상황 (미션, 목표 등)
5. 친밀도나 게임 상태 변화

요약은 200-300 단어 이내로 간결하게 작성하되, 스토리의 연속성을 유지할 수 있도록 중요한 정보는 모두 포함해주세요."""

        user_prompt_parts = []

        # 기존 요약
        if existing_summary:
            user_prompt_parts.append("=== 기존 요약 ===")
            user_prompt_parts.append(existing_summary)
            user_prompt_parts.append("")

        # 시나리오 컨텍스트
        if scenario_context:
            user_prompt_parts.append("=== 시나리오 정보 ===")
            user_prompt_parts.append(scenario_context)
            user_prompt_parts.append("")

        # 새로운 대화
        user_prompt_parts.append("=== 요약할 대화 ===")
        user_prompt_parts.append(conversation_text)
        user_prompt_parts.append("")

        # 요청
        if existing_summary:
            user_prompt_parts.append("위의 기존 요약과 새로운 대화를 통합하여 전체 스토리를 요약해주세요.")
        else:
            user_prompt_parts.append("위의 대화 내용을 요약해주세요.")

        user_prompt = "\n".join(user_prompt_parts)

        try:
            # LLM 호출
            summary = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500,
                use_cache=False
            )

            logger.info("generate_summary", f"Generated summary ({len(summary)} chars)")
            return summary.strip()

        except Exception as e:
            logger.error("generate_summary", f"Summary generation failed: {e}")
            return existing_summary or ""

    def get_scenario_context(self, state: Dict[str, Any]) -> str:
        """
        State에서 시나리오 컨텍스트 추출

        Args:
            state: Session state

        Returns:
            컨텍스트 문자열
        """
        context_parts = []

        scenario_id = state.get("scenario_id", "unknown")
        context_parts.append(f"시나리오: {scenario_id}")

        current_stage = state.get("current_stage", "unknown")
        context_parts.append(f"현재 스테이지: {current_stage}")

        active_character = state.get("active_character", "unknown")
        context_parts.append(f"주요 캐릭터: {active_character}")

        user_name = state.get("user_name", "사용자")
        context_parts.append(f"사용자: {user_name}")

        affinity_scores = state.get("affinity_scores", {})
        if affinity_scores:
            affinity_str = ", ".join([f"{char}: {score}" for char, score in affinity_scores.items()])
            context_parts.append(f"친밀도: {affinity_str}")

        return "\n".join(context_parts)

    async def update_summary(
        self,
        state: Dict[str, Any],
        message_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        대화 요약 업데이트 (메인 함수)

        Args:
            state: Session state
            message_history: 메시지 히스토리

        Returns:
            {"summary": str, "summary_turn_count": int}
        """
        current_turn_count = state.get("turn_count", 0)
        last_summary_turn_count = state.get("summary_turn_count", 0)
        existing_summary = state.get("conversation_summary", "")

        # 요약 필요 여부 확인
        if not self.should_create_summary(current_turn_count, last_summary_turn_count):
            return {
                "summary": existing_summary,
                "summary_turn_count": last_summary_turn_count
            }

        logger.info("update_summary", f"Generating summary at turn {current_turn_count}")

        # 요약할 대화 추출
        conversations_to_summarize = self.extract_conversations_to_summarize(
            message_history,
            last_summary_turn_count,
            current_turn_count
        )

        if not conversations_to_summarize:
            logger.warning("update_summary", "No conversations to summarize")
            return {
                "summary": existing_summary,
                "summary_turn_count": last_summary_turn_count
            }

        # 시나리오 컨텍스트
        scenario_context = self.get_scenario_context(state)

        # 요약 생성
        new_summary = await self.generate_summary(
            conversations_to_summarize,
            existing_summary,
            scenario_context
        )

        logger.info("update_summary", "Summary generated",
                   turns_summarized=f"{last_summary_turn_count + 1}~{current_turn_count - KEEP_RECENT_TURNS}")

        return {
            "summary": new_summary,
            "summary_turn_count": current_turn_count - KEEP_RECENT_TURNS
        }

    def get_recent_conversations(
        self,
        message_history: List[Dict[str, Any]],
        keep_turns: int = KEEP_RECENT_TURNS
    ) -> List[Dict[str, Any]]:
        """
        최근 대화만 추출

        Args:
            message_history: 전체 메시지 히스토리
            keep_turns: 유지할 턴 수

        Returns:
            최근 대화 리스트
        """
        if not message_history:
            return []

        # 턴 번호 기준 정렬
        sorted_history = sorted(message_history, key=lambda x: x.get("turn", 0), reverse=True)

        return sorted_history[:keep_turns]

    def format_context_with_summary(
        self,
        summary: str,
        recent_conversations: List[Dict[str, Any]]
    ) -> str:
        """
        요약 + 최근 대화를 프롬프트용으로 포맷팅

        Args:
            summary: 대화 요약
            recent_conversations: 최근 대화 리스트

        Returns:
            포맷팅된 컨텍스트
        """
        parts = []

        # 요약
        if summary:
            parts.append("=== 이전 대화 요약 ===")
            parts.append(summary)
            parts.append("")

        # 최근 대화
        if recent_conversations:
            parts.append("=== 최근 대화 ===")
            recent_text = self.format_conversations_for_summary(recent_conversations)
            parts.append(recent_text)

        return "\n".join(parts)

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 또는 None
        """
        if not text or not text.strip():
            return None

        try:
            embedding = await self.embeddings_service.embed(text.strip())
            return embedding
        except Exception as e:
            logger.error("generate_embedding", f"Embedding generation failed: {e}")
            return None
