"""
============================================================
✅ Dialogue Validation Service — 대사 검증
============================================================
LLM 및 규칙 기반으로 대사를 검증합니다.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.graph_state import Dialogue, AgentState
from src.utils.llm_client import LLMClient, get_llm_client
from src.utils.config_loader import get_config_loader

_PROMPTS = get_config_loader().get_prompts()
_DIALOGUE_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("dialogue") or {})
_DIALOGUE_VALIDATION_PROMPT = (_DIALOGUE_PROMPTS.get("validation") or "").strip()

if not _DIALOGUE_VALIDATION_PROMPT:
    raise ValueError("DialogueAgent validation prompt missing in configs/prompts.yaml")


class DialogueValidationService:
    """
    대사 검증 서비스

    책임:
    - LLM 기반 대사 검증
    - 규칙 기반 대사 검증
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
        """
        self._llm = llm_client

        # 검증 기준
        self.validation_criteria = {
            "character_consistency": {
                "weight": 0.4,
                "description": "캐릭터 성격과 말투의 일관성"
            },
            "context_relevance": {
                "weight": 0.3,
                "description": "게임 상황과 문맥에 적합한지"
            },
            "emotional_appropriateness": {
                "weight": 0.2,
                "description": "감정 표현이 적절한지"
            },
            "game_rule_compliance": {
                "weight": 0.1,
                "description": "게임 규칙을 준수하는지"
            }
        }

    def validate_dialogue(self, dialogue: Dialogue, state: AgentState, use_llm: bool = True) -> Dict:
        """
        대사 검증

        Args:
            dialogue: 검증할 대사
            state: 전체 state 객체
            use_llm: LLM 사용 여부

        Returns:
            검증 결과 dict
        """
        print(f"[VALIDATION] validate_dialogue: use_llm={use_llm}", flush=True)

        if use_llm and self._llm:
            print(f"[VALIDATION] Calling _validate_with_llm", flush=True)
            result = self._validate_with_llm(dialogue, state)
            if result:
                return result

        # LLM 실패 시 규칙 기반 검증
        print(f"[VALIDATION] Calling _validate_with_rules", flush=True)
        result = self._validate_with_rules(dialogue, state)
        print(f"[VALIDATION] _validate_with_rules returned", flush=True)
        return result

    def _validate_with_llm(self, dialogue: Dialogue, state: AgentState) -> Optional[Dict]:
        """
        LLM을 이용한 대사 검증

        Args:
            dialogue: 검증할 대사
            state: 전체 state 객체

        Returns:
            검증 결과 dict 또는 None (실패 시)
        """
        if not self._llm:
            return None

        try:
            system_prompt = _DIALOGUE_VALIDATION_PROMPT

            # 캐릭터 정보
            character_info = self._get_character_info(dialogue.speaker)

            user_prompt = f"""캐릭터: {dialogue.speaker}
캐릭터 성격: {character_info.get('personality', '알 수 없음')}
친밀도 레벨: {dialogue.affinity_level}
현재 씬: {state.scene.current_scene}
씬 분위기: {state.scene.mood}

대사: "{dialogue.content}"
감정: {dialogue.emotion}

최근 대화 맥락:
{state.message_history.get_recent_context()}

위 대사를 평가하세요. JSON 형식으로 응답:
{{
  "scores": {{
    "character_consistency": 점수,
    "context_relevance": 점수,
    "emotional_appropriateness": 점수,
    "game_rule_compliance": 점수
  }},
  "total_score": 전체점수,
  "passed": true/false,
  "issues": ["문제점1", "문제점2", ...],
  "suggestions": "개선 제안"
}}"""

            temperature = self._llm.get_agent_setting(
                "dialogue",
                "validation_temperature",
                self._llm.get_agent_setting("dialogue", "temperature", 0.2),
            )
            max_tokens = self._llm.get_agent_setting("dialogue", "validation_max_tokens", None)

            response = self._llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                agent="dialogue",
            )

            return response

        except Exception as e:
            print(f"LLM 검증 실패: {str(e)}")
            return None

    def _validate_with_rules(self, dialogue: Dialogue, state: AgentState) -> Dict:
        """
        규칙 기반 대사 검증

        Args:
            dialogue: 검증할 대사
            state: 전체 state 객체

        Returns:
            검증 결과 dict
        """
        scores = {
            "character_consistency": 80,  # 기본 점수
            "context_relevance": 80,
            "emotional_appropriateness": 80,
            "game_rule_compliance": 90
        }

        issues = []

        # 1. 길이 검증
        if len(dialogue.content) < 5:
            scores["context_relevance"] -= 20
            issues.append("대사가 너무 짧습니다")
        elif len(dialogue.content) > 200:
            scores["context_relevance"] -= 10
            issues.append("대사가 너무 깁니다")

        # 2. 금지어 확인
        banned_words = ["씨발", "시발", "병신"]
        if any(word in dialogue.content for word in banned_words):
            scores["game_rule_compliance"] = 0
            issues.append("부적절한 언어 포함")

        # 3. 감정 일관성 확인
        emotion_keywords = {
            "happy": ["좋", "기쁘", "행복", "웃"],
            "worried": ["걱정", "불안", "조심"],
            "determined": ["반드시", "꼭", "결심"],
            "scared": ["무섭", "두렵", "으악"]
        }

        if dialogue.emotion in emotion_keywords:
            keywords = emotion_keywords[dialogue.emotion]
            if not any(kw in dialogue.content for kw in keywords):
                scores["emotional_appropriateness"] -= 15

        # 전체 점수 계산 (가중치 적용)
        total_score = sum(
            scores[key] * self.validation_criteria[key]["weight"]
            for key in scores.keys()
        )

        passed = total_score >= 70

        return {
            "scores": scores,
            "total_score": total_score,
            "passed": passed,
            "issues": issues,
            "suggestions": "기본 규칙 기반 검증 통과" if passed else "대사 수정 필요"
        }

    def _get_character_info(self, speaker: str) -> Dict:
        """
        캐릭터 정보 가져오기

        Args:
            speaker: 캐릭터 이름

        Returns:
            캐릭터 정보 dict
        """
        # 간단한 캐릭터 정보 (실제로는 DB에서 가져옴)
        characters = {
            "탄지로": {
                "personality": "정직하고 배려심 깊음. 동료애가 강함"
            },
            "이노스케": {
                "personality": "자유분방하고 호승심이 강함"
            },
            "젠이츠": {
                "personality": "겁이 많지만 용기를 보임"
            },
            "렌고쿠": {
                "personality": "열정적이고 정의로움"
            }
        }
        return characters.get(speaker, {})


__all__ = ["DialogueValidationService"]
