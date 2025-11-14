"""
Prompt Service - YAML 기반 프롬프트 관리 서비스 (Layer 4)

Features:
- prompts.yaml 로드 및 캐싱
- 템플릿 변수 치환
- 프롬프트 빌더 패턴
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.logging import get_parent_logger

logger = get_parent_logger("PromptService")


class PromptService:
    """
    프롬프트 관리 서비스 (Layer 4 - Service)

    책임:
    - prompts.yaml 파일 로드
    - 프롬프트 템플릿 관리
    - 변수 치환

    금지:
    - DB 접근
    - 비즈니스 로직
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: prompts.yaml 파일 경로 (None이면 기본 경로 사용)
        """
        if config_path is None:
            # 기본 경로: backend/configs/prompts.yaml
            # From /app/app/core/llm/prompt_service.py → /app/configs/prompts.yaml
            base_dir = Path(__file__).parent.parent.parent.parent
            config_path = base_dir / "configs" / "prompts.yaml"

        self.config_path = Path(config_path)
        self.prompts: Dict[str, Any] = {}
        self._load_prompts()

        logger.info("__init__", f"PromptService initialized from {self.config_path}")

    def _load_prompts(self):
        """prompts.yaml 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.prompts = data.get("llm_prompts", {})

            logger.info("_load_prompts", f"Loaded {len(self.prompts)} prompt categories")
        except FileNotFoundError:
            logger.error("_load_prompts", f"Prompts file not found: {self.config_path}")
            self.prompts = {}
        except Exception as e:
            logger.error("_load_prompts", f"Failed to load prompts: {e}", exc_info=True)
            self.prompts = {}

    def get_dialogue_generation_prompt(
        self,
        beats_description: str,
        speaker_pool: list,
        user_input: str,
        recent_dialogues: list,
        current_turn: int = 0,
        max_turns: int = 10,
        tone_profile: Optional[str] = None,
        atmosphere: Optional[str] = None,
        scene_setting: Optional[str] = None,
        previous_scene_summary: Optional[str] = None,
        previous_emotion_tone: Optional[str] = None,
        spatial_continuity: Optional[str] = None,
        character_states: Optional[str] = None,
        transition_hint: Optional[str] = None,
        world_context: Optional[str] = None
        long_term_memories: Optional[list] = None
    ) -> str:
        """
        children.dialogue_generation 프롬프트 생성

        Args:
            beats_description: Beat 설명 (상황 요약)
            speaker_pool: 등장 캐릭터 목록
            user_input: 사용자 입력
            recent_dialogues: 최근 대화 내역
            current_turn: 현재 턴 번호
            max_turns: 최대 턴 수
            tone_profile: 캐릭터 톤 프로필
            atmosphere: 분위기 (1-3단계)
            scene_setting: 장면 설정
            previous_scene_summary: 이전 장면 요약
            previous_emotion_tone: 이전 감정 톤
            spatial_continuity: 공간 연속성
            character_states: 캐릭터 상태
            transition_hint: 전환 힌트
            world_context: 세계관 설정 (YAML에서 로드)
            long_term_memories: 장기 기억 목록

        Returns:
            완성된 프롬프트
        """
        template = self.prompts.get("children", {}).get("dialogue_generation", "")

        if not template:
            logger.warning("get_dialogue_generation_prompt", "dialogue_generation prompt not found in YAML")
            return self._get_fallback_prompt(beats_description, speaker_pool, user_input)

        # 최근 대화 포맷팅
        recent_history = self._format_recent_dialogues(recent_dialogues)
        logger.debug("get_dialogue_generation_prompt",
                    f"🔍 DEBUG: Formatted recent_history length = {len(recent_history)} chars")

        # 장기 기억 포맷팅
        formatted_memories = self._format_long_term_memories(long_term_memories)
        logger.debug("get_dialogue_generation_prompt",
                    f"🔍 DEBUG: Formatted {len(long_term_memories or [])} long-term memories")

        # 변수 치환을 위한 컨텍스트 준비
        context = {
            "상황 요약": beats_description,
            "speaker_pool": ", ".join(speaker_pool),
            "사용자 입력": user_input or "(없음)",
            "최근 대화": recent_history or "(없음)",
            "장기 기억": formatted_memories,
            "현재 턴": str(current_turn),
            "max_turns": str(max_turns),
            "tone_profile": tone_profile or "(제공되지 않음)",
            "atmosphere": atmosphere or "2 (보통)",
            "장면 설정": scene_setting or "(제공되지 않음)",
            "이전 장면 요약": previous_scene_summary or "(제공되지 않음)",
            "이전 감정 톤": previous_emotion_tone or "(제공되지 않음)",
            "공간 연속성": spatial_continuity or "(제공되지 않음)",
            "캐릭터 상태": character_states or "(제공되지 않음)",
            "전환 힌트": transition_hint or "(제공되지 않음)",
            "세계관": world_context or "(제공되지 않음)",
        }

        # 템플릿 변수 치환
        prompt = self._substitute_variables(template, context)

        logger.debug("get_dialogue_generation_prompt",
                    f"Generated prompt with {len(prompt)} chars, turn={current_turn}")

        return prompt

    def _format_recent_dialogues(self, dialogues: list) -> str:
        """최근 대화를 텍스트로 포맷팅"""
        if not dialogues:
            return "(없음)"

        lines = []
        for d in dialogues[-10:]:  # 최근 10개
            if isinstance(d, dict):
                speaker = d.get("speaker", "Unknown")
                text = d.get("text", "")
                lines.append(f"{speaker}: {text}")
            elif hasattr(d, "speaker") and hasattr(d, "text"):
                lines.append(f"{d.speaker}: {d.text}")

        return "\n".join(lines) if lines else "(없음)"

    def _format_long_term_memories(self, memories: Optional[list]) -> str:
        """장기 기억을 텍스트로 포맷팅"""
        logger.debug("_format_long_term_memories", f"DEBUG: Formatting memories, count={len(memories) if memories else 0}")
        if memories:
            logger.debug("_format_long_term_memories", f"DEBUG: First memory = {memories[0]}")

        if not memories:
            return "(없음)"

        lines = []
        for m in memories:
            if isinstance(m, dict):
                memory_type = m.get("type", "unknown")
                content = m.get("content", "")
                importance = m.get("importance", 0.0)
                # 중요도를 별로 표시 (0.7 이상: ★★★, 0.5 이상: ★★, 그 외: ★)
                stars = "★★★" if importance >= 0.7 else ("★★" if importance >= 0.5 else "★")
                lines.append(f"[{memory_type}] {stars} {content}")
                logger.debug("_format_long_term_memories", f"DEBUG: Formatted memory: [{memory_type}] {stars} {content}")

        result = "\n".join(lines) if lines else "(없음)"
        logger.debug("_format_long_term_memories", f"DEBUG: Final formatted result length = {len(result)}")
        return result

    def _substitute_variables(self, template: str, context: Dict[str, str]) -> str:
        """
        템플릿 변수 치환

        YAML의 [변수명] 형식을 context 값으로 치환
        """
        result = template
        for key, value in context.items():
            placeholder = f"[{key}]"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    def _get_fallback_prompt(
        self,
        beats_description: str,
        speaker_pool: list,
        user_input: str
    ) -> str:
        """YAML 로드 실패 시 fallback 프롬프트"""
        return f"""당신은 귀멸의 칼날 시나리오의 대사 작가입니다.

[상황 요약]
{beats_description}

[등장 캐릭터]
{", ".join(speaker_pool)}

[사용자 입력]
{user_input}

위 상황에 맞는 자연스러운 NPC 대화를 생성하세요.

[중요 규칙]
1. 플레이어의 대사는 생성하지 마세요 (NPC만)
2. NPC가 플레이어를 언급할 때는 "{{user}}" 사용
3. JSON 형식으로 응답: {{"dialogues": [{{"speaker": "캐릭터명", "text": "대사", "emotion": "감정"}}, ...]}}
"""

    def get_router_topic_classifier_prompt(
        self,
        user_text: str,
        recent_history: str,
        scenario_id: str,
        current_stage: str
    ) -> tuple[str, str]:
        """
        router.topic_classifier 프롬프트 생성

        Returns:
            (system_prompt, user_prompt) 튜플
        """
        system_template = self.prompts.get("router", {}).get("topic_classifier", "")
        user_template = self.prompts.get("router", {}).get("topic_classifier_user", "")

        if not system_template or not user_template:
            logger.warning("get_router_topic_classifier_prompt", "Router prompts not found")
            return ("", "")

        # user_prompt 변수 치환
        user_prompt = user_template.format(
            text=user_text,
            recent_history=recent_history,
            scenario_id=scenario_id,
            current_stage=current_stage
        )

        return (system_template, user_prompt)


# 싱글톤 인스턴스
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """PromptService 싱글톤"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service


__all__ = ["PromptService", "get_prompt_service"]
