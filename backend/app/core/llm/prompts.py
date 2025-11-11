"""
Prompt Template Management
프롬프트 템플릿 관리 시스템
"""
from typing import Dict, Any, Optional
from string import Template


class PromptTemplate:
    """
    프롬프트 템플릿 클래스

    Usage:
        template = PromptTemplate(
            "당신은 ${character_name}입니다. ${user_name}와 대화하세요."
        )
        prompt = template.format(character_name="탄지로", user_name="플레이어")
    """

    def __init__(self, template_string: str):
        """
        Args:
            template_string: 템플릿 문자열 (${variable} 형식)
        """
        self.template_string = template_string
        self.template = Template(template_string)

    def format(self, **kwargs) -> str:
        """
        템플릿에 변수를 치환하여 최종 프롬프트 생성

        Args:
            **kwargs: 치환할 변수들

        Returns:
            치환된 프롬프트 문자열
        """
        try:
            return self.template.substitute(kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

    def safe_format(self, **kwargs) -> str:
        """
        안전한 치환 (누락된 변수는 그대로 유지)

        Args:
            **kwargs: 치환할 변수들

        Returns:
            치환된 프롬프트 문자열
        """
        return self.template.safe_substitute(kwargs)


class DialoguePrompts:
    """
    대사 생성용 프롬프트 모음
    """

    # 시스템 프롬프트: 캐릭터 설정
    CHARACTER_SYSTEM = PromptTemplate("""당신은 '${character_name}'입니다.

[캐릭터 설정]
${character_description}

[성격 특징]
${personality_traits}

[말투 특징]
${speaking_style}

[현재 상황]
${current_situation}

[지시사항]
- 캐릭터의 성격과 말투를 정확히 반영하세요
- 주어진 감정(${emotion})을 자연스럽게 표현하세요
- 대화 맥락을 고려하여 응답하세요
- JSON 형식으로 응답하세요: {"dialogues": [{"speaker": "캐릭터명", "text": "대사", "emotion": "감정"}]}
""")

    # 유저 프롬프트: 대사 생성 요청
    DIALOGUE_REQUEST = PromptTemplate("""[대화 이력]
${conversation_history}

[사용자 입력]
${user_input}

위 대화 맥락을 바탕으로, ${character_name}의 응답을 생성하세요.

[요구사항]
- 대사 수: ${num_dialogues}개
- 감정 상태: ${emotion}
- 추가 지시사항: ${additional_instructions}
""")

    # 간단한 대사 생성 (Beat 없음)
    SIMPLE_DIALOGUE = PromptTemplate("""당신은 '${character_name}'입니다.

성격: ${personality}
현재 감정: ${emotion}

사용자가 "${user_input}"라고 말했습니다.

${character_name}의 입장에서 자연스럽게 응답하세요.
JSON 형식: {"dialogues": [{"speaker": "${character_name}", "text": "대사", "emotion": "${emotion}"}]}
""")

    # Beat 기반 대사 생성
    BEAT_BASED_DIALOGUE = PromptTemplate("""당신은 시나리오 작가입니다.

[시나리오 Beat]
${beat_description}

[등장 캐릭터 (NPC)]
${characters_info}

[플레이어]
- 플레이어는 "{user}"로 표시됩니다
- **중요: 플레이어({user})의 대사는 절대 생성하지 마세요**
- NPC 캐릭터의 대사만 생성하세요
- NPC가 플레이어를 언급할 때는 "{user}" 플레이스홀더를 사용하세요 (예: "{user}는 훌륭한 제자야!")

[이전 대화]
${conversation_history}

[사용자 입력]
${user_input}

위 Beat를 따라 NPC 캐릭터들의 자연스러운 대화를 생성하세요.

[중요 규칙]
1. **플레이어({user})의 대사는 절대 생성하지 마세요** - NPC만 말합니다
2. NPC 캐릭터의 speaker는 캐릭터 이름 사용 (예: "렌고쿠", "탄지로", "narr")
3. NPC 대사에서 플레이어를 언급할 때는 "{user}" 사용 (예: "렌고쿠: {user}는 훌륭해!")
4. 플레이어 이름(츠구코 등)을 직접 사용하지 말고 "{user}" 플레이스홀더 사용

[출력 형식]
JSON 형식으로 응답하세요:
{
  "dialogues": [
    {"speaker": "캐릭터명", "text": "대사", "emotion": "감정"},
    ...
  ]
}

[올바른 예시]
{
  "dialogues": [
    {"speaker": "narr", "text": "무한열차 안. 렌고쿠가 도시락을 먹고 있다.", "emotion": "neutral"},
    {"speaker": "렌고쿠", "text": "우마이! {user}도 먹어봐!", "emotion": "joyful"},
    {"speaker": "탄지로", "text": "렌고쿠 선배, 질문이 있습니다.", "emotion": "serious"}
  ]
}

[잘못된 예시 - 하지 마세요!]
{
  "dialogues": [
    {"speaker": "{user}", "text": "...", ...},  ❌ 플레이어 대사 생성 금지!
    {"speaker": "츠구코", "text": "...", ...},  ❌ 플레이어 이름 직접 사용 금지!
    {"speaker": "렌고쿠", "text": "츠구코는...", ...}  ❌ {user} 플레이스홀더 사용!
  ]
}
""")


class SystemPrompts:
    """
    시스템 레벨 프롬프트 모음
    """

    # Guardrail: 입력 검증
    GUARDRAIL_VALIDATION = PromptTemplate("""당신은 입력 검증 시스템입니다.

사용자 입력: "${user_input}"

다음 항목을 검증하세요:
1. 부적절한 내용 포함 여부 (욕설, 폭력, 차별 등)
2. 시나리오 벗어남 여부
3. 의미 있는 입력인지 확인

JSON 형식으로 응답:
{
  "is_valid": true/false,
  "reason": "검증 실패 이유 (실패 시)",
  "severity": "low/medium/high" (실패 시)
}
""")

    # Router: 토픽 분류
    ROUTER_CLASSIFICATION = PromptTemplate("""당신은 대화 분류 시스템입니다.

사용자 입력: "${user_input}"

이 입력이 어떤 카테고리에 속하는지 분류하세요:
${available_categories}

JSON 형식으로 응답:
{
  "category": "카테고리명",
  "confidence": 0.0~1.0,
  "reasoning": "분류 근거"
}
""")


def get_dialogue_prompt(
    character_name: str,
    user_input: str,
    emotion: str = "neutral",
    personality: str = "친근하고 밝음",
    conversation_history: Optional[str] = None
) -> tuple[str, str]:
    """
    간단한 대사 생성 프롬프트 생성

    Args:
        character_name: 캐릭터 이름
        user_input: 사용자 입력
        emotion: 감정 상태
        personality: 성격 설명
        conversation_history: 대화 이력 (선택)

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = DialoguePrompts.SIMPLE_DIALOGUE.format(
        character_name=character_name,
        personality=personality,
        emotion=emotion,
        user_input=user_input
    )

    user_prompt = f"사용자: {user_input}"

    if conversation_history:
        user_prompt = f"{conversation_history}\n\n{user_prompt}"

    return system_prompt, user_prompt


def get_beat_dialogue_prompt(
    beat_description: str,
    characters_info: str,
    user_input: str,
    conversation_history: str = ""
) -> tuple[str, str]:
    """
    Beat 기반 대사 생성 프롬프트 생성

    Args:
        beat_description: Beat 설명
        characters_info: 캐릭터 정보
        user_input: 사용자 입력
        conversation_history: 대화 이력

    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = "당신은 창의적인 시나리오 작가입니다. 캐릭터의 성격과 상황에 맞는 자연스러운 대화를 생성하세요."

    user_prompt = DialoguePrompts.BEAT_BASED_DIALOGUE.format(
        beat_description=beat_description,
        characters_info=characters_info,
        user_input=user_input,
        conversation_history=conversation_history or "(없음)"
    )

    return system_prompt, user_prompt
