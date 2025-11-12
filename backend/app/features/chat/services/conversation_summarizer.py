"""
Conversation Summarizer Service
대화 요약 자동화 서비스

Features:
- LLM 기반 대화 요약
- 임베딩 생성 (pgvector)
- 주기적 요약 업데이트
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import openai
import os

from app.features.chat.models import ConversationSummary, DialogueTurn
from app.core.logging import get_parent_logger as get_service_logger

logger = get_service_logger("ConversationSummarizer")

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-ada-002"
SUMMARY_MODEL = os.getenv("LLM_MODEL", "gpt-4")

# 요약 트리거 설정
SUMMARY_UPDATE_THRESHOLD = 10  # N개 메시지마다 요약 업데이트


class ConversationSummarizerService:
    """
    대화 요약 서비스

    Layer 3: Service
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            임베딩 벡터 (1536 차원) 또는 None
        """
        if not OPENAI_API_KEY:
            logger.warning("generate_embedding", "OpenAI API key not configured")
            return None

        try:
            response = openai.Embedding.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            embedding = response['data'][0]['embedding']

            logger.debug("generate_embedding", f"Generated embedding for text (length: {len(text)})")
            return embedding

        except Exception as e:
            logger.error("generate_embedding", f"Failed to generate embedding: {e}")
            return None

    async def generate_summary(
        self,
        dialogue_turns: List[DialogueTurn],
        previous_summary: Optional[str] = None
    ) -> str:
        """
        LLM 기반 대화 요약 생성

        Args:
            dialogue_turns: 대화 턴 목록
            previous_summary: 이전 요약 (선택)

        Returns:
            생성된 요약 텍스트
        """
        if not OPENAI_API_KEY:
            logger.warning("generate_summary", "OpenAI API key not configured, using fallback")
            return self._fallback_summary(dialogue_turns)

        # 대화 텍스트 구성
        conversation_text = "\n".join([
            f"{turn.speaker}: {turn.content}"
            for turn in dialogue_turns
        ])

        # 프롬프트 구성
        if previous_summary:
            prompt = f"""이전 요약:
{previous_summary}

새로운 대화:
{conversation_text}

위 대화를 간결하게 요약해주세요. 중요한 사건, 감정, 결정 등을 포함하세요."""
        else:
            prompt = f"""다음 대화를 간결하게 요약해주세요:

{conversation_text}

중요한 사건, 감정, 결정 등을 포함하세요."""

        try:
            response = openai.ChatCompletion.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 대화를 간결하고 정확하게 요약하는 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )

            summary = response.choices[0].message.content.strip()
            logger.info("generate_summary", f"Generated summary for {len(dialogue_turns)} turns")
            return summary

        except Exception as e:
            logger.error("generate_summary", f"Failed to generate summary: {e}")
            return self._fallback_summary(dialogue_turns)

    def _fallback_summary(self, dialogue_turns: List[DialogueTurn]) -> str:
        """
        폴백 요약 (LLM 사용 불가 시)

        Args:
            dialogue_turns: 대화 턴 목록

        Returns:
            간단한 요약 텍스트
        """
        speakers = set(turn.speaker for turn in dialogue_turns)
        message_count = len(dialogue_turns)

        return f"{', '.join(speakers)} 간의 대화 ({message_count}개 메시지). 최근 메시지: {dialogue_turns[-1].content[:50]}..."

    async def get_or_create_summary(
        self,
        session_id: str,
        user_id: str,
        scenario_id: Optional[str] = None
    ) -> Optional[ConversationSummary]:
        """
        대화 요약 조회 또는 생성

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (선택)

        Returns:
            대화 요약 객체 또는 None
        """
        # 기존 요약 조회
        query = select(ConversationSummary).where(
            ConversationSummary.session_id == session_id
        )
        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()

        if summary:
            logger.debug("get_or_create_summary", f"Found existing summary for session {session_id}")
            return summary

        # 대화 턴 조회
        turns_query = select(DialogueTurn).where(
            DialogueTurn.session_id == session_id
        ).order_by(DialogueTurn.turn_number)

        turns_result = await self.db.execute(turns_query)
        turns = list(turns_result.scalars().all())

        if not turns:
            logger.debug("get_or_create_summary", f"No dialogue turns found for session {session_id}")
            return None

        # 새 요약 생성
        summary_text = await self.generate_summary(turns)
        embedding = await self.generate_embedding(summary_text)

        summary = ConversationSummary(
            session_id=session_id,
            user_id=user_id,
            scenario_id=scenario_id,
            summary_text=summary_text,
            embedding=embedding,
            message_count=len(turns),
            last_turn_number=turns[-1].turn_number
        )

        self.db.add(summary)
        await self.db.flush()

        logger.info("get_or_create_summary", f"Created new summary for session {session_id}")
        return summary

    async def update_conversation_summary(
        self,
        session_id: str,
        force_update: bool = False
    ) -> Optional[ConversationSummary]:
        """
        대화 요약 업데이트

        주기적으로 (N개 메시지마다) 또는 강제로 요약 업데이트

        Args:
            session_id: 세션 ID
            force_update: 강제 업데이트 여부

        Returns:
            업데이트된 요약 객체 또는 None
        """
        # 기존 요약 조회
        query = select(ConversationSummary).where(
            ConversationSummary.session_id == session_id
        )
        result = await self.db.execute(query)
        summary = result.scalar_one_or_none()

        if not summary:
            logger.debug("update_conversation_summary", f"No summary found for session {session_id}")
            return None

        # 새로운 대화 턴 조회
        turns_query = select(DialogueTurn).where(
            DialogueTurn.session_id == session_id,
            DialogueTurn.turn_number > summary.last_turn_number
        ).order_by(DialogueTurn.turn_number)

        turns_result = await self.db.execute(turns_query)
        new_turns = list(turns_result.scalars().all())

        # 업데이트 필요 여부 확인
        if not force_update and len(new_turns) < SUMMARY_UPDATE_THRESHOLD:
            logger.debug(
                "update_conversation_summary",
                f"Not enough new turns ({len(new_turns)}) to trigger update"
            )
            return summary

        if not new_turns:
            logger.debug("update_conversation_summary", "No new turns to summarize")
            return summary

        # 요약 업데이트
        new_summary_text = await self.generate_summary(new_turns, summary.summary_text)
        new_embedding = await self.generate_embedding(new_summary_text)

        summary.summary_text = new_summary_text
        summary.embedding = new_embedding
        summary.message_count += len(new_turns)
        summary.last_turn_number = new_turns[-1].turn_number
        summary.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(
            "update_conversation_summary",
            f"Updated summary for session {session_id}",
            new_turns=len(new_turns),
            total_messages=summary.message_count
        )
        return summary

    async def get_recent_summaries(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationSummary]:
        """
        사용자의 최근 대화 요약 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            요약 목록
        """
        query = select(ConversationSummary).where(
            ConversationSummary.user_id == user_id
        ).order_by(
            desc(ConversationSummary.updated_at)
        ).limit(limit)

        result = await self.db.execute(query)
        summaries = list(result.scalars().all())

        logger.debug("get_recent_summaries", f"Found {len(summaries)} recent summaries for user {user_id}")
        return summaries
