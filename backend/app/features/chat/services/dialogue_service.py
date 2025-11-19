"""
Dialogue Service - 대화 검증, 수정, 정규화, 이벤트 감지 통합 서비스

Features:
- LLM 기반 대사 검증
- 대사 자동 수정
- 대사 정규화 및 렌더링 (변수 치환)
- 키워드 기반 이벤트 감지
- 이벤트 기반 이미지 선택

Combines 5 services:
1. DialogueValidationService - 대사 검증
2. DialogueCorrectionService - 대사 수정
3. DialogueFormatterService - 대사 포맷팅
4. DialogueEventDetectorService - 이벤트 감지
5. DialogueImageService - 이미지 선택
"""
import re
import json
from typing import List, Dict, Any, Optional

from app.core.config import get_settings
from app.core.llm.client import LLMClient
from app.core.logging import get_parent_logger

settings = get_settings()
logger = get_parent_logger("DialogueService")


# 이벤트 감지 키워드 매핑
EVENT_KEYWORDS = {
    # 캐릭터 등장
    "아카자": "akaza_appeared",
    "렌고쿠": "rengoku_appeared",
    "탄지로": "tanjiro_appeared",
    "젠이츠": "zenitsu_appeared",
    "이노스케": "inosuke_appeared",
    "네즈코": "nezuko_appeared",

    # 전투
    "전투 시작": "battle_started",
    "공격": "combat_action",
    "방어": "combat_action",
    "승리": "victory_moment",
    "패배": "defeat_moment",

    # 감정
    "희생": "sacrifice_moment",
    "눈물": "emotional_moment",
    "슬픔": "sad_moment",
    "분노": "anger_moment",

    # 스토리
    "설득": "persuasion_attempt",
    "비밀": "secret_revealed",
    "발견": "discovery_moment",
}


class DialogueService:
    """
    대화 처리 통합 서비스 (Layer 3 - Service)

    Features:
    - validate_dialogue(): 대사 검증 (LLM/규칙)
    - correct_dialogue(): 검증 실패 시 자동 수정
    - format_dialogue(): 대사 정규화 (변수 치환)
    - detect_events(): 키워드 기반 이벤트 감지
    - select_image(): 이벤트 기반 이미지 선택

    Example:
        service = DialogueService(llm_client=llm)

        # 검증
        result = await service.validate_dialogue(
            dialogue_text="탄지로가 외친다",
            speaker="tanjiro",
            state=state
        )

        # 수정
        if not result["passed"]:
            corrected = await service.correct_dialogue(
                dialogue_text="원본",
                speaker="tanjiro",
                validation_result=result,
                state=state
            )

        # 이벤트 감지
        events = service.detect_events(
            dialogues=[{"speaker": "tanjiro", "text": "..."}],
            state=state
        )
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        enable_llm: bool = True,
        chat_repository: Optional[Any] = None
    ):
        """
        Args:
            llm_client: LLM 클라이언트
            enable_llm: LLM 사용 여부
            chat_repository: ChatRepository (이미지 조회용, 선택적)
        """
        self.llm_client = llm_client or LLMClient()
        self.enable_llm = enable_llm
        self.chat_repository = chat_repository

    # ========== 1. Validation ==========

    async def validate_dialogue(
        self,
        dialogue_text: str,
        speaker: str,
        state: Dict[str, Any],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        대사 검증

        Args:
            dialogue_text: 검증할 대사
            speaker: 화자
            state: 게임 상태
            use_llm: LLM 사용 여부

        Returns:
            {
                "passed": bool,
                "total_score": float,
                "scores": {...},
                "issues": [...],
                "suggestions": str
            }
        """
        logger.debug("validate_dialogue", "Validating dialogue",
                    speaker=speaker,
                    use_llm=use_llm)

        if use_llm and self.enable_llm:
            result = await self._validate_with_llm(dialogue_text, speaker, state)
            if result:
                return result

        # Fallback: 규칙 기반 검증
        return self._validate_with_rules(dialogue_text, speaker, state)

    async def _validate_with_llm(
        self,
        dialogue_text: str,
        speaker: str,
        state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """LLM 기반 대사 검증"""
        try:
            system_prompt = """당신은 대사 검증 전문가입니다.

대사를 다음 기준으로 평가하세요:
1. character_consistency: 캐릭터 성격과 말투의 일관성 (0-100)
2. context_relevance: 게임 상황과 문맥 적합성 (0-100)
3. emotional_appropriateness: 감정 표현의 적절성 (0-100)
4. game_rule_compliance: 게임 규칙 준수 (0-100)

JSON 형식으로 응답:
{{
  "scores": {{
    "character_consistency": 점수,
    "context_relevance": 점수,
    "emotional_appropriateness": 점수,
    "game_rule_compliance": 점수
  }},
  "total_score": 전체점수,
  "passed": true/false,
  "issues": ["문제점1", ...],
  "suggestions": "개선 제안"
}}"""

            current_scene = state.get("current_stage", "unknown")
            scenario_id = state.get("scenario_id", "unknown")

            user_prompt = f"""캐릭터: {speaker}
현재 씬: {current_scene}
시나리오: {scenario_id}

대사: "{dialogue_text}"

위 대사를 평가하세요."""

            response_text = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300
            )

            result = json.loads(response_text)

            logger.info("_validate_with_llm", "Validation complete",
                       passed=result.get("passed"),
                       score=result.get("total_score"))

            return result

        except Exception as e:
            logger.error("_validate_with_llm", f"LLM validation failed: {e}")
            return None

    def _validate_with_rules(
        self,
        dialogue_text: str,
        speaker: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """규칙 기반 대사 검증 (fallback)"""
        # 간단한 규칙 기반 검증
        passed = True
        issues = []

        # 대사 길이 체크
        if len(dialogue_text) > 500:
            passed = False
            issues.append("대사가 너무 깁니다")

        if len(dialogue_text) < 3:
            passed = False
            issues.append("대사가 너무 짧습니다")

        return {
            "passed": passed,
            "total_score": 80.0 if passed else 50.0,
            "scores": {
                "character_consistency": 80,
                "context_relevance": 80,
                "emotional_appropriateness": 80,
                "game_rule_compliance": 80
            },
            "issues": issues,
            "suggestions": "규칙 기반 검증 완료"
        }

    # ========== 2. Correction ==========

    async def correct_dialogue(
        self,
        dialogue_text: str,
        speaker: str,
        validation_result: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Optional[str]:
        """
        대사 자동 수정

        Args:
            dialogue_text: 원본 대사
            speaker: 화자
            validation_result: 검증 결과
            state: 게임 상태

        Returns:
            수정된 대사 또는 None
        """
        if not self.enable_llm:
            return None

        try:
            issues = validation_result.get("issues", [])
            suggestions = validation_result.get("suggestions", "대사를 상황에 맞게 다듬어 주세요.")

            issues_block = "\n".join(f"- {issue}" for issue in issues) if issues else "- 자연스럽게 다듬어 주세요."

            system_prompt = f"""당신은 대사 수정 전문가입니다.

화자: {speaker}

문제점:
{issues_block}

개선 제안: {suggestions}

원본 대사를 위 피드백을 반영하여 수정하세요."""

            user_prompt = f"""원본 대사: "{dialogue_text}"

수정된 대사만 출력하세요 (따옴표 없이):"""

            corrected_text = await self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=100
            )

            corrected = corrected_text.strip().strip('"').strip("'")

            logger.info("correct_dialogue", "Dialogue corrected",
                       speaker=speaker,
                       original_len=len(dialogue_text),
                       corrected_len=len(corrected))

            return corrected

        except Exception as e:
            logger.error("correct_dialogue", f"Correction failed: {e}")
            return None

    # ========== 3. Formatting & Normalization ==========

    def format_dialogues(
        self,
        entries: List[Any],
        state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        대사 정규화 및 렌더링 (변수 치환)

        Args:
            entries: 다양한 형식의 대사 리스트
            state: 게임 상태 (user_name 등)

        Returns:
            정규화된 대사 리스트 [{"speaker": "...", "text": "...", "fx": ...}, ...]
        """
        normalized = self._normalize_dialogues(entries)
        rendered = self._render_dialogues(state, normalized)

        logger.debug("format_dialogues", "Dialogues formatted",
                    input_count=len(entries),
                    output_count=len(rendered))

        return rendered

    def _normalize_dialogues(self, entries: List[Any]) -> List[Dict[str, Any]]:
        """다양한 형식을 표준 형식으로 정규화"""
        normalized: List[Dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("line")
                    or entry.get("goal")
                    or entry.get("description")
                )
                speaker = entry.get("speaker")
                if not speaker:
                    hints = entry.get("speaker_hint")
                    if isinstance(hints, list) and hints:
                        speaker = hints[0]

                # goal에서 따옴표 안의 대사 추출
                if not entry.get("text") and text:
                    text = self._extract_dialogue_from_goal(text, speaker or "narr")

                normalized.append({
                    "speaker": (speaker or "narr"),
                    "text": text or json.dumps(entry, ensure_ascii=False),
                    "fx": entry.get("fx"),
                })
            else:
                normalized.append({"speaker": "narr", "text": str(entry)})

        return normalized

    def _extract_dialogue_from_goal(self, goal: str, speaker: str) -> str:
        """goal 텍스트에서 따옴표 안의 대사 추출"""
        quotes_pattern = r"['\"\「]([^'\"」]+)['\"\」]"
        matches = re.findall(quotes_pattern, goal)

        if matches:
            dialogue = " ".join(matches)

            # narr인 경우 goal 전체 사용
            if speaker == "narr":
                cleaned = re.sub(r"【[^】]+】\s*", "", goal)
                return cleaned.strip()

            return dialogue.strip()

        return goal

    def _render_dialogues(
        self,
        state: Dict[str, Any],
        entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """대사 리스트 렌더링 (변수 치환)"""
        rendered: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # 텍스트 치환
            text = entry.get("text")
            if isinstance(text, str):
                entry["text"] = self._render_text(state, text)
            # 화자 이름 치환 (예: {user} → 츠구코)
            speaker = entry.get("speaker")
            if isinstance(speaker, str):
                entry["speaker"] = self._render_text(state, speaker)
            rendered.append(entry)
        return rendered

    def _render_text(self, state: Dict[str, Any], text: str) -> str:
        """플레이어 이름 등 변수 치환"""
        user_name = (
            state.get("user_name")
            or (state.get("temp_data") or {}).get("user_name")
            or "츠구코"
        )

        replacements = {
            "{user}": user_name,
            "{user_name}": user_name,
            "{{user}}": user_name,
        }

        result = text
        for token, value in replacements.items():
            result = result.replace(token, value)

        return result

    # ========== 4. Event Detection ==========

    def detect_events(
        self,
        dialogues: List[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> List[str]:
        """
        대화에서 이벤트 감지 (키워드 기반)

        Args:
            dialogues: 대화 리스트 [{"speaker": "...", "text": "..."}, ...]
            state: 게임 상태

        Returns:
            감지된 이벤트 플래그 리스트
        """
        detected = set()

        for dialogue in dialogues:
            text = dialogue.get("text", "")
            speaker = dialogue.get("speaker", "")

            # 키워드 매칭
            for keyword, event_flag in EVENT_KEYWORDS.items():
                if keyword in text or keyword in speaker:
                    detected.add(event_flag)

        events = list(detected)

        if events:
            logger.info("detect_events", f"Events detected: {events}")

        return events

    # ========== 5. Image Selection ==========

    async def select_image(
        self,
        state: Dict[str, Any],
        detected_events: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        스테이지 기반 이미지 선택 (DB 조회)

        state에서 scenario_id, current_stage, turn_count를 추출하여
        DB에서 최적의 이미지를 조회합니다.

        Args:
            state: 게임 상태 (scenario_id, current_stage, turn_count 포함)
            detected_events: 감지된 이벤트 (호환성 유지용, 사용 안 함)

        Returns:
            이미지 URL/경로 또는 None
        """
        # DB 기반 조회 (ChatRepository 사용)
        if self.chat_repository:
            scenario_id = state.get("scenario_id")
            stage_id = state.get("current_stage") or state.get("stage_tag")
            turn_count = state.get("turn_count", 0)

            if scenario_id and stage_id:
                try:
                    image_data = await self.chat_repository.get_best_image_for_stage(
                        scenario_id=scenario_id,
                        stage_id=stage_id,
                        turn_count=turn_count
                    )

                    if image_data:
                        image_url = image_data.get("image_url")
                        logger.info("select_image",
                                   f"Image selected from DB: {image_url}",
                                   scenario=scenario_id,
                                   stage=stage_id,
                                   priority=image_data.get("priority"))
                        return image_url
                    else:
                        logger.warning("select_image",
                                      f"No image found in DB for scenario={scenario_id}, stage={stage_id}")
                except Exception as e:
                    logger.error("select_image",
                                f"Error fetching image from DB: {e}",
                                exc_info=True)

        # Fallback: 이벤트 기반 하드코딩 매핑 (하위 호환성)
        events = detected_events or state.get("event_flags", [])
        event_image_mapping = {
            "battle_started": "battle_scene.jpg",
            "victory_moment": "victory.jpg",
            "emotional_moment": "emotional.jpg",
        }

        for event in events:
            if event in event_image_mapping:
                image_path = event_image_mapping[event]
                logger.info("select_image",
                           f"Image selected from fallback mapping: {image_path}",
                           event=event)
                return image_path

        return None


__all__ = ["DialogueService"]
