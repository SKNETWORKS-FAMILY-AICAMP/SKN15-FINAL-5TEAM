"""
자동 Memory 추출 모듈

conversation_summary에서 LLM을 사용하여 중요한 정보를 추출하고
user_memories 테이블에 자동 저장합니다.

IMemoryRepository를 사용하여 DatabaseManager 의존성 제거
"""

# ============================================================
# 🧠 메모리 추출기 — 요약에서 장기 기억 생성
# ============================================================
import json
from typing import Dict, List, Optional, Any
from src.infrastructure.shared.dependency_container import get_llm_provider as get_llm_client
from src.core.interfaces.repositories.memory_repository import IMemoryRepository


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
    "confidence": 0.9
  }},
  {{
    "memory_key": "user_preference:choice_style",
    "memory_value": "신중하게 선택을 고민하는 스타일. 동료들의 의견을 중요하게 생각함",
    "memory_type": "preference",
    "importance": 0.7,
    "tags": ["choice", "careful", "collaborative"],
    "confidence": 0.85
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


async def extract_memories_from_summary(
    conversation_summary: str,
    llm_client: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    대화 요약에서 장기 기억 추출 (LLM 사용)

    Args:
        conversation_summary: 대화 요약 텍스트
        llm_client: LLM 클라이언트 (없으면 자동 생성)

    Returns:
        List of memory dictionaries
    """
    if not conversation_summary or len(conversation_summary.strip()) < 50:
        return []

    client = llm_client or get_llm_client()

    try:
        prompt = MEMORY_EXTRACTION_PROMPT.format(
            conversation_summary=conversation_summary
        )

        # LLM 호출
        result = client.call(
            system_prompt="You are an AI that extracts important information from conversation summaries.",
            user_prompt=prompt,
            temperature=0.3,  # 낮은 temperature로 일관성 확보
            max_tokens=1000,
            agent="memory_extractor"
        )

        try:
            result_text = result.strip()
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif "```" in result_text:
                start = result_text.find("```") + 3
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()

            memories = json.loads(result_text)

            if not isinstance(memories, list):
                print(f"⚠️ Memory extraction returned non-list: {type(memories)}")
                return []

            # 
            valid_memories = []
            for mem in memories:
                if not isinstance(mem, dict):
                    continue
                if not all(k in mem for k in ["memory_key", "memory_value", "memory_type"]):
                    continue

                # 
                mem.setdefault("importance", 0.5)
                mem.setdefault("tags", [])
                mem.setdefault("confidence", 0.8)

                #  
                mem["importance"] = max(0.0, min(1.0, mem["importance"]))
                mem["confidence"] = max(0.0, min(1.0, mem["confidence"]))

                valid_memories.append(mem)

            return valid_memories[:5]  # 최대 5개

        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse memory extraction JSON: {e}")
            print(f"   Raw output: {result[:200]}")
            return []

    except Exception as e:
        print(f"⚠️ Memory extraction failed: {e}")
        return []


async def extract_and_save_memories(
    user_id: str,
    session_id: str,
    conversation_summary: str,
    memory_repository: IMemoryRepository,
    llm_client: Optional[Any] = None
) -> int:
    """
    대화 요약에서 기억을 추출하고 DB에 저장

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        conversation_summary: 대화 요약
        memory_repository: IMemoryRepository 인스턴스
        llm_client: LLM 클라이언트 (선택)

    Returns:
        저장된 기억 개수
    """
    if not user_id:
        return 0

    memories = await extract_memories_from_summary(conversation_summary, llm_client)

    if not memories:
        return 0

    saved_count = 0
    for memory in memories:
        try:
            # IMemoryRepository.create_or_update_memory() 사용
            memory_id = memory_repository.create_or_update_memory(
                user_id=user_id,
                memory_key=memory["memory_key"],
                memory_value=memory["memory_value"],
                memory_type=memory["memory_type"],
                importance=memory["importance"],
                tags=memory.get("tags", []),
                confidence=memory.get("confidence"),
                context={"source_session_id": session_id}
            )

            if memory_id:
                saved_count += 1
                print(f"🧠 Memory saved: {memory['memory_type']} - {memory['memory_key']}")

        except Exception as e:
            print(f"⚠️ Failed to save memory '{memory.get('memory_key')}': {e}")

    return saved_count
