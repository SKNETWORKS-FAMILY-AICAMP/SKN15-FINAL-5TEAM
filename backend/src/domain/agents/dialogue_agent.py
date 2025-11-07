# ============================================================
# 🗣️ 대화 에이전트 — 자식 에이전트 출력 검증과 조정
# ============================================================
from datetime import datetime
import time
from typing import Dict, List, Optional

from src.core.graph_state import AgentState, Dialogue
from src.utils.llm_client import get_llm_client
from src.utils.config_loader import get_config_loader
from src.tools.training_logger import log_agent

_PROMPTS = get_config_loader().get_prompts()
_DIALOGUE_PROMPTS = (_PROMPTS.get("llm_prompts", {}).get("dialogue") or {})
_DIALOGUE_VALIDATION_PROMPT = (_DIALOGUE_PROMPTS.get("validation") or "").strip()
_DIALOGUE_CORRECTION_TEMPLATE = (_DIALOGUE_PROMPTS.get("correction_template") or "").strip()
if not _DIALOGUE_VALIDATION_PROMPT:
    raise ValueError("DialogueAgent validation prompt missing in configs/prompts.yaml (llm_prompts.dialogue.validation).")
if not _DIALOGUE_CORRECTION_TEMPLATE:
    raise ValueError("DialogueAgent correction_template missing in configs/prompts.yaml (llm_prompts.dialogue.correction_template).")

# ============================================================
# ============================================================

class DialogueAgent:
    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self, use_llm: bool = True, enable_multi_conversation: bool = False):
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

        state.output.dialogues.sort(key=lambda d: d.order)
        print(f"[DIALOGUE] Dialogues sorted by order: {[d.order for d in state.output.dialogues]}", flush=True)

        # 각 대사 검증
        validated_dialogues = []
        validation_results = []

        print(f"[DIALOGUE] Starting validation loop", flush=True)
        for dialogue in state.output.dialogues:
            print(f"[DIALOGUE] Validating dialogue from {dialogue.speaker} (order: {dialogue.order})", flush=True)
            validation_result = self._validate_dialogue(dialogue, state)
            validation_results.append(validation_result)

            # 검증 통과 시 그대로 사용, 실패 시 수정
            if validation_result["passed"]:
                validated_dialogues.append(dialogue)
            else:
                # 자동 수정 시도
                corrected = self._correct_dialogue(dialogue, state, validation_result)
                validated_dialogues.append(corrected if corrected else dialogue)

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

        # 단계 4: 로그 수집
        log_agent(
            agent_name="dialogue",
            state=state,
            model_output={
                "validated_count": len(validated_dialogues),
                "validation_results": validation_results,
                "dialogues": [{"speaker": d.speaker, "text": d.text} for d in validated_dialogues]
            },
            start_time=start_time,
            llm_model="gpt-4o-mini",  # Dialogue Agent uses gpt-4o-mini for validation
        )

        print(f"[DIALOGUE] process() end", flush=True)
        return _finish(state, "completed")

    # ============================================================
    # 🔍 대사 검증 파이프라인
    # ============================================================
    def _validate_dialogue(self, dialogue: Dialogue, state: AgentState) -> Dict:
        """대사 검증"""
        print(f"[DIALOGUE] _validate_dialogue: use_llm={self.use_llm}", flush=True)

        if self.use_llm:
            print(f"[DIALOGUE] Calling _validate_with_llm", flush=True)
            result = self._validate_with_llm(dialogue, state)
            if result:
                return result

        # LLM 실패 시 규칙 기반 검증
        print(f"[DIALOGUE] Calling _validate_with_rules", flush=True)
        result = self._validate_with_rules(dialogue, state)
        print(f"[DIALOGUE] _validate_with_rules returned", flush=True)
        return result

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

    # ============================================================
    # ✏️ 대사 자동 수정
    # ============================================================
    def _correct_dialogue(self, dialogue: Dialogue, state: AgentState,
                         validation_result: Dict) -> Optional[Dialogue]:
        """대사 자동 수정"""
        if not self.use_llm:
            return None

        try:
            issues = validation_result.get("issues", [])
            suggestions = validation_result.get("suggestions") or "대사를 상황에 맞게 다듬어 주세요."

            issues_block = "\n".join(f"- {issue}" for issue in issues) if issues else "- 자연스럽게 다듬어 주세요."
            system_prompt = _DIALOGUE_CORRECTION_TEMPLATE.format(
                speaker=dialogue.speaker,
                issues_block=issues_block,
                suggestions=suggestions,
            )

            character_info = self._get_character_info(dialogue.speaker)

            user_prompt = f"""원본 대사: "{dialogue.content}"
캐릭터 성격: {character_info.get('personality', '')}
감정: {dialogue.emotion}
씬: {state.scene.current_scene}

수정된 대사만 출력하세요 (따옴표 없이):"""

            correction_temperature = self.llm_client.get_agent_setting(
                "dialogue",
                "correction_temperature",
                self.llm_client.get_agent_setting("dialogue", "temperature", 0.7),
            )
            correction_max_tokens = self.llm_client.get_agent_setting("dialogue", "correction_max_tokens", 100)

            corrected_content = self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=correction_temperature,
                max_tokens=correction_max_tokens,
                agent="dialogue",
            )

            # 새 대화 객체 생성
            return Dialogue(
                speaker=dialogue.speaker,
                content=corrected_content.strip().strip('"').strip("'"),
                emotion=dialogue.emotion,
                emotion_intensity=dialogue.emotion_intensity,
                affinity_level=dialogue.affinity_level
            )

        except Exception as e:
            print(f"대사 수정 실패: {str(e)}")
            return None

    # ============================================================
    # 📚 캐릭터 정보/멀티 대화 유틸
    # ============================================================
    def _get_character_info(self, speaker: str) -> Dict:
        """캐릭터 정보 가져오기"""
        # 간단한 캐릭터 정보 (실제로는 데이터베이스에서 가져옴)
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

# ============================================================
# 🚀 모듈 수준 엔트리 포인트
# ============================================================
def run_dialogue_agent(state: AgentState) -> AgentState:
    """
    Dialogue Agent 실행 함수 (Simplified for Blueprint 5)
    GraphState dict 구조에 맞춰 간소화
    """
    print(f"[DIALOGUE] Formatting output...")

    agent_responses = state.get("agent_responses", [])
    if not agent_responses:
        print(f"[DIALOGUE] No agent_responses, skipping output update")
    else:
        if "output" not in state:
            state["output"] = {}

        if "dialogues" not in state["output"]:
            state["output"]["dialogues"] = []

        state["output"]["dialogues"] = agent_responses.copy()
        print(f"[DIALOGUE] Updated output with {len(agent_responses)} new dialogues")

        state["agent_responses"] = []

    # 엔딩 상태 확인
    current_stage = state.get("current_stage") or ""
    final_ending = state.get("final_ending")

    if final_ending or (current_stage and "ending" in current_stage.lower()):
        # 엔딩에 도달한 경우에만 종료
        state["next_node"] = "END"
        print(f"[DIALOGUE] Ending reached: {current_stage}")
    else:
        # 대화 계속 진행 - 라우터로 돌아가서 다음 사용자 입력 대기
        state["next_node"] = "router"
        print(f"[DIALOGUE] Continuing conversation...")

    print(f"[DIALOGUE] Output formatted. Dialogues: {len(state['output'].get('dialogues', []))}")
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
