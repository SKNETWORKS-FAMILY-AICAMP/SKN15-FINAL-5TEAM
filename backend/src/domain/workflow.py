"""
LangGraph Workflow - 대화 흐름 오케스트레이션

ParentAgent를 LangGraph 호환 인터페이스로 래핑.
Clean Architecture: Domain Layer의 비즈니스 로직 오케스트레이션.
"""

from typing import Dict, Any
import logging

from src.domain.agents.parent_agent import ParentAgent

logger = logging.getLogger(__name__)


class Workflow:
    """
    LangGraph Workflow

    ParentAgent를 사용하여 대화 흐름을 관리하는 간단한 래퍼.
    """

    def __init__(self, locale: str = "ko"):
        """
        Args:
            locale: 언어 설정 (기본값: "ko")
        """
        self.parent_agent = ParentAgent(locale=locale)
        logger.info(f"🔧 Workflow initialized with locale={locale}")

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        워크플로우 실행 (LangGraph 호환)

        Args:
            state: 현재 상태 (GraphState)

        Returns:
            업데이트된 상태
        """
        logger.debug(f"🚀 Workflow invoked: session={state.get('session_id')}")

        try:
            # ParentAgent를 통한 오케스트레이션
            result_state = self.parent_agent.run(state)

            logger.debug(f"✅ Workflow completed: session={state.get('session_id')}")
            return result_state

        except Exception as e:
            logger.error(f"❌ Workflow error: {e}", exc_info=True)
            # 에러 발생 시에도 상태 반환 (에러 정보 포함)
            state["error"] = str(e)
            state["output"] = {
                "dialogues": [
                    {
                        "speaker": "시스템",
                        "content": "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                        "emotion": "neutral"
                    }
                ],
                "has_more": False
            }
            return state


def create_workflow(locale: str = "ko") -> Workflow:
    """
    Workflow 팩토리 함수

    Args:
        locale: 언어 설정 (기본값: "ko")

    Returns:
        Workflow 인스턴스
    """
    return Workflow(locale=locale)


__all__ = ["Workflow", "create_workflow"]
