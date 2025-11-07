"""
FastAPI Background Tasks for Async Data Processing

응답 속도와 데이터 수집을 모두 달성하기 위한 비동기 작업 처리 모듈
"""
import os
from typing import Dict, Any, Optional, List
from src.domain.models.conversation import ConversationTurn, Dialogue
from src.core.utils.logger import log


def process_training_data_async(
    state: Dict[str, Any],
    model_output: Dict[str, Any],
    agent_name: str,
    llm_model: Optional[str] = None,
    start_time: Optional[float] = None,
) -> None:
    """
    백그라운드에서 Training Logger 처리

    사용자에게 응답을 즉시 반환한 후, 백그라운드에서 학습 데이터를 처리합니다.
    - Entity extraction
    - Embedding generation
    - LLM-based labeling
    """
    # Training Logger가 비활성화되어 있으면 즉시 리턴
    if os.getenv("TRAINING_LOGGER_ENABLED", "false").lower() != "true":
        return

    try:
        from src.core.utils.tools.training_logger import log_agent

        # 백그라운드에서 Training Logger 실행
        log_agent(
            agent_name=agent_name,
            state=state,
            model_output=model_output,
            start_time=start_time,
            llm_model=llm_model,
        )

        log("background_tasks", f"✅ Training data processed for {agent_name}")

    except Exception as e:
        # 백그라운드 작업 실패는 로깅만 하고 에러 발생시키지 않음
        log("background_tasks", f"❌ Training data processing failed for {agent_name}: {e}")


def process_entity_extraction_async(
    session_id: str,
    log_id: int,
    user_input: str,
    context: Dict[str, Any],
) -> None:
    """
    백그라운드에서 Entity Extraction 및 Embedding 생성

    가장 느린 작업을 백그라운드로 처리하여 응답 속도 향상
    """
    # Entity extraction이 비활성화되어 있으면 즉시 리턴
    if os.getenv("ENTITY_EXTRACTION_ENABLED", "false").lower() != "true":
        return

    try:
        from src.core.utils.entity_extractor import EntityExtractor
        from src.core.utils.embedding_matcher import EmbeddingClient
        from src.infrastructure.database.db_manager import DatabaseManager

        # Entity Extractor 초기화
        entity_extractor = EntityExtractor()
        embedding_client = EmbeddingClient()
        db_manager = DatabaseManager()

        # Entity extraction 수행
        entities = entity_extractor.extract_entities(
            text=user_input,
            context=context,
        )

        # Embedding 생성 및 DB 저장
        embedding_text = f"{user_input}"
        if context.get("history"):
            recent_history = context["history"][-2:]
            history_text = " ".join([h for h in recent_history if isinstance(h, str)])
            embedding_text = f"{history_text} {embedding_text}"

        embedding = embedding_client.embed(embedding_text)

        # Entity 저장
        entity_ids = []
        for entity in entities:
            entity_embedding_text = f"{entity.entity_type}: {entity.entity_name}"
            if entity.description:
                entity_embedding_text += f" - {entity.description}"

            entity_embedding = embedding_client.embed(entity_embedding_text)

            # Entity DB 저장 (upsert)
            entity_id = db_manager.save_or_update_entity(
                entity_name=entity.entity_name,
                entity_type=entity.entity_type,
                description=entity.description,
                properties=entity.properties,
                embedding=entity_embedding,
                importance_score=entity.confidence,
            )

            if entity_id:
                entity_ids.append(entity_id)

        # Training log 업데이트
        if embedding or entity_ids:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE training_logs
                SET embedding = %s,
                    mentioned_entity_ids = %s
                WHERE id = %s
            """, (embedding, entity_ids, log_id))
            conn.commit()
            cursor.close()
            conn.close()

        log("background_tasks", f"✅ Entity extraction completed: {len(entities)} entities for log {log_id}")

    except Exception as e:
        log("background_tasks", f"❌ Entity extraction failed for log {log_id}: {e}")


def process_conversation_summary_async(
    session_id: str,
    turn_count: int,
) -> None:
    """
    백그라운드에서 대화 요약 생성

    10턴마다 실행되는 요약 생성을 백그라운드로 처리
    """
    if turn_count % 10 != 0:
        return

    try:
        from src.infrastructure.database.db_manager import DatabaseManager
        from src.core.utils.conversation_summarizer import update_conversation_summary

        db_manager = DatabaseManager()

        # 대화 내역 조회
        dialogues = db_manager.get_session_dialogues(session_id)

        if not dialogues or len(dialogues) == 0:
            log("background_tasks", f"⚠️ No dialogues found for session {session_id}")
            return

        # message_history 형식으로 변환
        message_history: List[ConversationTurn] = []
        turn_map: Dict[int, ConversationTurn] = {}

        for dlg in dialogues:
            turn = dlg["turn_number"]
            speaker = dlg["speaker"]
            content = dlg["content"]

            if turn not in turn_map:
                turn_map[turn] = ConversationTurn(
                    turn_number=turn,
                    user_input="",
                    agent_responses=[]
                )

            current_turn = turn_map[turn]

            if speaker == "user":
                current_turn.user_input = content
            else:
                current_turn.agent_responses.append(Dialogue(
                    speaker=speaker,
                    content=content
                ))
    
        message_history = sorted(turn_map.values(), key=lambda t: t.turn_number)

        # 요약 생성 (비동기)
        import asyncio

        async def generate_summary():
            # State 준비
            state = {"session_id": session_id}
            summary_result = await update_conversation_summary(
                state=state,
                message_history=message_history
            )
            return summary_result

        # 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate_summary())
        loop.close()

        log("background_tasks", f"✅ Conversation summary generated for session {session_id} at turn {turn_count}")

    except Exception as e:
        log("background_tasks", f"❌ Conversation summary failed for session {session_id}: {e}")
