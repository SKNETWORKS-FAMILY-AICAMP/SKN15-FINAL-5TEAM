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
        world_context: Optional[str] = None,
        long_term_memories: Optional[list] = None,
        conversation_summary: Optional[str] = None,  # ✅ 대화 요약 추가
        user_name: Optional[str] = None,
        stage_turn: int = 0,  # ✅ Stage 턴 추가
        user_profile: Optional[str] = None,  # v2: User Profile
        stm_summary: Optional[str] = None,  # v2: STM
        scenario_buffer: Optional[str] = None,  # v2: Scenario Buffer
        time_context: Optional[str] = None  # ✅ Time context 추가
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
            return self._get_fallback_prompt(
                beats_description,
                speaker_pool,
                user_input,
                recent_dialogues,
                conversation_summary
            )

        # 최근 대화 포맷팅 ({{user}} 그대로 유지 - LLM이 학습)
        recent_history = self._format_recent_dialogues(recent_dialogues, user_name=None)
        logger.debug("get_dialogue_generation_prompt",
                    f"🔍 DEBUG: Formatted recent_history length = {len(recent_history)} chars")

        # 장기 기억 포맷팅
        formatted_memories = self._format_long_term_memories(long_term_memories)
        logger.debug("get_dialogue_generation_prompt",
                    f"🔍 DEBUG: Formatted {len(long_term_memories or [])} long-term memories")

        # ✅ 상황 블록 생성 (stage_turn에 따라 다름)
        situation_block = self._create_situation_block(
            stage_turn=stage_turn,
            beats_description=beats_description,
            recent_history=recent_history
        )

        # v2: User Profile 포맷팅
        profile_block = f"[사용자 프로필]\n{user_profile}" if user_profile else ""

        # v2: STM 포맷팅
        stm_block = f"[세션 맥락 (STM)]\n{stm_summary}" if stm_summary else ""

        # v2: Scenario Buffer 포맷팅
        buffer_block = f"[시나리오 진행 상황]\n{scenario_buffer}" if scenario_buffer else ""

        # v2: 메모리 블록 (LTM 또는 Scenario Buffer)
        memory_block = ""
        if long_term_memories:
            memory_block = f"[장기 기억 (LTM)]\n{formatted_memories}"
        elif scenario_buffer:
            memory_block = buffer_block

        # ✅ speaker_pool에서 active_counselor 치환 (최근 대화 기반)
        processed_speaker_pool = self._resolve_active_counselor(speaker_pool, recent_dialogues)

        # 변수 치환을 위한 컨텍스트 준비 (v2 순서)
        context = {
            "세계관": world_context or "(제공되지 않음)",
            "사용자 프로필": profile_block,  # v2
            "최근 대화": recent_history,  # v2: 순서 변경
            "세션 맥락": stm_block,  # v2
            "메모리 블록": memory_block,  # v2: LTM 또는 Scenario Buffer
            "상황 블록": situation_block,
            "speaker_pool": ", ".join(processed_speaker_pool),
            "사용자 입력": user_input or "(없음)",
            "대화 요약": conversation_summary or "(없음)",  # deprecated
            "장기 기억": formatted_memories,  # deprecated (메모리 블록으로 통합)
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
            "time_context": time_context or "",  # ✅ Time context 추가
        }

        # 템플릿 변수 치환
        prompt = self._substitute_variables(template, context)

        logger.debug("get_dialogue_generation_prompt",
                    f"Generated prompt with {len(prompt)} chars, turn={current_turn}")

        return prompt

    def _format_recent_dialogues(self, dialogues: list, user_name: Optional[str] = None) -> str:
        """
        최근 대화를 텍스트로 포맷팅

        중요: {{user}} 플레이스홀더를 그대로 유지합니다.
        LLM이 {{user}} 패턴을 학습하고 동일한 형식으로 생성하도록 합니다.

        ✅ NEW: speaker가 "user"이면 "{user}"로 변환하여 LLM이 인식하도록 함

        Args:
            dialogues: 대화 목록
            user_name: 사용하지 않음 (하위 호환성 유지)
        """
        if not dialogues:
            return "(없음)"

        lines = []
        for d in dialogues[-10:]:  # 최근 10개
            if isinstance(d, dict):
                speaker = d.get("speaker", "Unknown")
                text = d.get("text", "")

                # ✅ user speaker를 {user}로 변환 (LLM 인식 가능하도록)
                if speaker.lower() == "user":
                    speaker = "{user}"

                lines.append(f"{speaker}: {text}")
            elif hasattr(d, "speaker") and hasattr(d, "text"):
                speaker = d.speaker
                # ✅ user speaker를 {user}로 변환
                if speaker.lower() == "user":
                    speaker = "{user}"
                lines.append(f"{speaker}: {d.text}")

        return "\n".join(lines) if lines else "(없음)"

    def _resolve_active_counselor(self, speaker_pool: list, recent_dialogues: list) -> list:
        """
        speaker_pool에 active_counselor가 있으면 최근 대화에서 실제 상담원을 찾아 치환

        Args:
            speaker_pool: 원본 speaker_pool
            recent_dialogues: 최근 대화 목록

        Returns:
            치환된 speaker_pool
        """
        if "active_counselor" not in speaker_pool:
            return speaker_pool

        # 최근 대화에서 상담원 캐릭터 찾기 (탄지로 제외)
        counselor_candidates = {"shinobu", "rengoku", "zenitsu", "inosuke", "giyu"}
        found_counselor = None

        # 최근 10개 대화에서 상담원 찾기
        for d in recent_dialogues[-10:]:
            if isinstance(d, dict):
                speaker = d.get("speaker", "")
            elif hasattr(d, "speaker"):
                speaker = d.speaker
            else:
                continue

            if speaker in counselor_candidates:
                found_counselor = speaker
                break

        # 상담원을 찾으면 치환, 못 찾으면 그대로 유지 (LLM이 판단하도록)
        if found_counselor:
            result = [found_counselor if s == "active_counselor" else s for s in speaker_pool]
            logger.info("_resolve_active_counselor",
                       f"✅ Resolved active_counselor → {found_counselor} (from recent dialogues)")
            return result
        else:
            logger.warning("_resolve_active_counselor",
                          "⚠️ Could not resolve active_counselor from recent dialogues, keeping as-is")
            return speaker_pool

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

    def _create_situation_block(
        self,
        stage_turn: int,
        beats_description: str,
        recent_history: str
    ) -> str:
        """
        stage_turn 값에 따라 조건부 상황 블록 생성

        Args:
            stage_turn: 현재 Stage의 턴 (0이면 Stage 전환 직후)
            beats_description: Beat 목표
            recent_history: 최근 대화 히스토리

        Returns:
            포맷된 상황 블록
        """
        # 질문/선택 상황인지 감지 (묻는다, 선택, 질문 등의 키워드)
        is_question_situation = any(keyword in beats_description for keyword in [
            "묻는다", "물어본다", "질문", "선택", "어느", "어떤", "무엇", "?", "?"
        ])

        if stage_turn == 0:
            # Stage 전환 직후: 새로운 상황 강조
            if is_question_situation:
                # 질문/선택 상황: 정확히 따를 것을 강조
                return f"""🎬 **새로운 장면 시작 - 선택/질문 상황 (중요!)**

**📍 지금 발생한 상황 (정확히 따르세요!):**
{beats_description}

**🎯 핵심 지시 (절대 준수):**
- **위 상황 설명을 정확히 따르세요!**
- 상황에 "묻는다" 또는 "질문"이 포함되어 있다면, 캐릭터가 반드시 **질문**을 해야 합니다
- **🚫 절대 금지: 캐릭터가 스스로 결정하거나 선택하는 것**
- **🚫 절대 금지: "가자", "찾으러 가자", "하자" 등의 행동 대사**
- **✅ 필수: 캐릭터는 {{{{user}}}}에게 선택을 묻는 질문으로 끝나야 합니다**
- 예시: "누구를 먼저 찾을까? 이노스케? 아니면 젠이츠?" ← 이렇게 질문으로 끝

**💬 참고: 최근 대화 (이전 장면)**
{recent_history}
(↑ 이전 장면의 대화입니다. 하지만 **위 📍 상황 지시가 최우선**입니다)"""
            else:
                # 일반 상황: 기존 로직
                return f"""🎬 **새로운 장면 시작 (중요!)**

**📍 지금 막 다음 상황이 발생했습니다:**
{beats_description}

**⚠️ 주의:**
- 위 상황이 **지금 막** 시작되었습니다
- 캐릭터는 이 새로운 상황에 즉시 반응해야 합니다
- 이전 대화는 자연스럽게 마무리하면서 새 상황을 연결하세요

**💬 참고: 최근 대화 (이전 장면)**
{recent_history}
(↑ 이전 장면의 대화입니다. 급격한 단절은 피하면서, 새 상황을 반영하세요)"""
        else:
            # Stage 진행 중: 사용자 입력과 대화 흐름 우선
            return f"""**📍 현재 상황 (진행 중):**
{beats_description}

**💬 최근 대화:**
{recent_history}

**진행 가이드:**
- 사용자 입력에 집중하여 자연스럽게 반응하세요
- 현재 상황 목표를 염두에 두면서, 대화 흐름을 우선하세요"""

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
        user_input: str,
        recent_dialogues: list = None,
        conversation_summary: str = None
    ) -> str:
        """YAML 로드 실패 시 fallback 프롬프트"""
        # 최근 대화 포맷팅
        recent_history = self._format_recent_dialogues(recent_dialogues or [], user_name=None)

        # 대화 요약 포맷팅
        summary_section = f"\n[대화 요약]\n{conversation_summary}\n" if conversation_summary else ""

        return f"""당신은 귀멸의 칼날 시나리오의 대사 작가입니다.

[상황 요약]
{beats_description}

[등장 캐릭터]
{", ".join(speaker_pool)}
{summary_section}
[최근 대화]
{recent_history}

[사용자 입력]
{user_input}

위 상황에 맞는 자연스러운 NPC 대화를 생성하세요.

[중요 규칙]
1. 최근 대화의 흐름을 이어가세요
2. 플레이어의 대사는 생성하지 마세요 (NPC만)
3. NPC가 플레이어를 언급할 때는 "{{user}}" 사용
4. JSON 형식으로 응답: {{"dialogues": [{{"speaker": "캐릭터명", "text": "대사", "emotion": "감정"}}, ...]}}
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
