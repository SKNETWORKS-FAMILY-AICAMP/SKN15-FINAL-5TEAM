"""
============================================================
🖼️ Dialogue Image Service
============================================================
대화 내용 기반 이미지 선택 서비스

주요 기능:
- 대화 내용에서 이벤트 감지
- DB 기반 최적 이미지 선택
- 이벤트 플래그 관리
"""
from typing import Dict, List, Any, Optional
import logging

from src.services.dialogue_event_detector_service import get_event_detector
from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DialogueImageService:
    """
    대화 내용 기반 이미지 선택 서비스

    이벤트 감지 + 이미지 매핑을 통합 처리
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Args:
            db_manager: DatabaseManager 인스턴스 (이미지 매핑용)
        """
        self.db_manager = db_manager
        self.event_detector = get_event_detector()

    def select_image_for_dialogue(
        self,
        state: Dict[str, Any],
        dialogues: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        대화 내용과 상태를 기반으로 최적의 이미지 선택 + 자동 획득

        Args:
            state: 게임 상태 (GraphState dict)
            dialogues: 대화 리스트 [{"speaker": "...", "text": "..."}, ...]

        Returns:
            선택된 이미지 경로 또는 None
        """
        if not self.db_manager:
            logger.debug("[DialogueImageService] No db_manager, skipping image selection")
            return None

        if not dialogues:
            logger.debug("[DialogueImageService] No dialogues, skipping image selection")
            return None

        # 1. 이벤트 감지
        detected_events = self._detect_events_from_dialogues(dialogues, state)

        # 2. 이벤트 플래그 업데이트
        self._update_event_flags(state, detected_events)

        # 3. 이미지 선택
        image_path = self._select_best_image(state)

        # 4. 이미지 자동 획득 (사용자 갤러리에 저장)
        if image_path:
            self._auto_unlock_image(state, image_path)

        return image_path

    def _detect_events_from_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[str]:
        """
        대화 내용에서 이벤트 감지

        Args:
            dialogues: 대화 리스트
            state: 게임 상태

        Returns:
            감지된 이벤트 플래그 리스트
        """
        try:
            detected_events = self.event_detector.detect_events(
                dialogues=dialogues,
                state=state
            )

            if detected_events:
                logger.info(f"[DialogueImageService] 🎯 Detected {len(detected_events)} events: {detected_events}")

            return detected_events

        except Exception as e:
            logger.error(f"[DialogueImageService] Event detection failed: {e}")
            return []

    def _update_event_flags(
        self,
        state: Dict[str, Any],
        new_events: List[str]
    ) -> None:
        """
        상태의 이벤트 플래그 업데이트 (중복 제거)

        Args:
            state: 게임 상태
            new_events: 새로 감지된 이벤트 리스트
        """
        if not new_events:
            return

        # 기존 플래그 가져오기
        existing_flags = state.get("event_flags", [])

        # 새로운 이벤트 추가 및 중복 제거
        combined_flags = existing_flags + new_events
        state["event_flags"] = list(set(combined_flags))

        logger.info(f"[DialogueImageService] 🏷️ Event flags updated: {state['event_flags']}")

    def _select_best_image(
        self,
        state: Dict[str, Any]
    ) -> Optional[str]:
        """
        DB를 통해 최적의 이미지 선택

        Args:
            state: 게임 상태

        Returns:
            선택된 이미지 경로 또는 None
        """
        try:
            scenario_id = state.get("scenario_id", "cutscene5_llm_driven")
            current_stage = state.get("current_stage", "INTRO")
            turn_count = state.get("turn_count", 0)
            dialogue_count = len(state.get("output", {}).get("dialogues", []))
            event_flags = state.get("event_flags", [])

            logger.debug(f"[DialogueImageService] Selecting image for {scenario_id}/{current_stage}")
            logger.debug(f"[DialogueImageService] Params: turn={turn_count}, dialogues={dialogue_count}, flags={event_flags}")

            # DB 쿼리
            image_info = self.db_manager.get_image_for_stage(
                scenario_id=scenario_id,
                stage_id=current_stage,
                turn_count=turn_count,
                dialogue_count=dialogue_count,
                event_flags=event_flags
            )

            if image_info:
                image_path = str(image_info.get("image_path") or image_info.get("index_number"))
                priority = image_info.get("priority", 0)

                logger.info(f"[DialogueImageService] 🖼️ Selected image: {image_path} (priority={priority})")
                return image_path
            else:
                logger.warning(f"[DialogueImageService] No image found for {scenario_id}/{current_stage}")
                return None

        except Exception as e:
            logger.error(f"[DialogueImageService] Image selection failed: {e}")
            return None

    def _auto_unlock_image(
        self,
        state: Dict[str, Any],
        image_path: str
    ) -> None:
        """
        이미지 자동 획득 처리 (사용자 갤러리에 저장)

        Args:
            state: 게임 상태
            image_path: 선택된 이미지 경로 또는 index_number
        """
        try:
            # 사용자 ID 가져오기
            user_id = state.get("user_id")
            if not user_id:
                logger.warning("[DialogueImageService] No user_id in state, skipping auto-unlock")
                return

            # 이미지 정보 가져오기 (image_path 또는 index_number로 조회)
            scenario_id = state.get("scenario_id", "cutscene5_llm_driven")

            # image_path가 숫자인 경우 (index_number)
            try:
                index_number = int(image_path)
                image_info = self.db_manager.get_image_by_index(scenario_id, index_number)
            except (ValueError, TypeError):
                # image_path가 문자열 경로인 경우
                image_info = self.db_manager.get_image_by_path(scenario_id, image_path)

            if not image_info:
                logger.warning(f"[DialogueImageService] Image not found: {image_path}")
                return

            image_id = image_info.get("image_id")
            if not image_id:
                logger.warning(f"[DialogueImageService] No image_id for path: {image_path}")
                return

            # 이미지 획득 처리
            session_id = state.get("session_id")
            current_stage = state.get("current_stage", "INTRO")

            was_unlocked = self.db_manager.unlock_image_for_user(
                user_id=user_id,
                image_id=image_id,
                scenario_id=scenario_id,
                session_id=session_id,
                stage_id=current_stage,
                unlock_method="story_progress"
            )

            if was_unlocked:
                logger.info(f"[DialogueImageService] 🎁 NEW IMAGE UNLOCKED: {image_path} for user {user_id}")
            else:
                logger.debug(f"[DialogueImageService] Image already unlocked: {image_path}")

        except Exception as e:
            logger.error(f"[DialogueImageService] Auto-unlock failed: {e}")


# ============================================================
# 싱글톤 팩토리 (선택적)
# ============================================================
_service_instance_cache: Dict[int, DialogueImageService] = {}


def get_dialogue_image_service(db_manager: Optional[DatabaseManager] = None) -> DialogueImageService:
    """
    DialogueImageService 인스턴스 반환 (캐시 사용)

    Args:
        db_manager: DatabaseManager 인스턴스

    Returns:
        DialogueImageService 인스턴스
    """
    # db_manager의 id를 키로 사용 (같은 db_manager면 재사용)
    cache_key = id(db_manager) if db_manager else 0

    if cache_key not in _service_instance_cache:
        _service_instance_cache[cache_key] = DialogueImageService(db_manager=db_manager)

    return _service_instance_cache[cache_key]
