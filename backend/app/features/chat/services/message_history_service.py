"""
Message History Service
대화 히스토리 로딩 및 관리 유틸리티

Features:
- DB에서 message_history 로드 (dialogues + user_inputs 통합)
- 최근 N개 메시지 선택
- 중복 로직 통합 (usecase.py:596-653 + context_service)
"""
from typing import List, Dict, Any, Optional
from app.core.logging import get_parent_logger
from app.features.chat.repositories import DialogueRepository
from app.features.progression.repository import ProgressionRepository

logger = get_parent_logger("MessageHistoryService")


class MessageHistoryService:
    """
    대화 히스토리 관리 서비스

    책임:
    - DB에서 dialogues + user_inputs 통합 로딩
    - 턴 번호 기준 정렬
    - 최근 N개 메시지 선택
    """

    def __init__(
        self,
        dialogue_repository: Optional[DialogueRepository] = None,
        progression_repository: Optional[ProgressionRepository] = None
    ):
        """
        Args:
            dialogue_repository: Dialogue Repository (optional - required only for load_full_message_history)
            progression_repository: Progression Repository (optional - required only for load_full_message_history)
        """
        # Repository는 lazy initialization으로 변경 (singleton에서 DB 없이 생성 가능하도록)
        self.dialogue_repository = dialogue_repository
        self.progression_repository = progression_repository

        logger.info("__init__", "MessageHistoryService initialized")

    async def load_full_message_history(
        self,
        session_id: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        DB에서 전체 message_history 로드 (dialogues + user_inputs 통합)

        Args:
            session_id: 세션 ID
            limit: 최대 로드 개수 (기본 500개, 약 125턴)

        Returns:
            message_history (턴 번호 기준 정렬)
        """
        # Repository 체크 (이 메서드는 DB 접근이 필요함)
        if not self.dialogue_repository or not self.progression_repository:
            raise RuntimeError("MessageHistoryService: dialogue_repository and progression_repository are required for load_full_message_history()")

        # 1. DB에서 로드
        recent_dialogues = await self.dialogue_repository.get_recent_dialogues(session_id, limit=limit)
        recent_user_inputs = await self.progression_repository.get_user_inputs(session_id, limit=limit)

        # 2. 대화와 유저 입력을 턴 번호 기준으로 통합
        message_history = []

        # 턴 번호별 stage_tag 매핑 (NPC 대화에서 추출)
        stage_tag_by_turn = {}
        for dlg in recent_dialogues:
            if dlg.stage_tag and dlg.turn_number not in stage_tag_by_turn:
                stage_tag_by_turn[dlg.turn_number] = dlg.stage_tag

        # 유저 입력을 턴 번호별로 매핑
        user_inputs_by_turn = {}
        for user_input in recent_user_inputs:
            user_inputs_by_turn[user_input.turn_number] = user_input.user_input

        # 턴 번호별로 정렬하기 위해 모든 메시지를 수집
        all_messages = []

        # NPC 대화 추가
        for dlg in recent_dialogues:
            all_messages.append({
                "speaker": dlg.speaker,
                "text": dlg.content,
                "emotion": dlg.emotion or "neutral",
                "turn": dlg.turn_number,
                "stage_tag": dlg.stage_tag,
                "order": dlg.turn_number * 100 + (dlg.order_index or 0) + 1  # 유저 입력 뒤에 배치
            })

        # 유저 입력 추가 (같은 턴의 NPC 대화에서 stage_tag 추론)
        for turn_num, user_text in user_inputs_by_turn.items():
            all_messages.append({
                "speaker": "{{user}}",  # ✅ 플레이스홀더 사용 (LLM 프롬프트용)
                "text": user_text,
                "emotion": "neutral",
                "turn": turn_num,
                "stage_tag": stage_tag_by_turn.get(turn_num),  # ✅ 같은 턴의 stage_tag 사용
                "order": turn_num * 100  # 해당 턴의 NPC 대화보다 먼저 배치
            })

        # 턴 번호와 order로 정렬
        all_messages.sort(key=lambda x: x["order"])

        # order 필드 제거하고 message_history에 추가
        for msg in all_messages:
            del msg["order"]
            message_history.append(msg)

        logger.info("load_full_message_history",
                   f"Loaded {len(message_history)} messages (dialogues={len(recent_dialogues)}, user_inputs={len(recent_user_inputs)})",
                   session_id=session_id)

        return message_history

    def select_recent_messages(
        self,
        message_history: List[Dict[str, Any]],
        keep_count: int = 8
    ) -> List[Dict[str, Any]]:
        """
        message_history에서 최근 N개만 선택

        Args:
            message_history: 전체 메시지 히스토리
            keep_count: 유지할 메시지 개수 (기본 8개, 약 2턴)

        Returns:
            최근 N개 메시지
        """
        if not isinstance(message_history, list) or not message_history:
            return []

        # 최근 N개만 선택
        recent_messages = message_history[-keep_count:] if len(message_history) > keep_count else message_history

        logger.info("select_recent_messages",
                   f"Selected {len(recent_messages)} recent messages (from total {len(message_history)})")

        # dict 형태로 반환 (PromptService와 호환)
        result = []
        for entry in recent_messages:
            if not isinstance(entry, dict):
                continue

            speaker = entry.get("speaker", "unknown")
            text = (entry.get("text") or "").strip()
            if text:
                result.append({"speaker": speaker, "text": text})

        return result


# 싱글톤 인스턴스
_service_instance = None


def get_message_history_service() -> MessageHistoryService:
    """MessageHistoryService 싱글톤"""
    global _service_instance
    if _service_instance is None:
        _service_instance = MessageHistoryService()
    return _service_instance
