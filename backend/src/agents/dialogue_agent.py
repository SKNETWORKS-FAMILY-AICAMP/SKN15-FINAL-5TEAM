from datetime import datetime
import time
from typing import Dict, List, Optional

from src.core.graph_state import AgentState, Dialogue
from src.services import DialogueValidationService, DialogueCorrectionService
from src.services.dialogue_image_service import get_dialogue_image_service
from src.utils.llm_client import get_llm_client
from src.tools.training_logger import log_agent
from src.database.db_manager import DatabaseManager

# ============================================================
# 🗣️ DialogueAgent — children_agent가 만든 대사를 검증·미세조정
# ============================================================

class DialogueAgent:
    # ============================================================
    # 🛠️ 초기화
    # ============================================================
    def __init__(self, use_llm: bool = True, enable_multi_conversation: bool = False, db_manager: DatabaseManager = None):
        """Dialogue Agent 초기화"""
        self.use_llm = use_llm
        self.enable_multi_conversation = enable_multi_conversation
        self.db_manager = db_manager  # 이미지 매핑용 DB 접근

        # 🆕 Service layer initialization
        llm_client = None
        if self.use_llm:
            try:
                llm_client = get_llm_client()
            except Exception as e:
                print(f"LLM 클라이언트 초기화 실패: {str(e)}")
                self.use_llm = False

        self._validation_service = DialogueValidationService(llm_client=llm_client)
        self._correction_service = DialogueCorrectionService(llm_client=llm_client)

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
        validated_dialogues = []
        validation_results = []

        print(f"[DIALOGUE] Starting validation loop", flush=True)
        for dialogue in state.output.dialogues:
            print(f"[DIALOGUE] Validating dialogue from {dialogue.speaker} (order: {dialogue.order})", flush=True)
            # 🆕 Use validation service
            validation_result = self._validation_service.validate_dialogue(dialogue, state, use_llm=self.use_llm)
            validation_results.append(validation_result)

            # 검증 통과 시 그대로 사용, 실패 시 수정
            if validation_result["passed"]:
                validated_dialogues.append(dialogue)
            else:
                # 🆕 Use correction service
                corrected = self._correction_service.correct_dialogue(dialogue, state, validation_result)
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

        # Phase 4: 로그 수집
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
    # 📚 멀티 대화 유틸
    # ============================================================
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

    # 🖼️ 이미지 선택 (이벤트 감지 + DB 기반 매핑) - Service layer 사용
    db_manager = state.get("db_manager")
    if db_manager and state.get("output", {}).get("dialogues"):
        try:
            image_service = get_dialogue_image_service(db_manager=db_manager)
            selected_image = image_service.select_image_for_dialogue(
                state=state,
                dialogues=state["output"]["dialogues"]
            )

            if selected_image:
                state["current_image"] = selected_image
                print(f"[DIALOGUE] 🖼️ Image selected: {selected_image}")
        except Exception as e:
            print(f"[DIALOGUE] ⚠️ Image selection failed: {e}")

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
