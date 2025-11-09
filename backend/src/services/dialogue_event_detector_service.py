"""
============================================================
💡 Dialogue Event Detector Service
============================================================
대화 내용을 분석하여 스토리 이벤트를 자동으로 감지하는 서비스

주요 기능:
- 키워드 기반 이벤트 감지 (빠르고 정확)
- 캐릭터 등장 감지
- 주요 스토리 포인트 감지
- 감정적 순간 감지
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DialogueEventDetectorService:
    """
    대화 내용에서 스토리 이벤트를 감지하는 서비스

    현재는 키워드 기반 감지만 지원
    향후 LLM 기반 감지 추가 가능
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: LLM 기반 감지 사용 여부 (현재 미지원)
        """
        self.use_llm = use_llm
        self.keyword_rules = self._initialize_keyword_rules()

    def _initialize_keyword_rules(self) -> Dict[str, str]:
        """
        키워드 → 이벤트 플래그 매핑 규칙 정의

        Returns:
            Dict[keyword, event_flag]
        """
        return {
            # ============================================================
            # 캐릭터 등장 (Character Appearances)
            # ============================================================
            "아카자": "akaza_appeared",
            "akaza": "akaza_appeared",
            "렌고쿠": "rengoku_appeared",
            "rengoku": "rengoku_appeared",
            "쿄쥬로": "rengoku_appeared",
            "탄지로": "tanjiro_appeared",
            "tanjiro": "tanjiro_appeared",
            "젠이츠": "zenitsu_appeared",
            "zenitsu": "zenitsu_appeared",
            "이노스케": "inosuke_appeared",
            "inosuke": "inosuke_appeared",
            "네즈코": "nezuko_appeared",
            "nezuko": "nezuko_appeared",

            # ============================================================
            # 전투 이벤트 (Combat Events)
            # ============================================================
            "전투 시작": "battle_started",
            "싸움 시작": "battle_started",
            "공격": "combat_action",
            "방어": "combat_action",
            "전투": "battle_ongoing",
            "싸우": "battle_ongoing",
            "결투": "battle_started",
            "승리": "victory_moment",
            "패배": "defeat_moment",
            "도망": "retreat_event",

            # ============================================================
            # 감정적 순간 (Emotional Moments)
            # ============================================================
            "희생": "sacrifice_moment",
            "죽음": "death_event",
            "사망": "death_event",
            "눈물": "emotional_moment",
            "슬픔": "sad_moment",
            "기쁨": "happy_moment",
            "분노": "anger_moment",
            "절망": "despair_moment",
            "희망": "hope_moment",
            "재회": "reunion_moment",

            # ============================================================
            # 스토리 포인트 (Story Points)
            # ============================================================
            "설득": "persuasion_attempt",
            "설득 성공": "persuasion_successful",
            "설득 실패": "persuasion_failed",
            "동맹": "alliance_formed",
            "배신": "betrayal_revealed",
            "비밀": "secret_revealed",
            "발견": "discovery_moment",
            "도시락": "eating_moment",
            "먹": "eating_moment",

            # ============================================================
            # 무한열차 특화 이벤트 (Mugen Train Specific)
            # ============================================================
            "무한열차": "train_mentioned",
            "열차": "train_mentioned",
            "객차": "cabin_scene",
            "꿈": "dream_sequence",
            "악몽": "nightmare_sequence",
            "잠": "sleep_event",

            # ============================================================
            # 선택 및 분기 (Choices & Branching)
            # ============================================================
            "선택": "choice_presented",
            "결정": "decision_made",
            "갈림길": "fork_point",
        }

    def detect_events(
        self,
        dialogues: List[Dict[str, Any]],
        state: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        대화 내용에서 이벤트를 감지

        Args:
            dialogues: 대화 리스트 [{"speaker": "...", "text": "..."}, ...]
            state: 게임 상태 (선택적, 상태 기반 감지에 사용)

        Returns:
            감지된 이벤트 플래그 리스트 (예: ["akaza_appeared", "battle_started"])
        """
        if not dialogues:
            return []

        # 1. 키워드 기반 감지
        events = self._detect_by_keywords(dialogues)

        # 2. 상태 기반 감지 (선택적)
        if state:
            state_events = self._detect_from_state(state)
            events.extend(state_events)

        # 3. 중복 제거
        unique_events = list(set(events))

        if unique_events:
            logger.info(f"[EventDetector] Detected {len(unique_events)} events: {unique_events}")

        return unique_events

    def _detect_by_keywords(self, dialogues: List[Dict[str, Any]]) -> List[str]:
        """
        키워드 매칭을 통한 이벤트 감지

        Args:
            dialogues: 대화 리스트

        Returns:
            감지된 이벤트 플래그 리스트
        """
        detected_events = []

        # 모든 대화를 하나의 텍스트로 합침
        all_text = " ".join([
            d.get("text", "") for d in dialogues
            if isinstance(d, dict) and d.get("text")
        ])

        # 키워드 매칭
        for keyword, event_flag in self.keyword_rules.items():
            if keyword in all_text:
                detected_events.append(event_flag)
                logger.debug(f"[EventDetector] Keyword '{keyword}' → flag '{event_flag}'")

        return detected_events

    def _detect_from_state(self, state: Dict[str, Any]) -> List[str]:
        """
        게임 상태 변화를 통한 이벤트 감지

        Args:
            state: 게임 상태

        Returns:
            감지된 이벤트 플래그 리스트
        """
        detected_events = []

        # 스테이지 변화 감지
        current_stage = state.get("current_stage", "")
        if "BATTLE" in current_stage.upper():
            detected_events.append("battle_stage")
        elif "RECRUIT" in current_stage.upper():
            detected_events.append("recruit_stage")
        elif "ENDING" in current_stage.upper():
            detected_events.append("ending_stage")

        # 설득 성공 감지
        allies_recruited = state.get("allies_recruited", [])
        if allies_recruited:
            detected_events.append("allies_recruited")
            if len(allies_recruited) >= 3:
                detected_events.append("full_party_recruited")

        # 엔딩 도달 감지
        if state.get("is_ended"):
            detected_events.append("story_ended")

        return detected_events

    def add_keyword_rule(self, keyword: str, event_flag: str):
        """
        런타임에 키워드 규칙 추가

        Args:
            keyword: 감지할 키워드
            event_flag: 설정할 이벤트 플래그
        """
        self.keyword_rules[keyword] = event_flag
        logger.info(f"[EventDetector] Added rule: '{keyword}' → '{event_flag}'")

    def remove_keyword_rule(self, keyword: str):
        """
        키워드 규칙 제거

        Args:
            keyword: 제거할 키워드
        """
        if keyword in self.keyword_rules:
            del self.keyword_rules[keyword]
            logger.info(f"[EventDetector] Removed rule: '{keyword}'")


# ============================================================
# 싱글톤 인스턴스 (재사용)
# ============================================================
_event_detector_instance = None


def get_event_detector() -> DialogueEventDetectorService:
    """
    이벤트 감지 서비스 싱글톤 인스턴스 반환

    Returns:
        DialogueEventDetectorService 인스턴스
    """
    global _event_detector_instance

    if _event_detector_instance is None:
        _event_detector_instance = DialogueEventDetectorService()

    return _event_detector_instance
