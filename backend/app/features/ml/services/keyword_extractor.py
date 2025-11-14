"""
KeywordExtractor Service

LLM을 사용하여 사용자 입력에서 핵심 키워드를 추출하는 서비스
"""
import json
from typing import Dict, List, Any, Optional

from app.core.llm import LLMClient
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("KeywordExtractor")


class KeywordExtractor:
    """
    LLM 기반 키워드 추출 서비스

    사용자 입력에서 다음을 추출합니다:
    - verbs: 동사 (싸운다, 설득한다, 도망간다 등)
    - targets: 대상 캐릭터/객체 (렌고쿠, 이노스케, 무잔 등)
    - modifiers: 수식어 (강하게, 조심스럽게, 빠르게 등)
    - emotions: 감정 (화난, 슬픈, 기쁜 등)
    - locations: 장소 (무한열차, 나비저택 등)
    """

    def __init__(self):
        self.llm = LLMClient()
        logger.info("__init__", "KeywordExtractor initialized")

    async def extract(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[str]]:
        """
        텍스트에서 키워드 추출

        Args:
            text: 추출할 텍스트 (사용자 입력)
            context: 추가 컨텍스트 (스테이지, 캐릭터 등)

        Returns:
            {
                "verbs": ["싸운다", "설득한다"],
                "targets": ["렌고쿠", "이노스케"],
                "modifiers": ["강하게"],
                "emotions": ["화난"],
                "locations": ["무한열차"]
            }
        """
        if not text or not text.strip():
            logger.warning("extract", "Empty text provided")
            return {
                "verbs": [],
                "targets": [],
                "modifiers": [],
                "emotions": [],
                "locations": [],
            }

        logger.info("extract", f"Extracting keywords from text: {text[:50]}...")

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(text, context)

        try:
            # LLM 호출 (JSON 모드)
            response = await self.llm.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # 낮은 온도로 일관성 확보
                max_tokens=500,
            )

            # 응답 정규화
            keywords = self._normalize_response(response)

            logger.info(
                "extract",
                f"Extracted keywords: verbs={len(keywords['verbs'])}, "
                f"targets={len(keywords['targets'])}, "
                f"modifiers={len(keywords['modifiers'])}",
                keywords=keywords,
            )

            return keywords

        except Exception as e:
            logger.error("extract", f"Failed to extract keywords: {e}", exc_info=True)
            # 실패 시 빈 결과 반환
            return {
                "verbs": [],
                "targets": [],
                "modifiers": [],
                "emotions": [],
                "locations": [],
            }

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 한국어 텍스트에서 핵심 키워드를 추출하는 전문가입니다.

귀멸의 칼날 세계관 기반의 대화형 게임에서 사용자 입력을 분석하여
다음 카테고리별로 키워드를 추출해주세요:

1. **verbs (동사)**: 행동을 나타내는 동사
   - 예: "싸운다", "설득한다", "도망간다", "훈련한다", "대화한다", "공격한다"

2. **targets (대상)**: 행동의 대상이 되는 캐릭터, 객체, 개념
   - 예: "렌고쿠", "이노스케", "시노부", "무잔", "귀신", "기둥"

3. **modifiers (수식어)**: 행동이나 대상을 수식하는 부사/형용사
   - 예: "강하게", "조심스럽게", "빠르게", "천천히", "격렬하게"

4. **emotions (감정)**: 표현된 감정이나 감정 상태
   - 예: "화난", "슬픈", "기쁜", "두려운", "흥분한"

5. **locations (장소)**: 언급된 장소나 위치
   - 예: "무한열차", "나비저택", "후지산", "오사카"

**출력 형식:**
반드시 JSON 형식으로 출력하세요:
{
    "verbs": ["동사1", "동사2"],
    "targets": ["대상1", "대상2"],
    "modifiers": ["수식어1"],
    "emotions": ["감정1"],
    "locations": ["장소1"]
}

**주의사항:**
- 키워드는 원형으로 추출 (예: "싸웠다" -> "싸운다")
- 중복 제거
- 관련성 높은 키워드만 추출 (최대 5개씩)
- 비어있는 카테고리는 빈 배열로 반환
"""

    def _build_user_prompt(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """사용자 프롬프트 생성"""
        prompt_parts = [f"**사용자 입력:**\n{text}"]

        if context:
            context_str = self._format_context(context)
            if context_str:
                prompt_parts.append(f"\n**현재 컨텍스트:**\n{context_str}")

        prompt_parts.append("\n위 텍스트에서 키워드를 추출하여 JSON 형식으로 반환해주세요.")

        return "\n".join(prompt_parts)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """컨텍스트 포맷팅"""
        parts = []

        if "stage" in context:
            parts.append(f"- 현재 스테이지: {context['stage']}")

        if "characters" in context and context["characters"]:
            parts.append(f"- 등장 캐릭터: {', '.join(context['characters'])}")

        if "scenario_id" in context:
            parts.append(f"- 시나리오: {context['scenario_id']}")

        return "\n".join(parts) if parts else ""

    def _normalize_response(self, response: Any) -> Dict[str, List[str]]:
        """LLM 응답 정규화"""
        # 기본 구조
        normalized = {
            "verbs": [],
            "targets": [],
            "modifiers": [],
            "emotions": [],
            "locations": [],
        }

        try:
            # response가 dict가 아니면 파싱 시도
            if isinstance(response, str):
                response = json.loads(response)

            if not isinstance(response, dict):
                logger.warning("_normalize_response", "Response is not a dict")
                return normalized

            # 각 카테고리 추출 및 정규화
            for key in normalized.keys():
                if key in response and isinstance(response[key], list):
                    # 문자열만 필터링하고 중복 제거
                    values = [
                        str(v).strip()
                        for v in response[key]
                        if v and str(v).strip()
                    ]
                    normalized[key] = list(dict.fromkeys(values))  # 순서 유지하며 중복 제거

            return normalized

        except json.JSONDecodeError as e:
            logger.error("_normalize_response", f"JSON decode error: {e}")
            return normalized
        except Exception as e:
            logger.error("_normalize_response", f"Normalization error: {e}")
            return normalized

    async def extract_batch(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, List[str]]]:
        """
        여러 텍스트에서 키워드 배치 추출

        Args:
            texts: 추출할 텍스트 리스트
            context: 공통 컨텍스트

        Returns:
            키워드 딕셔너리 리스트
        """
        logger.info("extract_batch", f"Extracting keywords from {len(texts)} texts")

        results = []
        for text in texts:
            keywords = await self.extract(text, context)
            results.append(keywords)

        return results
