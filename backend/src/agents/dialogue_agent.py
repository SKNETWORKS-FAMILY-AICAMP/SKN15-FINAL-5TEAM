from datetime import datetime
import time
from typing import Any, Dict, List, Optional

from src.core.graph_state import AgentState, Dialogue
from src.utils.llm_client import get_llm_client
from src.utils.config_loader import get_config_loader
from src.tools.training_logger import log_agent
from src.utils.logger import log

_PROMPTS = get_config_loader().get_prompts()
_DIALOGUE_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("dialogue") or {})
_DIALOGUE_VALIDATION_PROMPT = (_DIALOGUE_PROMPTS.get("validation") or "").strip()
_DIALOGUE_CORRECTION_TEMPLATE = (_DIALOGUE_PROMPTS.get("correction_template") or "").strip()
if not _DIALOGUE_VALIDATION_PROMPT:
    raise ValueError("DialogueAgent validation prompt missing in configs/prompts.yaml (llm_prompts.dialogue.validation).")
if not _DIALOGUE_CORRECTION_TEMPLATE:
    raise ValueError("DialogueAgent correction_template missing in configs/prompts.yaml (llm_prompts.dialogue.correction_template).")

# ============================================================
# 🗣️ DialogueAgent — children_agent가 만든 대사를 검증·미세조정
# ============================================================

class DialogueAgent:
    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self, use_llm: bool = False, enable_multi_conversation: bool = False):
        """Dialogue Agent 초기화"""
        self.use_llm = use_llm
        self.enable_multi_conversation = enable_multi_conversation

        if self.use_llm:
            try:
                self.llm_client = get_llm_client()
            except Exception as e:
                print(f"LLM 클라이언트 초기화 실패: {str(e)}")
                self.use_llm = False

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

    # ============================================================
    # 🚦 메인 처리 루프
    # ============================================================
    def process(self, state: AgentState) -> AgentState:
        """Dialogue Agent 메인 처리"""
        start_time = time.perf_counter()

        def _finish(result_state: AgentState, label: str) -> AgentState:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f"[DIALOGUE] Elapsed {elapsed_ms:.2f} ms ({label})", flush=True)
            return result_state

        print(f"[DIALOGUE] process() start, dialogues count: {len(state.output.dialogues)}", flush=True)

        # 검증할 대사가 없으면 스킵
        if not state.output.dialogues:
            state.next_node = "wait_user_input"
            print(f"[DIALOGUE] No dialogues, skipping", flush=True)
            return _finish(state, "no_dialogues")

        # 🔥 다중 발화 지원: order 필드로 정렬 (0, 1, 2, 3... 순서대로)
        state.output.dialogues.sort(key=lambda d: d.order)
        print(f"[DIALOGUE] Dialogues sorted by order: {[d.order for d in state.output.dialogues]}", flush=True)

        # 각 대사 검증
        validated_dialogues = list(state.output.dialogues)
        print("[DIALOGUE] Starting validation loop", flush=True)
        raw_dialogues = [
            {
                "speaker": dialogue.speaker,
                "text": dialogue.content,
                "emotion": dialogue.emotion,
                "emotion_intensity": dialogue.emotion_intensity,
                "affinity_level": dialogue.affinity_level,
                "order": dialogue.order,
            }
            for dialogue in validated_dialogues
        ]
        validation_results = self.validate_batch(raw_dialogues, state)

        print(f"[DIALOGUE] Validation complete", flush=True)

        # 검증된 대사로 교체 (정렬 유지)
        state.output.dialogues = validated_dialogues

        # 🔥 턴 증가 (각 대화 완료 후)
        old_turn = state.game.turn
        state.game.increment_turn()
        print(f"[DIALOGUE] Turn incremented: {old_turn} → {state.game.turn}", flush=True)

        # 🔥 무한루프 방지: 턴 증가 후 전환 카운트 초기화
        if "_transition_count" in state.game.temp_data:
            del state.game.temp_data["_transition_count"]
            print(f"[DIALOGUE] Transition count reset after turn completion", flush=True)

        # 워크플로우 완료 시 process_depth도 리셋 (전체 워크플로우 사이클 완료)
        if "_process_depth" in state.game.temp_data:
            del state.game.temp_data["_process_depth"]
            print(f"[DIALOGUE] Process depth reset after workflow completion", flush=True)

        # 🎭 멀티캐릭터 대화 추가 (특정 씬 종료 시)
        if self.enable_multi_conversation:
            self._add_multi_character_conversation(state)

        # 메타 정보 업데이트
        state.meta.processed_by = "dialogue_agent"
        state.meta.timestamp = datetime.now().isoformat()
        state.next_node = "wait_user_input"

        log_agent(
            agent_name="dialogue",
            state=state,
            model_output={
                "validated_count": len(validated_dialogues),
                "validation_results": validation_results,
                "dialogues": [{"speaker": d.speaker, "text": d.text} for d in validated_dialogues],
            },
            start_time=start_time,
            llm_model="gpt-4o-mini",
        )

        print(f"[DIALOGUE] process() end", flush=True)
        return _finish(state, "completed")

    # ============================================================
    # 🔍 대사 검증 파이프라인
    # ============================================================
    def _validate_dialogue(self, dialogue: Dialogue, state: AgentState) -> Dict:
        """대사 검증"""
        return self._validate_with_rules(dialogue, state)

    def _validate_with_llm(self, dialogue: Dialogue, state: AgentState) -> Optional[Dict]:
        """LLM을 이용한 대사 검증"""
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

            temperature = self.llm_client.get_agent_setting(
                "dialogue",
                "validation_temperature",
                self.llm_client.get_agent_setting("dialogue", "temperature", 0.2),
            )
            max_tokens = self.llm_client.get_agent_setting("dialogue", "validation_max_tokens", None)

            response = self.llm_client.call_json(
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

    # ============================================================
    # 📏 규칙 기반 보정
    # ============================================================
    def _validate_with_rules(self, dialogue: Dialogue, state: AgentState) -> Dict:
        """규칙 기반 대사 검증"""
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

    def validate_batch(self, raw_dialogues: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """
        dict 기반 대사 리스트를 rule-based 검증한다.
        """
        results: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_dialogues or []):
            if not isinstance(raw, dict):
                continue

            dialogue = Dialogue(
                speaker=raw.get("speaker") or raw.get("character") or "unknown",
                content=raw.get("text") or raw.get("content") or "",
                emotion=raw.get("emotion") or "neutral",
                emotion_intensity=raw.get("emotion_intensity") or raw.get("tone", "normal"),
                affinity_level=str(raw.get("affinity_level") or raw.get("affinity", "medium")),
                order=raw.get("order", idx),
            )

            validation_result = self._validate_dialogue(dialogue, state)
            scores = validation_result.get("scores", {})
            total_score = float(validation_result.get("total_score", 0.0))
            passed = bool(validation_result.get("passed", False))

            score_summary = ", ".join(
                f"{metric}={scores.get(metric, 0)}" for metric in self.validation_criteria.keys()
            )
            print(
                f"[DIALOGUE] Score summary → speaker={dialogue.speaker}, total={total_score:.2f}, passed={passed} [{score_summary}]",
                flush=True,
            )

            log(
                "dialogue",
                "validation_scores",
                speaker=dialogue.speaker,
                total_score=f"{total_score:.2f}",
                passed=passed,
                **{f"{metric}_score": scores.get(metric, 0) for metric in self.validation_criteria.keys()},
            )

            results.append(
                {
                    "order": dialogue.order,
                    "speaker": dialogue.speaker,
                    "scores": scores,
                    "total_score": total_score,
                    "passed": passed,
                    "issues": validation_result.get("issues", []),
                    "suggestions": validation_result.get("suggestions"),
                }
            )

        return results


    # ============================================================
    # 📚 캐릭터 정보/멀티 대화 유틸
    # ============================================================
    def _get_character_info(self, speaker: str) -> Dict:
        """캐릭터 정보 가져오기"""
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

    def _add_multi_character_conversation(self, state: AgentState) -> None:
        """
        멀티캐릭터 대화 추가 (비활성화됨)

        Note: 이 기능은 현재 비활성화되어 있습니다.
        enable_multi_conversation=False로 설정되어 있습니다.
        """
        # 기능 비활성화
        return

DEFAULT_VALIDATION_AGENT = DialogueAgent(use_llm=False)

# ============================================================
# 🚀 모듈 수준 엔트리 포인트
# ============================================================
def run_dialogue_agent(state: AgentState) -> AgentState:
    """GraphState 기반 Dialogue Agent 실행"""
    start_time = time.perf_counter()
    print("[DIALOGUE] Formatting output...")

    agent_responses = state.get("agent_responses", []) or []
    validation_results: List[Dict[str, Any]] = []

    if agent_responses:
        validation_results = DEFAULT_VALIDATION_AGENT.validate_batch(agent_responses, state)

        if "output" not in state or not isinstance(state["output"], dict):
            state["output"] = {}

        if "dialogues" not in state["output"]:
            state["output"]["dialogues"] = []

        # 🔧 기존 dialogues 보존 (pre-transition response 등)
        existing_dialogues = state["output"]["dialogues"]
        if not isinstance(existing_dialogues, list):
            existing_dialogues = []

        # 🔥 배치 모드 지원: has_more_dialogues가 True면 agent_responses 전체를 사용
        # (children_agent가 이미 배치 크기만큼만 생성함)
        # 기존 dialogues + 새 agent_responses
        state["output"]["dialogues"] = existing_dialogues + agent_responses.copy()

        if existing_dialogues:
            print(f"[DIALOGUE] Preserved {len(existing_dialogues)} existing dialogue(s)")
        print(f"[DIALOGUE] Updated output with {len(agent_responses)} new dialogues")

        # agent_responses 초기화 (다음 배치를 위해)
        state["agent_responses"] = []
    else:
        print("[DIALOGUE] No agent_responses, skipping output update")

    # 검증 결과를 메타에 저장 (선택사항)
    meta = state.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    diagnostics = meta.get("dialogue_agent") or {}
    diagnostics["validation_results"] = validation_results
    diagnostics["validated_count"] = len(validation_results)
    meta["dialogue_agent"] = diagnostics
    state["meta"] = meta

    # 엔딩 상태 확인
    current_stage = state.get("current_stage") or ""
    final_ending = state.get("final_ending")

    if final_ending or (current_stage and "ending" in current_stage.lower()):
        state["next_node"] = "END"
        print(f"[DIALOGUE] Ending reached: {current_stage}")
    else:
        state["next_node"] = "router"
        print("[DIALOGUE] Continuing conversation...")

    print(f"[DIALOGUE] Output formatted. Dialogues: {len(state.get('output', {}).get('dialogues', []))}")

    try:
        log_agent(
            agent_name="dialogue",
            state=state,
            model_output={
                "validated_count": len(validation_results),
                "validation_results": validation_results,
                "dialogues": state.get("output", {}).get("dialogues", []),
            },
            start_time=start_time,
            llm_model="rule-based",
        )
    except Exception as exc:
        print(f"[DIALOGUE] Logging failed: {exc}")

    return state

# 테스트
if __name__ == "__main__":
    from src.core.graph_state import create_enhanced_initial_state, Dialogue

    state = create_enhanced_initial_state("test")
    state.output.dialogues = [
        Dialogue(
            speaker="탄지로",
            content="함께 싸우자! 우리가 힘을 합치면 이길 수 있어!",
            emotion="determined",
            affinity_level="high"
        )
    ]

    result = run_dialogue_agent(state)
    print(f"검증 완료. 대사 수: {len(result.output.dialogues)}")
