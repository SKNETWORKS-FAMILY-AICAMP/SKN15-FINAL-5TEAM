"""
Memory Extraction Service
대화 요약에서 장기 기억 자동 추출

Memory Types:
- relationship: 캐릭터 관계
- preference: 사용자 선호도
- event: 스토리 진행
- fact: 사실 정보
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.core.config import get_settings
from app.core.logging import get_parent_logger
from app.core.llm.client import LLMClient

settings = get_settings()
logger = get_parent_logger("MemoryExtractor")


@dataclass
class Memory:
    """추출된 기억"""
    memory_key: str
    memory_value: str
    memory_type: str  # 'relationship', 'preference', 'event', 'fact'
    importance: float  # 0.0-1.0
    tags: List[str]
    confidence: float  # 0.0-1.0
    related_entities: Optional[List[str]] = None  # 관련 엔티티 이름 리스트

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# Memory 추출 프롬프트
MEMORY_EXTRACTION_PROMPT = """다음은 사용자와 AI 캐릭터 간의 대화 요약입니다.

이 요약에서 사용자의 **장기 기억**으로 저장할 만한 중요한 정보를 추출하세요.

대화 요약:
{conversation_summary}

추출할 정보 타입:
1. **relationship** (캐릭터 관계): 특정 캐릭터와의 관계, 친밀도 변화, 상호작용 패턴
2. **preference** (사용자 선호도): 대화 스타일, 선택 패턴, 플레이 스타일
3. **event** (스토리 진행): 중요한 스토리 이벤트, 미션 완료, 스테이지 진행
4. **fact** (사실 정보): 사용자에 대한 객관적 사실 (좋아하는 것, 특징 등)

출력 형식 (JSON):
[
  {{
    "memory_key": "character_relationship:tanjiro",
    "memory_value": "탄지로와의 신뢰 관계가 깊어짐. 함께 위험한 상황을 극복했음",
    "memory_type": "relationship",
    "importance": 0.8,
    "tags": ["tanjiro", "relationship", "trust"],
    "confidence": 0.9,
    "related_entities": ["tanjiro"]
  }},
  {{
    "memory_key": "user_preference:choice_style",
    "memory_value": "신중하게 선택을 고민하는 스타일. 동료들의 의견을 중요하게 생각함",
    "memory_type": "preference",
    "importance": 0.7,
    "tags": ["choice", "careful", "collaborative"],
    "confidence": 0.85,
    "related_entities": []
  }}
]

규칙:
- memory_key는 고유해야 함 (타입:식별자 형식)
- importance는 0.0~1.0 (중요도, 높을수록 중요)
- confidence는 0.0~1.0 (확신도, 높을수록 확실)
- 중요하지 않거나 일시적인 정보는 제외
- 최대 5개까지만 추출
- 빈 배열 [] 반환 가능 (추출할 것이 없으면)

JSON만 출력하세요:"""


class MemoryExtractor:
    """
    대화 요약에서 장기 기억 추출 시스템
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self.llm_client = llm_client

        logger.info("__init__", "MemoryExtractor initialized")

    async def extract_memories(
        self,
        conversation_summary: str
    ) -> List[Memory]:
        """
        대화 요약에서 장기 기억 추출

        Args:
            conversation_summary: 대화 요약 텍스트

        Returns:
            추출된 Memory 리스트
        """
        if not conversation_summary or len(conversation_summary.strip()) < 50:
            logger.warning("extract_memories", "Conversation summary too short or empty")
            return []

        if not self.llm_client:
            logger.warning("extract_memories", "LLM client not available")
            return []

        try:
            system_prompt = "You are an AI that extracts important information from conversation summaries."

            user_prompt = MEMORY_EXTRACTION_PROMPT.format(
                conversation_summary=conversation_summary
            )

            # LLM 호출
            result_text = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1000,
                use_cache=False
            )

            # JSON 파싱
            try:
                # JSON 블록 추출
                if "```json" in result_text:
                    start = result_text.find("```json") + 7
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()
                elif "```" in result_text:
                    start = result_text.find("```") + 3
                    end = result_text.find("```", start)
                    result_text = result_text[start:end].strip()

                memories_data = json.loads(result_text)

                if not isinstance(memories_data, list):
                    logger.warning("extract_memories", f"Non-list result: {type(memories_data)}")
                    return []

                # Validation 및 변환
                memories = []
                for mem_data in memories_data:
                    if not isinstance(mem_data, dict):
                        continue

                    # 필수 필드 체크
                    if not all(k in mem_data for k in ["memory_key", "memory_value", "memory_type"]):
                        continue

                    # Normalize
                    importance = float(mem_data.get("importance", 0.5))
                    confidence = float(mem_data.get("confidence", 0.8))
                    tags = mem_data.get("tags", [])
                    related_entities = mem_data.get("related_entities", [])

                    # Clamp values
                    importance = max(0.0, min(1.0, importance))
                    confidence = max(0.0, min(1.0, confidence))

                    memories.append(Memory(
                        memory_key=mem_data["memory_key"],
                        memory_value=mem_data["memory_value"],
                        memory_type=mem_data["memory_type"],
                        importance=importance,
                        tags=tags if isinstance(tags, list) else [],
                        confidence=confidence,
                        related_entities=related_entities if isinstance(related_entities, list) else []
                    ))

                # 최대 5개로 제한
                memories = memories[:5]

                logger.info("extract_memories", f"Extracted {len(memories)} memories")
                return memories

            except json.JSONDecodeError as e:
                logger.error("extract_memories", f"JSON parsing failed: {e}")
                logger.debug("extract_memories", f"Raw output: {result_text[:200]}")
                return []

        except Exception as e:
            logger.error("extract_memories", f"Memory extraction failed: {e}")
            return []

    async def extract_long_term_traits(
        self,
        session_summary: str
    ) -> List[Memory]:
        """세션 요약에서 장기 특성만 추출 (단발성 정보 제외)

        v2 Memory System: 세션 종료 시 자유대화 모드에서만 호출

        Args:
            session_summary: 세션 전체 요약

        Returns:
            List[Memory]: 장기 특성 메모리 (최대 3개, importance >= 0.7)
        """
        LONG_TERM_TRAITS_PROMPT = """다음은 세션 전체 요약입니다.

이 요약에서 **장기적으로 유지되어야 할 사용자 특성**만 추출하세요.

추출 대상:
1. **relationship** (캐릭터 관계): 지속적인 관계, 신뢰도 변화
2. **preference** (사용자 선호도): 일관된 선택 패턴, 플레이 스타일
3. **personality** (성격 특성): 반복적으로 나타나는 성격
4. **traits** (고정 특징): 사용자의 안정적인 특징

제외 대상:
- 단발성 사건 (예: "오늘 주먹밥을 샀다")
- 일시적 감정 (예: "잠깐 화가 났다")
- 특정 시나리오 진행 정보

출력 형식 (JSON):
[
  {{
    "memory_key": "relationship:tanjiro",
    "memory_value": "탄지로와의 신뢰 관계가 깊어짐. 함께 싸우며 동료애를 느낌.",
    "memory_type": "relationship",
    "importance": 0.8,
    "tags": ["tanjiro", "relationship", "trust"],
    "confidence": 0.9
  }}
]

규칙:
- 장기 특성만 추출 (단발성 제외)
- 최대 3개까지만 추출
- importance는 0.7 이상만

[세션 요약]
{session_summary}
"""

        try:
            result_text = await self.llm_client.call(
                system_prompt="You are an AI that extracts long-term user traits from session summaries.",
                user_prompt=LONG_TERM_TRAITS_PROMPT.format(session_summary=session_summary),
                temperature=0.3,
                max_tokens=800
            )

            # JSON 파싱
            try:
                result_text = result_text.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                result_text = result_text.strip()

                memories_data = json.loads(result_text)

                memories = []
                for mem_data in memories_data:
                    if not all(k in mem_data for k in ["memory_key", "memory_value", "memory_type"]):
                        continue

                    # importance 0.7 이상만
                    importance = float(mem_data.get("importance", 0.5))
                    if importance < 0.7:
                        continue

                    memories.append(Memory(
                        memory_key=mem_data["memory_key"],
                        memory_value=mem_data["memory_value"],
                        memory_type=mem_data["memory_type"],
                        importance=importance,
                        tags=mem_data.get("tags", []),
                        confidence=float(mem_data.get("confidence", 0.8))
                    ))

                # 최대 3개
                memories = memories[:3]
                logger.info("extract_long_term_traits", f"Extracted {len(memories)} long-term traits")
                return memories

            except json.JSONDecodeError as e:
                logger.error("extract_long_term_traits", f"JSON parsing failed: {e}")
                return []

        except Exception as e:
            logger.error("extract_long_term_traits", f"Long-term traits extraction failed: {e}")
            return []

    async def extract_and_save(
        self,
        user_id: str,
        session_id: str,
        conversation_summary: str,
        repository: Any  # ChatRepository
    ) -> int:
        """
        기억 추출 후 Repository를 통해 DB에 저장

        Args:
            user_id: 사용자 ID
            session_id: 세션 ID
            conversation_summary: 대화 요약
            repository: ChatRepository 인스턴스

        Returns:
            저장된 기억 개수
        """
        if not user_id:
            logger.warning("extract_and_save", "user_id is required")
            return 0

        # 기억 추출
        memories = await self.extract_memories(conversation_summary)

        if not memories:
            return 0

        # Repository를 통해 저장
        saved_count = 0
        for memory in memories:
            try:
                memory_id = await repository.save_memory(
                    user_id=user_id,
                    memory_key=memory.memory_key,
                    memory_value=memory.memory_value,
                    memory_type=memory.memory_type,
                    importance=memory.importance,
                    source_session_id=session_id,
                    tags=memory.tags,
                    metadata={
                        "confidence": memory.confidence
                    }
                )

                if memory_id:
                    saved_count += 1
                    logger.info("extract_and_save", f"Memory saved: {memory.memory_type} - {memory.memory_key}")

            except Exception as e:
                logger.error("extract_and_save", f"Failed to save memory '{memory.memory_key}': {e}")

        logger.info("extract_and_save", f"Saved {saved_count}/{len(memories)} memories")
        return saved_count
