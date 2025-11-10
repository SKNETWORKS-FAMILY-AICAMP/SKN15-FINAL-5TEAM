"""
[Core/LLM] 프롬프트 템플릿 관리 모듈

이 모듈은 LLM(Large Language Model)에 전달할 프롬프트들을 체계적으로
관리하기 위한 템플릿 클래스와 사전 정의된 프롬프트들을 제공합니다.

- PromptTemplate: 변수를 포함하는 프롬프트 문자열을 쉽게 포맷팅할 수 있는 클래스.
- DialoguePrompts / SystemPrompts: 특정 목적(대화, 시스템)에 따라 프롬프트들을 그룹화.
- 헬퍼 함수: 동적으로 프롬프트를 생성하는 편의 함수.

NOTE: 현재 프롬프트들이 코드 내에 하드코딩되어 있습니다.
      유지보수성을 높이려면 이들을 `configs/prompts.yaml` 같은 외부 파일에서
      읽어오도록 리팩터링하는 것을 강력히 권장합니다.
      이를 통해 코드 변경 및 재배포 없이 프롬프트를 수정할 수 있습니다.
"""
from typing import Dict, Any, Optional
from string import Template


# ============================================================
# 프롬프트 템플릿 클래스
# ============================================================
class PromptTemplate:
    """
    Python의 내장 `string.Template`을 래핑하여 프롬프트 문자열을 관리하는 클래스입니다.
    `${variable}` 형식의 플레이스홀더를 사용하여 동적으로 프롬프트를 생성합니다.

    Usage:
        template = PromptTemplate("Hello, ${name}!")
        prompt = template.format(name="World")
        # prompt: "Hello, World!"
    """

    def __init__(self, template_string: str):
        """
        PromptTemplate을 초기화합니다.

        Args:
            template_string (str): `${variable}` 형식의 플레이스홀더를 포함하는 템플릿 문자열.
        """
        self.template_string = template_string
        self.template = Template(template_string)

    def format(self, **kwargs) -> str:
        """
        템플릿의 플레이스홀더를 주어진 키워드 인자로 치환하여 최종 프롬프트를 생성합니다.
        만약 템플릿에 필요한 변수가 `kwargs`에 없으면 `KeyError`가 발생합니다.

        Args:
            **kwargs: 템플릿의 플레이스홀더에 해당하는 변수들.

        Returns:
            str: 모든 변수가 치환된 최종 프롬프트 문자열.
        """
        try:
            return self.template.substitute(kwargs)
        except KeyError as e:
            raise ValueError(f"프롬프트 템플릿에 필요한 변수가 누락되었습니다: {e}")

    def safe_format(self, **kwargs) -> str:
        """
        `.format()`과 유사하지만, 템플릿에 필요한 변수가 누락되어도 에러를 발생시키지 않고
        플레이스홀더를 그대로 남겨두는 안전한 버전입니다.

        Args:
            **kwargs: 템플릿의 플레이스홀더에 해당하는 변수들.

        Returns:
            str: 변수가 치환된 프롬프트 문자열 (누락된 변수는 ${variable} 형태로 유지됨).
        """
        return self.template.safe_substitute(kwargs)


# ============================================================
# 대화 생성용 프롬프트 그룹
# ============================================================
class DialoguePrompts:
    """
    캐릭터 대사 생성을 위해 사용되는 프롬프트들을 모아놓은 클래스입니다.
    """

    # 시스템 프롬프트: LLM에게 캐릭터의 역할과 정체성을 부여합니다.
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
- 캐릭터의 성격과 말투를 정확히 반영하세요.
- 주어진 감정(${emotion})을 자연스럽게 표현하세요.
- 대화 맥락을 고려하여 응답하세요.
- 반드시 아래 JSON 형식으로만 응답하세요:
{"dialogues": [{"speaker": "캐릭터명", "text": "대사", "emotion": "감정"}]}
""")

    # 유저 프롬프트: LLM에게 실제 대화 생성을 요청하는 부분입니다.
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

    # 간단한 대화 생성을 위한 단일 프롬프트
    SIMPLE_DIALOGUE = PromptTemplate("""당신은 '${character_name}'입니다.

성격: ${personality}
현재 감정: ${emotion}

사용자가 "${user_input}"라고 말했습니다.

${character_name}의 입장에서 자연스럽게 응답하세요.
JSON 형식: {"dialogues": [{"speaker": "${character_name}", "text": "대사", "emotion": "${emotion}"}]}
""")

    # 시나리오의 특정 'Beat'(장면 또는 사건)에 기반하여 대화를 생성하기 위한 프롬프트
    BEAT_BASED_DIALOGUE = PromptTemplate("""당신은 시나리오 작가입니다.

[시나리오 Beat]
${beat_description}

[등장 캐릭터]
${characters_info}

[이전 대화]
${conversation_history}

[사용자 입력]
${user_input}

위 Beat의 흐름을 따라, 캐릭터들의 성격에 맞는 자연스러운 대화를 생성하세요.

[출력 형식]
JSON 형식으로 응답하세요:
{
  "dialogues": [
    {"speaker": "캐릭터명", "text": "대사", "emotion": "감정"},
    ...
  ]
}
""")


# ============================================================
# 시스템 기능용 프롬프트 그룹
# ============================================================
class SystemPrompts:
    """
    대화 생성 외에, 시스템의 내부 로직(입력 검증, 라우팅 등)을 위해
    사용되는 프롬프트들을 모아놓은 클래스입니다.
    """

    # Guardrail: 사용자 입력을 검증하여 부적절하거나 유효하지 않은 입력을 필터링합니다.
    GUARDRAIL_VALIDATION = PromptTemplate("""당신은 입력 검증 시스템입니다.

사용자 입력: "${user_input}"

다음 항목을 검증하세요:
1. 부적절한 내용 포함 여부 (욕설, 폭력, 차별, 성적인 내용 등)
2. 주어진 시나리오와 완전히 무관한 내용인지 여부
3. 의미 있는 입력인지 여부 (예: "...", "asdf" 등 무의미한 입력)

반드시 아래 JSON 형식으로만 응답하세요:
{
  "is_valid": true/false,
  "reason": "검증 실패 이유 (실패 시에만 작성)",
  "severity": "low/medium/high" (실패 시에만 작성)
}
""")

    # Router: 사용자 입력의 의도를 파악하여 적절한 기능으로 분기(라우팅)합니다.
    ROUTER_CLASSIFICATION = PromptTemplate("""당신은 대화 의도 분류 시스템입니다.

사용자 입력: "${user_input}"

이 입력이 아래 카테고리 중 어떤 것에 가장 가까운지 분류하세요:
${available_categories}

반드시 아래 JSON 형식으로만 응답하세요:
{
  "category": "분류된 카테고리명",
  "confidence": 0.0~1.0 사이의 신뢰도 점수,
  "reasoning": "왜 그렇게 분류했는지에 대한 간략한 근거"
}
""")


# ============================================================
# 프롬프트 생성 헬퍼 함수
# ============================================================
def get_dialogue_prompt(
    character_name: str,
    user_input: str,
    emotion: str = "neutral",
    personality: str = "친근하고 밝음",
    conversation_history: Optional[str] = None
) -> tuple[str, str]:
    """
    간단한 대화 생성을 위한 시스템 및 유저 프롬프트를 동적으로 생성합니다.

    Args:
        character_name (str): 대화를 생성할 캐릭터의 이름.
        user_input (str): 사용자의 최근 입력.
        emotion (str): 캐릭터가 표현할 감정.
        personality (str): 캐릭터의 성격.
        conversation_history (Optional[str]): 이전 대화 기록.

    Returns:
        tuple[str, str]: (시스템 프롬프트, 유저 프롬프트) 튜플.
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
    시나리오 Beat 기반 대화 생성을 위한 시스템 및 유저 프롬프트를 동적으로 생성합니다.

    Args:
        beat_description (str): 현재 진행 중인 시나리오 Beat에 대한 설명.
        characters_info (str): 장면에 등장하는 캐릭터들에 대한 정보.
        user_input (str): 사용자의 최근 입력.
        conversation_history (str): 이전 대화 기록.

    Returns:
        tuple[str, str]: (시스템 프롬프트, 유저 프롬프트) 튜플.
    """
    system_prompt = "당신은 창의적인 시나리오 작가입니다. 캐릭터의 성격과 주어진 상황에 맞는 자연스러운 대화를 생성하세요."
    user_prompt = DialoguePrompts.BEAT_BASED_DIALOGUE.format(
        beat_description=beat_description,
        characters_info=characters_info,
        user_input=user_input,
        conversation_history=conversation_history or "(대화 시작)"
    )
    return system_prompt, user_prompt
