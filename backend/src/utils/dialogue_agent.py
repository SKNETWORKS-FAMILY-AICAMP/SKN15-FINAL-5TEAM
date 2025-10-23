# Dialogue Agent - 대사 품질 검증
"""
Dialogue Agent - Parent와 Children에서 생성된 대사의 품질 검증
- 캐릭터 일관성 확인
- 문맥 적합성 확인
- 게임 규칙 준수 확인
- GPT-4를 활용한 고품질 검증
"""

from typing import Dict, List, Optional
from datetime import datetime
import time
from src.core.graph_state import AgentState, Dialogue
from src.utils.llm_client import get_llm_client
from src.utils.multi_character_conversation import MultiCharacterConversation

class DialogueAgent:
    def __init__(self, use_llm: bool = True, enable_multi_conversation: bool = True):
        """Dialogue Agent 초기화"""
        self.use_llm = use_llm
        self.enable_multi_conversation = enable_multi_conversation

        if self.use_llm:
            try:
                self.llm_client = get_llm_client()
            except Exception as e:
                print(f"LLM 클라이언트 초기화 실패: {str(e)}")
                self.use_llm = False

        # 멀티캐릭터 대화 시스템
        if self.enable_multi_conversation:
            try:
                self.multi_conv = MultiCharacterConversation()
            except Exception as e:
                print(f"멀티캐릭터 대화 시스템 초기화 실패: {str(e)}")
                self.enable_multi_conversation = False

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

        print(f"[DIALOGUE] process() end", flush=True)
        return _finish(state, "completed")

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
            system_prompt = """당신은 게임 대사의 품질을 검증하는 AI입니다.
다음 기준으로 대사를 평가하세요:

1. character_consistency (40%): 캐릭터 성격과 말투가 일관되는가?
2. context_relevance (30%): 현재 게임 상황과 문맥에 적합한가?
3. emotional_appropriateness (20%): 감정 표현이 자연스럽고 적절한가?
4. game_rule_compliance (10%): 게임 규칙을 위반하지 않는가?

각 기준을 0-100점으로 평가하고, 전체 점수가 70점 이상이면 합격입니다."""

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

            response = self.llm_client.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2
            )

            return response

        except Exception as e:
            print(f"LLM 검증 실패: {str(e)}")
            return None

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

    def _correct_dialogue(self, dialogue: Dialogue, state: AgentState,
                         validation_result: Dict) -> Optional[Dialogue]:
        """대사 자동 수정"""
        if not self.use_llm:
            return None

        try:
            issues = validation_result.get("issues", [])
            suggestions = validation_result.get("suggestions", "")

            system_prompt = f"""당신은 게임 캐릭터 '{dialogue.speaker}'입니다.
다음 문제점을 해결하여 대사를 개선하세요:
{chr(10).join(f'- {issue}' for issue in issues)}

개선 제안: {suggestions}

캐릭터 성격과 현재 상황에 맞게 자연스럽게 수정하세요."""

            character_info = self._get_character_info(dialogue.speaker)

            user_prompt = f"""원본 대사: "{dialogue.content}"
캐릭터 성격: {character_info.get('personality', '')}
감정: {dialogue.emotion}
씬: {state.scene.current_scene}

수정된 대사만 출력하세요 (따옴표 없이):"""

            corrected_content = self.llm_client.call(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=100
            )

            # 새 Dialogue 객체 생성
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
        멀티캐릭터 대화 추가 (특정 씬 종료 시)

        다음 조건일 때 멀티캐릭터 대화 자동 생성:
        1. cutscene5_akaza_encounter 종료 시 (victory 또는 recruit)
        2. cutscene6_mind_on_fire 종료 시 (final victory)
        """
        # temp_data에서 대화 횟수 설정 확인
        num_exchanges = state.game.temp_data.get("follow_up_conversation", 0)

        if num_exchanges <= 0:
            # 기본값: 특정 플래그가 있을 때만 자동 생성
            if not hasattr(state.game, 'flags'):
                return

            flags = state.game.flags

            # 컷신5 승리 후
            if "cutscene5_victory" in flags and "multi_conv_cutscene5_victory" not in flags:
                num_exchanges = 4
                scene_key = "cutscene5_victory"
                state.game.flags.append("multi_conv_cutscene5_victory")

            # 컷신5 동료 규합 후
            elif "inosuke_recruited" in flags and "zenitsu_recruited" in flags and "multi_conv_cutscene5_recruit" not in flags:
                num_exchanges = 4
                scene_key = "cutscene5_recruit"
                state.game.flags.append("multi_conv_cutscene5_recruit")

            # 컷신6 최종 승리 후
            elif "cutscene6_final_victory" in flags and "multi_conv_cutscene6_final" not in flags:
                num_exchanges = 4
                scene_key = "cutscene6_final"
                state.game.flags.append("multi_conv_cutscene6_final")

            # 컷신5 패배 후
            elif "cutscene5_defeat" in flags and "multi_conv_cutscene5_defeat" not in flags:
                num_exchanges = 4
                scene_key = "cutscene5_defeat"
                state.game.flags.append("multi_conv_cutscene5_defeat")

            else:
                return  # 조건 미충족 시 멀티캐릭터 대화 생성하지 않음

        else:
            # play.py에서 --follow-up-conversation 옵션으로 명시적 요청
            # 현재 씬 기반으로 scene_key 결정
            current_scene = state.game.scene_id

            # 씬 ID → conversation scene_key 매핑
            scene_mapping = {
                "cutscene5_akaza": "cutscene5_victory",
                "cutscene6_mind_fire": "cutscene6_final",
            }

            scene_key = scene_mapping.get(current_scene, None)

            if not scene_key:
                print(f"[MULTI_CONV] No scene mapping for {current_scene}, skipping")
                return

        print(f"\n[MULTI_CONV] Generating {num_exchanges} multi-character exchanges for '{scene_key}'", flush=True)

        try:
            # 멀티캐릭터 대화 생성 및 상태에 적용
            self.multi_conv.apply_to_state(
                state=state,
                scene_key=scene_key,
                num_exchanges=num_exchanges,
                use_llm=self.use_llm
            )

        except Exception as e:
            print(f"[MULTI_CONV] Error generating conversation: {e}", flush=True)

def run_dialogue_agent(state: AgentState) -> AgentState:
    """
    Dialogue Agent 실행 함수 (Simplified for Blueprint 5)
    GraphState dict 구조에 맞춰 간소화
    """
    print(f"[DIALOGUE] Formatting output...")

    # agent_responses가 비어있으면 대화 생성 없음
    agent_responses = state.get("agent_responses", [])
    if not agent_responses:
        print(f"[DIALOGUE] No agent_responses, skipping output update")
    else:
        # agent_responses를 output.dialogues로 복사
        if "output" not in state:
            state["output"] = {}

        if "dialogues" not in state["output"]:
            state["output"]["dialogues"] = []

        # 🔥 배치 모드 지원: has_more_dialogues가 True면 agent_responses 전체를 사용
        # (children_agent가 이미 배치 크기만큼만 생성함)
        state["output"]["dialogues"] = agent_responses.copy()
        print(f"[DIALOGUE] Updated output with {len(agent_responses)} new dialogues")

        # agent_responses 초기화 (다음 배치를 위해)
        state["agent_responses"] = []

    # 엔딩 상태 확인
    current_stage = state.get("current_stage") or ""
    final_ending = state.get("final_ending")

    if final_ending or (current_stage and "ending" in current_stage.lower()):
        # 엔딩에 도달한 경우에만 종료
        state["next_node"] = "END"
        print(f"[DIALOGUE] Ending reached: {current_stage}")
    else:
        # 대화 계속 진행 - Router로 돌아가서 다음 사용자 입력 대기
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
