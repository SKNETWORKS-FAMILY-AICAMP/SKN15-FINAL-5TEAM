from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.services import DialogueGenerationService
from src.utils.logger import log
from src.tools.training_logger import log_agent
from src.database.session_manager import HybridSessionManager

# ============================================================
# 🎭 ChildrenAgent — parent가 넘겨준 children_ctx로 실제 대사를 생성
# ============================================================

class ChildrenAgent:
    """
    ChildrenAgent - 대사 생성 노드

    ParentAgent가 구성한 children_ctx를 받아 DialogueGenerationService를 통해 대사를 생성합니다.
    비즈니스 로직은 DialogueGenerationService에 위임하고, 노드 역할만 수행합니다.
    """

    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self):
        """DialogueGenerationService 초기화"""
        self._session_manager: Optional[HybridSessionManager] = None

        # Initialize session manager for error logging
        try:
            from src.database.db_manager import DatabaseManager
            from src.database.cache_manager import CacheManager
            db = DatabaseManager()
            cache_manager = CacheManager()
            self._session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
        except Exception as e:
            log("children", "session_manager_init_failed", error=str(e))

        # DialogueGenerationService 초기화 (session_manager 주입)
        self._dialogue_service = DialogueGenerationService(session_manager=self._session_manager)

    # ============================================================
    # 🚦 실행 엔트리 포인트
    # ============================================================
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChildrenAgent의 메인 엔트리 포인트.
        ParentAgent → children_ctx를 넘겨주면,
        DialogueGenerationService를 통해 실제 대사 리스트(agent_responses)를 생성한다.
        """
        ctx = self._extract_context(state)

        # 컨텍스트가 없으면 빈 응답 처리
        if not ctx:
            log("children", "Missing children_ctx; emitting empty response")
            state["agent_responses"] = []
            state["has_more_dialogues"] = False
            state["next_node"] = "dialogue_agent"
            return state

        # ✅ 대사 생성 (DialogueGenerationService 사용)
        dialogues = self._dialogue_service.generate_dialogues(ctx, state)

        # 생성된 대사 결과를 state에 저장
        state["agent_responses"] = dialogues
        state["has_more_dialogues"] = False
        state["next_node"] = "dialogue_agent"

        return state

    # ============================================================
    # 🔧 내부 헬퍼
    # ============================================================
    def _extract_context(self, state: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        children_ctx를 추출하는 함수.
        - state.children_ctx를 직접 사용 (parent_agent가 업데이트하는 값)
        - state.agent_inputs.children은 stale할 수 있으므로 사용하지 않음
        """
        # 🔧 수정: agent_inputs.children은 오래된 값일 수 있으므로 무시
        # parent_agent가 업데이트한 state.children_ctx만 사용
        ctx = state.get("children_ctx")

        if ctx:
            log("children", "✅ Using ctx from state.children_ctx")
        else:
            log("children", "⚠️ No children_ctx found in state")

        return ctx if isinstance(ctx, dict) else None


# ============================================================
# 🚀 모듈 수준 헬퍼
# ============================================================
DEFAULT_AGENT = ChildrenAgent()


def run_children_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    # Phase 4: 로그 수집 시작
    start_time = time.perf_counter()

    try:
        result = DEFAULT_AGENT.run(state)

        # Phase 4: 로그 수집 (성공)
        model_output = {
            "agent_responses": result.get("agent_responses", []),
            "has_more_dialogues": result.get("has_more_dialogues", False),
            "next_node": result.get("next_node"),
        }

        log_agent(
            agent_name="children",
            state=state,
            model_output=model_output,
            start_time=start_time,
            llm_model="gpt-4o-mini",  # Children Agent uses gpt-4o-mini (설정 기준)
        )

        # 📊 Performance Metric 저장: Children Agent 실행 시간
        try:
            from src.database.session_manager import HybridSessionManager
            from src.database.db_manager import DatabaseManager

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            session_id = state.get("session_id")

            if session_id:
                from src.database.cache_manager import CacheManager
                db = DatabaseManager()
                cache_manager = CacheManager()
                session_manager = HybridSessionManager(db_manager=db, cache_manager=cache_manager)
                session_manager.save_performance_metric(
                    metric_name="children_agent_execution_time",
                    metric_value=execution_time_ms,
                    session_id=session_id,
                    metadata={
                        "dialogue_count": len(result.get("agent_responses", [])),
                        "has_more": result.get("has_more_dialogues", False),
                        "next_node": result.get("next_node")
                    }
                )
        except Exception as e:
            log("children", "performance_metric_save_failed", error=str(e))

        return result
    except Exception as e:
        # Phase 4: 로그 수집 (에러)
        log_agent(
            agent_name="children",
            state=state,
            model_output={"error": str(e)},
            start_time=start_time,
            is_error=True,
            error_message=str(e),
        )
        raise


__all__ = ["ChildrenAgent", "run_children_agent"]
