from __future__ import annotations  # ⚠️ 항상 맨 위!

# --- [Dynamic import path fix: local & server 호환] ---
import os, sys
from typing import Any, Dict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# --- Internal project imports ---
from .utils.logger import log
from .utils.text_matcher import detect_mission_target


class RouterAgent:
    """
    RouterAgent
    -------------------
    사용자의 입력을 intent로 분류하고,
    ParentAgent로 전달할 다음 노드를 결정한다.

    🔹 guardrail 이후 실행됨
    🔹 시나리오 로드는 ParentAgent가 담당 (여기선 로드 안 함)
    """

    def __init__(self) -> None:
        self._keyword_map = {
            "choose_allies_path": ["동료", "합류", "도움", "지원", "젠이츠", "이노스케"],
            "choose_reckless_path": ["함께 싸우", "돌진", "직접", "무모", "버텨"],
            "intervene_attack": ["공격", "베어", "찌르", "썰"],
            "intervene_noise": ["소리", "주의", "소란", "방향 전환"],
        }

    # ---------------------------------------------------------------------
    def run(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """Main router logic"""
        normalized = (user_input or "").strip()
        scene = state.get("scene") or {}
        stage_completed = scene.get("stage_completed")

        # ✅ 이미 완료된 스테이지면 대기 상태로 전환
        if stage_completed and (not normalized or normalized.startswith("__auto_continue__")):
            state["next_node"] = "wait_user_input"
            log("router", "Stage already completed; waiting for user input")
            return state
        if stage_completed:
            scene["stage_completed"] = False

        # ✅ Intent / Classification 결정
        intent = self._detect_intent(normalized)
        classification = "off_topic" if intent == "off_topic" else "on_topic"
        mission_target = detect_mission_target(normalized)

        routing_result = {
            "intent": intent,
            "classification": classification,
            "confidence": 0.7 if intent != "off_topic" else 0.2,
        }
        if mission_target:
            routing_result["mission_target"] = mission_target

        state["routing_result"] = routing_result
        state["user_intent"] = intent 
        state["next_node"] = "parent_agent"

        # ✅ temp_data에 보조 상태 기록
        temp = state.setdefault("temp_data", {})
        if mission_target in ("inosuke", "zenitsu"):
            temp["mission_first_target"] = mission_target
        if intent in ("choose_allies_path", "choose_reckless_path"):
            temp["last_user_choice"] = intent
        elif intent == "on_topic_start":
            temp["last_user_choice"] = "start"

        # ✅ 다음 노드는 항상 parent_agent
        state["next_node"] = "parent_agent"
        log("router", "Intent classified", intent=intent, target=mission_target)
        return state

    # ---------------------------------------------------------------------
    def _detect_intent(self, user_input: str) -> str:
        """Keyword 기반 intent 분류기"""
        if not user_input:
            return "off_topic"

        lowered = user_input.lower()

        # 시나리오 시작 의도
        start_keywords = ("시작", "start", "begin", "준비", "go", "시작해")
        if any(keyword in lowered for keyword in start_keywords):
            return "on_topic_start"

        # 주요 라우팅 intent
        for intent, keywords in self._keyword_map.items():
            if any(keyword in lowered for keyword in keywords):
                return intent

        # 이노스케 / 젠이츠 직접 언급 시 allies path로 분류
        if detect_mission_target(user_input) in ("inosuke", "zenitsu"):
            return "choose_allies_path"

        # 기본 fallthrough
        return "on_topic_generic"


# ---------------------------------------------------------------------
# 외부 노드용 실행 래퍼
# ---------------------------------------------------------------------
DEFAULT_AGENT = RouterAgent()


def run_router_agent(state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """LangGraph 노드에서 호출되는 엔트리 포인트"""
    return DEFAULT_AGENT.run(state, user_input)


__all__ = ["RouterAgent", "run_router_agent"]
