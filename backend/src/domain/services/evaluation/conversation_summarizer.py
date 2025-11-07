"""
대화 요약 생성 유틸리티 (장기기억 시스템)

대화 히스토리가 일정 길이를 넘으면 오래된 대화를 LLM으로 요약하여
컨텍스트 윈도우를 효율적으로 관리합니다.

추가 기능:
- 임베딩 생성 (OpenAI text-embedding-3-small)
- 중요한 정보 추출 (선호도, 사실 등)
- user_memories 테이블에 저장
"""

# ============================================================
# 📝 대화 요약기 — 세션 요약과 스테이지 기록
# ============================================================
import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI

from ...models.conversation import ConversationTurn, Dialogue

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 요약 설정
SUMMARY_TRIGGER_TURN_COUNT = 10  # 10턴마다 요약
KEEP_RECENT_TURNS = 5  # 최근 5턴은 전문 유지
SUMMARY_MODEL = "gpt-4o-mini"  # 요약용 모델 (저렴하고 빠름)
EMBEDDING_MODEL = "text-embedding-3-small"  # 임베딩 모델 (1536차원)


def should_create_summary(
    current_turn_count: int,
    last_summary_turn_count: int
) -> bool:
    """
    요약을 생성해야 하는지 판단

    Args:
        current_turn_count: 현재 대화 턴 수
        last_summary_turn_count: 마지막 요약 시점의 턴 수

    Returns:
        bool: 요약 생성 필요 여부
    """
    return (current_turn_count - last_summary_turn_count) >= SUMMARY_TRIGGER_TURN_COUNT


def extract_conversations_to_summarize(
    message_history: List[ConversationTurn],
    last_summary_turn_count: int,
    current_turn_count: int
) -> List[ConversationTurn]:
    """
    요약할 대화 추출 (오래된 대화만)

    Args:
        message_history: 전체 메시지 히스토리
        last_summary_turn_count: 마지막 요약 시점의 턴 수
        current_turn_count: 현재 턴 수

    Returns:
        요약할 대화 목록
    """
    summarize_until_turn = current_turn_count - KEEP_RECENT_TURNS

    conversations_to_summarize = []

    for msg in message_history:
        turn = msg.turn_number

        # 이미 요약된 턴은 제외, 최근 턴도 제외
        if turn > last_summary_turn_count and turn <= summarize_until_turn:
            conversations_to_summarize.append(msg)

    return conversations_to_summarize


def format_conversations_for_summary(
    conversations: List[ConversationTurn]
) -> str:
    """
    대화를 요약하기 좋은 형식으로 포맷팅

    Args:
        conversations: 대화 목록

    Returns:
        포맷팅된 대화 문자열
    """
    formatted = []

    for conv in conversations:
        turn = conv.turn_number
        user_input = conv.user_input

        # 에이전트 응답들
        agent_responses = conv.agent_responses

        formatted.append(f"[Turn {turn}]")
        formatted.append(f"사용자: {user_input}")

        for resp in agent_responses:
            speaker = resp.speaker
            text = resp.content
            formatted.append(f"{speaker}: {text}")

        formatted.append("")  # 빈 줄

    return "\n".join(formatted)


async def generate_conversation_summary(
    conversations: List[ConversationTurn],
    existing_summary: Optional[str] = None,
    scenario_context: Optional[str] = None
) -> str:
    """
    LLM을 사용하여 대화 요약 생성

    Args:
        conversations: 요약할 대화 목록
        existing_summary: 기존 요약 (있을 경우 통합)
        scenario_context: 시나리오 컨텍스트 (캐릭터, 배경 등)

    Returns:
        생성된 요약 텍스트
    """
    if not conversations:
        return existing_summary or ""

    # 대화 포맷팅
    conversation_text = format_conversations_for_summary(conversations)

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

    # 기존 요약이 있으면 먼저 제시
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
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # 일관성 있는 요약을 위해 낮은 temperature
            max_tokens=500,
        )

        summary = response.choices[0].message.content.strip()
        return summary

    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        # 요약 생성 실패 시 기존 요약 반환
        return existing_summary or ""


def get_scenario_context(state: Dict[str, Any]) -> str:
    """
    GraphState에서 시나리오 컨텍스트 추출

    Args:
        state: GraphState

    Returns:
        시나리오 컨텍스트 문자열
    """
    context_parts = []

    # 시나리오 
    scenario_id = state.get("scenario_id", "unknown")
    context_parts.append(f"시나리오: {scenario_id}")

    # 현재 스테이지
    current_stage = state.get("current_stage", "unknown")
    context_parts.append(f"현재 스테이지: {current_stage}")

    # 활성 캐릭터
    active_character = state.get("active_character", "unknown")
    context_parts.append(f"주요 캐릭터: {active_character}")

    # 사용자 이름
    user_name = state.get("user_name", "사용자")
    context_parts.append(f"사용자: {user_name}")

    # 친밀도 점수
    affinity_scores = state.get("affinity_scores", {})
    if affinity_scores:
        affinity_str = ", ".join([f"{char}: {score}" for char, score in affinity_scores.items()])
        context_parts.append(f"친밀도: {affinity_str}")

    return "\n".join(context_parts)


async def update_conversation_summary(
    state: Dict[str, Any],
    message_history: List[ConversationTurn]
) -> Dict[str, Any]:
    """
    대화 요약 업데이트 (메인 함수)

    Args:
        state: GraphState
        message_history: 메시지 히스토리

    Returns:
        업데이트된 요약 정보 {"summary": str, "summary_turn_count": int}
    """
    current_turn_count = state.get("turn_count", 0)
    last_summary_turn_count = state.get("summary_turn_count", 0)
    existing_summary = state.get("conversation_summary", "")

    # 요약이 필요한지 확인
    if not should_create_summary(current_turn_count, last_summary_turn_count):
        return {
            "summary": existing_summary,
            "summary_turn_count": last_summary_turn_count
        }

    print(f"🧠 Generating conversation summary (Turn {current_turn_count})...")

    # 요약할 대화 추출
    conversations_to_summarize = extract_conversations_to_summarize(
        message_history,
        last_summary_turn_count,
        current_turn_count
    )

    if not conversations_to_summarize:
        print("⚠️ No new conversations to summarize")
        return {
            "summary": existing_summary,
            "summary_turn_count": last_summary_turn_count
        }

    # 시나리오 컨텍스트 추출
    scenario_context = get_scenario_context(state)

    # 요약 생성
    new_summary = await generate_conversation_summary(
        conversations_to_summarize,
        existing_summary,
        scenario_context
    )

    print(f"✅ Summary generated ({len(new_summary)} characters)")
    print(f"📊 Summarized turns: {last_summary_turn_count + 1} ~ {current_turn_count - KEEP_RECENT_TURNS}")

    return {
        "summary": new_summary,
        "summary_turn_count": current_turn_count - KEEP_RECENT_TURNS
    }


def get_recent_conversations(
    message_history: List[ConversationTurn],
    keep_turns: int = KEEP_RECENT_TURNS
) -> List[ConversationTurn]:
    """
    최근 대화만 추출

    Args:
        message_history: 전체 메시지 히스토리
        keep_turns: 유지할 턴 수

    Returns:
        최근 대화 목록
    """
    if not message_history:
        return []

    # 턴 번호 기준으로 정렬
    sorted_history = sorted(message_history, key=lambda x: x.turn_number, reverse=True)

    return sorted_history[:keep_turns]


def format_context_with_summary(
    summary: str,
    recent_conversations: List[ConversationTurn]
) -> str:
    """
    요약 + 최근 대화를 프롬프트용으로 포맷팅

    Args:
        summary: 대화 요약
        recent_conversations: 최근 대화 목록

    Returns:
        포맷팅된 컨텍스트 문자열
    """
    parts = []

    # 요약 섹션
    if summary:
        parts.append("=== 이전 대화 요약 ===")
        parts.append(summary)
        parts.append("")

    # 최근 대화 섹션
    if recent_conversations:
        parts.append("=== 최근 대화 ===")
        recent_text = format_conversations_for_summary(recent_conversations)
        parts.append(recent_text)

    return "\n".join(parts)


# ========================================
# ========================================

def generate_embedding(text: str) -> Optional[List[float]]:
    """
    텍스트로부터 임베딩 벡터 생성

    Args:
        text: 임베딩할 텍스트

    Returns:
        1536차원 임베딩 벡터 또는 None (실패 시)
    """
    if not text or not text.strip():
        return None

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.strip()
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None


async def extract_important_memories(
    summary: str,
    state: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    요약으로부터 중요한 정보 추출 (LLM 사용)

    Args:
        summary: 대화 요약
        state: GraphState (컨텍스트)

    Returns:
        추출된 기억 리스트 [{"key": str, "value": str, "type": str, "importance": float}, ...]
    """
    if not summary:
        return []

    system_prompt = """당신은 대화 요약에서 중요한 정보를 추출하는 AI입니다.

다음 카테고리로 정보를 분류하고 추출해주세요:
1. character_preference: 캐릭터 선호도 (좋아하는/싫어하는 캐릭터)
2. user_fact: 사용자에 대한 사실 (이름, 직업, 취미 등)
3. game_progress: 게임 진행 상황 (완료한 미션, 선택, 성취)
4. relationship: 캐릭터와의 관계 변화
5. important_event: 중요한 사건이나 결정

각 정보는 다음 형식의 JSON 배열로 반환해주세요:
[
  {
    "key": "favorite_character",
    "value": "탄지로를 가장 좋아한다",
    "type": "character_preference",
    "importance": 0.8,
    "tags": ["character", "preference"]
  }
]

- key는 snake_case로 짧고 명확하게
- value는 완전한 문장으로
- importance는 0.0~1.0 (중요도)
- tags는 검색을 위한 키워드 리스트

중요한 정보만 추출하고, 너무 세부적이거나 일시적인 정보는 제외하세요."""

    user_prompt = f"""=== 시나리오 정보 ===
시나리오: {state.get('scenario_id', 'unknown')}
캐릭터: {state.get('active_character', 'unknown')}
사용자: {state.get('user_name', '사용자')}

=== 대화 요약 ===
{summary}

위 요약에서 중요한 정보를 추출해주세요."""

    try:
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content.strip()

        try:
            result = json.loads(content)
            # 배열 또는 객체 처리
            if isinstance(result, list):
                memories = result
            elif isinstance(result, dict) and 'memories' in result:
                memories = result['memories']
            else:
                memories = []

            return memories
        except json.JSONDecodeError:
            print(f"⚠️ Failed to parse memories JSON: {content}")
            return []

    except Exception as e:
        print(f"❌ Error extracting memories: {e}")
        return []


async def save_memories_to_db(
    db_manager,
    user_id: str,
    memories: List[Dict[str, Any]],
    session_id: str,
    scenario_id: str
):
    """
    추출된 기억을 user_memories 테이블에 저장

    Args:
        db_manager: DatabaseManager 인스턴스
        user_id: 사용자 ID
        memories: 추출된 기억 리스트
        session_id: 현재 세션 ID
        scenario_id: 시나리오 ID
    """
    if not memories:
        print("ℹ️  No memories to save")
        return

    print(f"💾 Saving {len(memories)} memories to database...")

    for memory in memories:
        try:
            memory_key = memory.get('key')
            memory_value = memory.get('value')
            memory_type = memory.get('type', 'fact')
            importance = memory.get('importance', 0.5)
            tags = memory.get('tags', [])

            if not memory_key or not memory_value:
                continue

            # 임베딩 생성
            embedding = generate_embedding(memory_value)

            # 컨텍스트 구성
            context = {
                "scenario_id": scenario_id,
                "extracted_from_session": session_id
            }

            # 데이터베이스에 저장
            memory_id = db_manager.create_or_update_memory(
                user_id=user_id,
                memory_key=memory_key,
                memory_value=memory_value,
                memory_type=memory_type,
                importance=importance,
                tags=tags,
                context=context,
                source_session_id=session_id,
                embedding=embedding
            )

            if memory_id:
                print(f"  ✅ Saved memory: {memory_key} (ID: {memory_id})")
            else:
                print(f"  ⚠️ Failed to save memory: {memory_key}")

        except Exception as e:
            print(f"  ❌ Error saving memory {memory.get('key')}: {e}")

    print(f"✅ Memory save complete")


async def process_conversation_for_memories(
    db_manager,
    user_id: str,
    session_id: str,
    state: Dict[str, Any],
    summary: str
):
    """
    대화 요약으로부터 기억 추출 및 저장 (메인 함수)

    Args:
        db_manager: DatabaseManager 인스턴스
        user_id: 사용자 ID
        session_id: 세션 ID
        state: GraphState
        summary: 대화 요약

    Returns:
        저장된 기억 개수
    """
    if not summary:
        return 0

    print("🧠 Processing conversation for long-term memories...")

    # 중요한 정보 추출
    memories = await extract_important_memories(summary, state)

    if not memories:
        print("ℹ️  No important memories extracted")
        return 0

    # 데이터베이스에 저장
    await save_memories_to_db(
        db_manager=db_manager,
        user_id=user_id,
        memories=memories,
        session_id=session_id,
        scenario_id=state.get('scenario_id', 'unknown')
    )

    return len(memories)
