# 3. Parent Agent 구현 (핵심 게임 로직)

"""
Parent Agent - 메인 게임 로직 처리
- Scene Tools와 State Tools 연동
- 턴 관리 및 친밀도 시스템
- 히든엔딩 조건 판단
- Children Agent용 대화 규칙 생성
"""

from typing import Dict, List, Optional, Tuple
import json
import os
from datetime import datetime
from src.core.graph_state import (
    AgentState,
    ParentDecisions,
    SceneToolRequest,
    StateToolRequest,
    NodeType,
)
from src.utils.llm_client import get_llm_client
from src.utils.debug_logging import get_logger
from src.utils.affinity_calculator import affinity_calculator
from src.utils.mission_manager import MissionManager, MissionStatus


def _debug_print(msg: str):
    """DEBUG 모드일 때만 출력"""
    if os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]:
        print(msg)


def _match_keywords_with_llm(
    user_input: str,
    keywords: List[str],
    context: str = "",
    confidence_threshold: int = 70,
) -> Tuple[bool, int, str]:
    """
    🔥 LLM을 사용하여 유저 입력이 키워드 의도와 매칭되는지 판단

    Args:
        user_input: 유저의 자연어 입력
        keywords: 매칭할 키워드 목록
        context: 상황 설명 (예: "이노스케를 설득하는 상황")
        confidence_threshold: 매칭으로 간주할 최소 신뢰도 (0-100)

    Returns:
        (매칭 여부, 신뢰도, 판단 이유)
    """
    use_llm = os.getenv("USE_LLM", "true").lower() in ["true", "1", "yes"]

    if not use_llm or not keywords:
        # LLM 미사용 시 폴백: 단순 문자열 검사
        user_input_lower = user_input.lower()
        matched = any(kw.lower() in user_input_lower for kw in keywords)
        return (matched, 100 if matched else 0, "Simple string matching")

    try:
        llm_client = get_llm_client()

        keywords_str = ", ".join(f'"{kw}"' for kw in keywords)

        system_prompt = """당신은 사용자의 자연어 입력을 분석하여 특정 키워드나 의도와 매칭되는지 판단하는 AI입니다.

**판단 기준**:
1. 사용자 입력이 키워드의 의미나 의도와 일치하는가?
2. 직접적인 단어 일치뿐만 아니라 유사한 표현, 동의어, 맥락적 의미도 고려
3. 특히 "비교" 표현 인식: "A보다 약하다", "B만큼 못하다", "C같지 않다"
4. 자존심을 건드리는 도발적 표현 인식
5. 신뢰도(confidence)는 0-100 사이의 정수

**응답 형식**:
```json
{
  "matched": true 또는 false,
  "confidence": 0-100 (정수),
  "reasoning": "판단 이유를 한 문장으로"
}
```

**예시**:
- 키워드: ["약하다", "겁쟁이"]
  입력: "너 정도는 아무것도 아니야"
  → matched: true, confidence: 75 (도발적 의미가 유사함)

- 키워드: ["약하다", "보다"]
  입력: "너 저 오니보다 약할 것 같은데"
  → matched: true, confidence: 90 (비교를 통한 도발, 자존심 자극)

- 키워드: ["못하다", "질"]
  입력: "너는 렌고쿠만큼 강하지 못할 거야"
  → matched: true, confidence: 85 (능력 비하, 자존심 자극)

- 키워드: ["네즈코", "위험"]
  입력: "네즈코를 지키러 가자"
  → matched: true, confidence: 95 (직접적으로 일치)"""

        user_prompt = f"""**상황**: {context if context else "일반 대화"}

**키워드 목록**: {keywords_str}

**사용자 입력**: "{user_input}"

사용자 입력이 키워드의 의도와 매칭되는지 분석해주세요."""

        response = llm_client.call_json(
            system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1
        )

        matched = response.get("matched", False)
        confidence = response.get("confidence", 0)
        reasoning = response.get("reasoning", "")

        print(
            f"[LLM_KEYWORD] Matched: {matched}, Confidence: {confidence}%, Reasoning: {reasoning}"
        )

        return (matched and confidence >= confidence_threshold, confidence, reasoning)

    except Exception as e:
        print(f"[LLM_KEYWORD] LLM 매칭 실패, 폴백 사용: {e}")
        # 폴백: 단순 문자열 검사
        user_input_lower = user_input.lower()
        matched = any(kw.lower() in user_input_lower for kw in keywords)
        return (matched, 100 if matched else 0, "Fallback string matching")


def _generate_dialogue_with_children(
    state: Dict,
    speakers: List[str],
    contents: List[str],
    emotions: List[str],
    stage_type: str = "cutscene",
) -> Dict:
    """
    🔥 Children Agent를 사용하여 LLM 기반 대사 생성

    Args:
        state: 현재 게임 상태
        speakers: 발화자 목록
        contents: 대사 템플릿/컨텍스트 목록
        emotions: 감정 목록
        stage_type: 스테이지 타입 (cutscene, choice, mission)

    Returns:
        업데이트된 state
    """
    use_llm = os.getenv("USE_LLM", "true").lower() in ["true", "1", "yes"]

    if not use_llm:
        # LLM 미사용 시 하드코딩된 대사 사용
        for i, speaker in enumerate(speakers):
            if speaker != "system":
                state["agent_responses"].append(
                    {
                        "speaker": speaker,
                        "text": contents[i] if i < len(contents) else "",
                        "emotion": emotions[i] if i < len(emotions) else "neutral",
                    }
                )
            else:
                state["agent_responses"].insert(
                    0,
                    {
                        "speaker": "시스템",
                        "text": contents[i] if i < len(contents) else "",
                    },
                )
        return state

    # LLM으로 대사 생성
    try:
        llm_client = get_llm_client()
        user_name = state.get("user_name", "여행자")
        current_stage = state.get("current_stage", "unknown")
        affinity_scores = state.get("affinity_scores", {})

        # 캐릭터 데이터 로드
        char_db_path = "data/characters_db.json"
        with open(char_db_path, "r", encoding="utf-8") as f:
            characters_data = json.load(f).get("characters", {})

        for i, speaker in enumerate(speakers):
            if speaker == "system":
                # 시스템 나레이션은 그대로 사용
                state["agent_responses"].insert(
                    0,
                    {
                        "speaker": "시스템",
                        "text": contents[i] if i < len(contents) else "",
                    },
                )
                continue

            # 캐릭터 데이터 가져오기
            char_data = characters_data.get(speaker.lower(), {})
            char_name_kr = char_data.get("name_kr", speaker)
            personality = char_data.get("personality", "")

            # 친밀도에 따른 말투 결정
            affinity = affinity_scores.get(speaker.lower(), 0)
            if affinity <= 200:
                tone_level = "low"
            elif affinity <= 600:
                tone_level = "mid"
            else:
                tone_level = "high"

            tone_data = char_data.get("tone_by_affinity", {}).get(tone_level, {})
            tone_style = tone_data.get("style", "")
            calling = tone_data.get("calling", "님")

            # 대사 컨텍스트 (원본 대사를 참고용으로 전달)
            original_text = contents[i] if i < len(contents) else ""
            emotion = emotions[i] if i < len(emotions) else "neutral"

            # LLM 프롬프트 구성
            system_prompt = f"""당신은 귀멸의 칼날 캐릭터 '{char_name_kr}'입니다.

**캐릭터 정보**:
- 이름: {char_name_kr}
- 성격: {personality}
- 현재 친밀도: {affinity}/1000 (레벨: {tone_level})
- 말투 스타일: {tone_style}
- 호칭: {calling}

**지침**:
1. 사용자 이름은 "{user_name}"입니다. 대화에서 사용자를 언급할 때 이 이름을 사용하세요.
2. 친밀도에 맞는 호칭과 말투를 사용하세요.
3. 현재 감정({emotion})을 대사에 반영하세요.
4. 캐릭터의 성격을 유지하면서 자연스러운 대사를 생성하세요.
5. 이모지는 사용하지 마세요.
6. 1-2문장으로 간결하게 작성하세요.

**참고 대사** (이것을 변형하여 사용하세요):
"{original_text}"

위 참고 대사의 의도와 맥락을 유지하되, 사용자 이름과 친밀도를 반영하여 자연스럽게 재작성하세요."""

            user_prompt = f"현재 상황: {current_stage}\n감정: {emotion}\n\n'{char_name_kr}'로서 대사를 생성해주세요."

            # LLM 호출
            response = llm_client.call(
                system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.7
            )

            generated_text = response.strip()

            # 대사 추가
            state["agent_responses"].append(
                {"speaker": speaker, "text": generated_text, "emotion": emotion}
            )

            print(f"[CHILDREN] {char_name_kr} 대사 생성 완료 (친밀도: {affinity})")

    except Exception as e:
        print(f"[CHILDREN] LLM 대사 생성 실패, 원본 사용: {e}")
        # 실패 시 원본 대사 사용
        for i, speaker in enumerate(speakers):
            if speaker != "system":
                state["agent_responses"].append(
                    {
                        "speaker": speaker,
                        "text": contents[i] if i < len(contents) else "",
                        "emotion": emotions[i] if i < len(emotions) else "neutral",
                    }
                )
            else:
                state["agent_responses"].insert(
                    0,
                    {
                        "speaker": "시스템",
                        "text": contents[i] if i < len(contents) else "",
                    },
                )

    return state


def _match_choice_with_llm(
    user_input: str, choices: List[Dict], state: Dict
) -> Optional[Dict]:
    """
    🔥 LLM을 사용하여 유저의 자연어 입력을 선택지와 매칭

    Args:
        user_input: 유저의 자연어 입력
        choices: 선택지 목록
        state: 현재 게임 상태

    Returns:
        매칭된 선택지 또는 None
    """
    use_llm = os.getenv("USE_LLM", "true").lower() in ["true", "1", "yes"]
    if not use_llm or not choices:
        return None

    try:
        # 선택지 정보 구성
        choices_info = []
        for i, choice in enumerate(choices):
            choice_id = choice.get("id", f"choice_{i}")
            text = choice.get("text", "")
            description = choice.get("description", "")
            choices_info.append(
                f"{i + 1}. ID: {choice_id}\n   텍스트: {text}\n   설명: {description}"
            )

        choices_str = "\n\n".join(choices_info)

        system_prompt = """당신은 유저의 자연어 입력을 분석하여 게임 선택지와 매칭하는 AI입니다.

유저가 입력한 자연어를 분석하여, 아래 선택지 중 어떤 것과 가장 일치하는지 판단하세요.

**판단 기준**:
1. 유저의 의도와 선택지의 의미가 일치하는가?
2. 키워드가 일치하는가?
3. 맥락상 적절한가?

**응답 형식**:
```json
{
  "matched_choice_id": "선택지 ID" 또는 null,
  "confidence": 0-100 (확신도),
  "reasoning": "판단 이유"
}
```

확신도가 70 이상일 때만 매칭으로 간주합니다."""

        user_prompt = f"""**유저 입력**: "{user_input}"

**선택지 목록**:
{choices_str}

유저 입력을 분석하여 가장 일치하는 선택지를 찾아주세요."""

        llm_client = get_llm_client()
        response = llm_client.call_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # 낮은 온도로 정확성 향상
        )

        matched_id = response.get("matched_choice_id")
        confidence = response.get("confidence", 0)

        print(f"[PARENT] LLM choice matching: {matched_id} (confidence: {confidence}%)")
        print(f"[PARENT] Reasoning: {response.get('reasoning', 'N/A')}")

        if matched_id and confidence >= 70:
            # 매칭된 선택지 찾기
            for choice in choices:
                if choice.get("id") == matched_id:
                    return choice

    except Exception as e:
        print(f"[PARENT] LLM choice matching failed: {e}")

    return None


def _match_choice_with_keywords(user_input: str, choices: List[Dict]) -> Optional[Dict]:
    """
    키워드 기반 폴백 매칭

    Args:
        user_input: 유저 입력
        choices: 선택지 목록

    Returns:
        매칭된 선택지 또는 None
    """
    user_lower = user_input.lower()

    for choice in choices:
        intent_keywords = choice.get("intent_keywords", [])

        # 키워드 매칭
        for keyword in intent_keywords:
            if keyword.lower() in user_lower:
                print(f"[PARENT] Keyword match: '{keyword}' → {choice.get('id')}")
                return choice

    return None


class ParentAgent:
    def __init__(
        self,
        use_llm: bool = True,
        debug: bool = False,
        config_path: str = "config/parent_config.json",
    ):
        """
        🔄 Parent Agent 초기화 (완전 동적 처리)

        - 모든 설정은 시나리오 JSON에서 로드
        - 하드코딩된 씬/캐릭터/조건 제거
        """
        self.use_llm = use_llm
        self.logger = get_logger(enabled=debug, verbose=debug)
        self.config = self._load_config(config_path)

        if self.use_llm:
            try:
                self.llm_client = get_llm_client()
            except Exception as e:
                _debug_print(
                    f"LLM 클라이언트 초기화 실패, 규칙 기반으로 전환: {str(e)}"
                )
                self.use_llm = False

    def _detect_stage_cycle(
        self, stages: dict, current: str, visited: set = None
    ) -> bool:
        """스테이지 순환 참조 감지"""
        if visited is None:
            visited = set()

        if current in visited:
            self.logger.error(f"Stage cycle detected: {current}")
            return True

        visited.add(current)

        if current in stages:
            stage_data = stages[current]
            next_stage = stage_data.get("next") or stage_data.get("next_stage")
            if next_stage:
                return self._detect_stage_cycle(stages, next_stage, visited.copy())

        return False

    def _load_config(self, config_path: str) -> Dict:
        """Parent Agent 설정 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.log(
                "Parent",
                "config_not_found",
                {"path": config_path, "using_defaults": True},
            )
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """기본 설정 (하드코딩 방지용)"""
        return {
            "main_guide_character": "tanjiro",
            "default_available_characters": ["tanjiro"],
            "mission": {"auto_target_on_keyword": True, "auto_move_cost": 0},
        }

    def process(self, state: AgentState) -> AgentState:
        """
        🔄 Parent Agent 메인 처리 (시나리오 JSON 기반)
        """
        # 🔥 무한 루프 방지: 처리 깊이 체크
        process_depth = state.game.temp_data.get("_process_depth", 0)
        if process_depth > 10:
            _debug_print(f"❌ 무한 루프 감지! process_depth={process_depth}")
            state.output.add_system_message(
                "시스템 오류가 발생했습니다. 게임을 재시작해주세요."
            )
            return state

        state.game.temp_data["_process_depth"] = process_depth + 1

        self.logger.log(
            "Parent",
            "process_start",
            {
                "stage": state.game.current_stage,
                "turn": state.game.turn,
                "user_input": state.user_input.content,
                "flags": list(state.game.flags),
                "depth": process_depth + 1,
            },
        )

        # 🔄 시나리오 데이터 확인
        if not state.game.scenario_data:
            print("❌ 시나리오 데이터가 로드되지 않음")
            state.error = {"message": "시나리오 데이터 없음"}
            state.next_node = "wait_user_input"
            return state

        # 🔥 ParentDecisions 초기화 (None인 경우)
        if not state.parent_decisions:
            state.parent_decisions = ParentDecisions()

        # 1. State Tools로 현재 상태 업데이트 요청
        state = self._request_state_update(state)

        # 🔄 2. 현재 스테이지 정보 가져오기
        current_stage_id = state.game.current_stage
        stages = state.game.scenario_data.get("stages", {})
        current_stage_data = stages.get(current_stage_id, {})

        if not current_stage_data:
            _debug_print(f"❌ 스테이지를 찾을 수 없음: {current_stage_id}")
            state.error = {"message": f"스테이지 없음: {current_stage_id}"}
            state.next_node = "wait_user_input"
            return state

        stage_type = current_stage_data.get("type")

        self.logger.log(
            "Parent",
            "stage_info",
            {
                "stage_id": current_stage_id,
                "stage_type": stage_type,
                "entered_flag": state.game.has_flag(f"{current_stage_id}_entered"),
                "completed_flag": state.game.has_flag(f"{current_stage_id}_completed"),
            },
        )

        # 🔄 3. 스테이지 타입별 처리 (JSON 기반)
        if stage_type == "cutscene":
            state = self._handle_cutscene_stage(state, current_stage_data)
        elif stage_type == "choice":
            state = self._handle_choice_stage(state, current_stage_data)
        elif stage_type == "mission":
            state = self._handle_mission_stage(state, current_stage_data)
        elif stage_type == "branch":
            state = self._handle_branch_stage(state, current_stage_data)
        elif stage_type == "ending":
            state = self._handle_ending_stage(state, current_stage_data)
        else:
            _debug_print(f"⚠️ 알 수 없는 스테이지 타입: {stage_type}")
            state = self._handle_generic_stage(state, current_stage_data)

        # 🔥 4. Children Agent용 대화 규칙 설정 (스테이지 전환 전에!)
        state = self._set_dialogue_rules(state)

        # 5. Scene Tools 요청 (이미지/컷신)
        state = self._request_scene_assets(state)

        # 6. 다음 스테이지로 전환 여부 확인 (대화 규칙 설정 후!)
        state = self._check_stage_transition(state, current_stage_data)

        # 7. 히든엔딩 조건 확인
        state = self._check_ending_conditions(state)

        # 처리 완료
        state.meta.processed_by = "parent_agent"
        state.meta.timestamp = datetime.now().isoformat()
        state.next_node = NodeType.CHILDREN.value

        # 🔥 처리 깊이는 여기서 리셋하지 않음 (dialogue_agent에서 리셋)
        # _process_depth는 워크플로우 전체 깊이 추적용

        return state

    def _request_state_update(self, state: AgentState) -> AgentState:
        """State Tools에 상태 업데이트 요청"""
        # 🔥 턴 증가는 dialogue_agent에서 처리 (중복 방지)
        # 친밀도 등 업데이트만 수행
        updates = {"last_action": f"user_input_turn_{state.game.turn}"}

        # 사용자 선택에 따른 친밀도 변화
        affinity_changes = self._calculate_affinity_changes(state)

        state.state_tool_request = StateToolRequest(
            action="update_state", updates=updates, character_updates=affinity_changes
        )

        return state

    def _handle_cutscene_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """
        🔥 컷신 스테이지 처리 - 다중 대화 지원 (방안 B)

        Parent Agent 역할:
        1. 현재 턴의 대화 정보 파싱 (speakers/contents/emotions)
        2. list 형태로 dialogue_context 설정
        3. user_prompt 저장
        """
        # 🔥 첫 진입 시
        if not state.game.has_flag(f"{state.game.current_stage}_entered"):
            self.logger.log(
                "Parent",
                "cutscene_first_entry",
                {"stage": state.game.current_stage, "turn": state.game.turn},
            )

            state.output.narration = (
                f"=== {state.game.scenario_data.get('title', '컷신')} ==="
            )
            state.game.add_flag(f"{state.game.current_stage}_entered")

        # 현재 턴의 대사 정보 가져오기
        dialogues = stage_data.get("dialogues", [])
        current_turn = state.game.turn
        turn_dialogue = next(
            (d for d in dialogues if d.get("turn") == current_turn), None
        )

        if not turn_dialogue:
            # 더 이상 대사가 없으면 완료
            state.game.add_flag(f"{state.game.current_stage}_completed")
            next_stage = stage_data.get("next_stage")
            if next_stage:
                print(
                    f"[PARENT] cutscene completed, transitioning: {state.game.current_stage} → {next_stage}",
                    flush=True,
                )
                state.game.stage_history.append(next_stage)
                state.game.current_stage = next_stage
            return state

        # 🔥 새로운 JSON 구조 파싱: speakers/contents/emotions
        speakers = turn_dialogue.get("speakers", [])
        contents = turn_dialogue.get("contents", [])
        emotions = turn_dialogue.get("emotions", [])
        user_prompt = turn_dialogue.get("user_prompt", "입력하세요")

        # 여러 캐릭터 대사를 list로 전달
        dialogue_list = []
        for i, speaker in enumerate(speakers):
            dialogue_list.append(
                {
                    "speaker": speaker,
                    "situation": contents[i] if i < len(contents) else "",
                    "emotion": emotions[i] if i < len(emotions) else "neutral",
                    "order": i,
                }
            )

        state.parent_decisions.dialogue_context = dialogue_list
        state.parent_decisions.user_input_prompt = user_prompt
        state.characters.available_characters = [s for s in speakers if s != "system"]

        print(
            f"[PARENT] Multi-speaker setup: {len(dialogue_list)} dialogues for turn {current_turn}",
            flush=True,
        )

        return state

    def _handle_choice_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """
        🔥 선택지 스테이지 처리 - 다중 대화 지원 (방안 B)

        JSON 구조:
        {
            "type": "choice",
            "pre_choice_speakers": ["system", "tanjiro", "tanjiro"],
            "pre_choice_contents": [...],
            "pre_choice_emotions": [...],
            "user_prompt": "...",
            "choices": [...]
        }
        """
        # 🔥 첫 진입 시 pre_choice 대화 표시
        if not state.game.has_flag(f"{state.game.current_stage}_entered"):
            # 🔥 새로운 JSON 구조 파싱: pre_choice_speakers/contents/emotions
            speakers = stage_data.get("pre_choice_speakers", [])
            contents = stage_data.get("pre_choice_contents", [])
            emotions = stage_data.get("pre_choice_emotions", [])
            user_prompt = stage_data.get("user_prompt", "선택하세요")

            if speakers:
                # 여러 캐릭터 대사를 list로 전달
                dialogue_list = []
                for i, speaker in enumerate(speakers):
                    dialogue_list.append(
                        {
                            "speaker": speaker,
                            "situation": contents[i] if i < len(contents) else "",
                            "emotion": emotions[i] if i < len(emotions) else "neutral",
                            "order": i,
                        }
                    )

                state.parent_decisions.dialogue_context = dialogue_list
                state.parent_decisions.user_input_prompt = user_prompt
                state.characters.available_characters = [
                    s for s in speakers if s != "system"
                ]
            else:
                # 폴백: 기존 방식
                guide_char = stage_data.get(
                    "guide_character",
                    self.config.get("main_guide_character", "tanjiro"),
                )
                state.characters.available_characters = [guide_char]

                state.parent_decisions.dialogue_context = [
                    {
                        "speaker": guide_char,
                        "emotion": "worried",
                        "situation": "어떻게 할지 생각해봐...",
                        "order": 0,
                    }
                ]
                state.parent_decisions.user_input_prompt = "선택하세요"

            # 🔥 선택지 정보를 시스템 메시지로 출력
            choices = stage_data.get("choices", [])
            if choices:
                choice_text = "\n\n💡 선택지:\n"
                for choice in choices:
                    text = choice.get("text", "")
                    preview = choice.get("preview", "")
                    if preview:
                        choice_text += f"   {text}\n      {preview}\n"
                    else:
                        choice_text += f"   {text}\n"

                state.output.add_system_message(choice_text)

            state.parent_decisions.speaking_rules["guide_mode"] = False
            state.parent_decisions.speaking_rules["allow_variation"] = True
            state.game.add_flag(f"{state.game.current_stage}_entered")
            # 🔥 선택 대기 플래그 추가 (다음 입력에서 선택 처리)
            state.game.add_flag(f"{state.game.current_stage}_awaiting_choice")

            self.logger.log(
                "Parent",
                "choice_first_entry_complete",
                {
                    "stage": state.game.current_stage,
                    "dialogue_context_set": True,
                    "pre_dialogues": len(speakers) if speakers else 0,
                    "awaiting_choice": True,
                },
            )

            return state

        # 🔥 두 번째 입력: 선택 대기 중이 아니면 스킵 (dialogue_context 초기화 방지)
        if not state.game.has_flag(f"{state.game.current_stage}_awaiting_choice"):
            # 이미 선택이 완료되었거나, 선택 대기 중이 아님
            self.logger.log(
                "Parent",
                "choice_already_completed",
                {
                    "stage": state.game.current_stage,
                    "user_input": state.user_input.content[:50],
                },
            )
            return state

        # 🔥 사용자 입력에서 의도 파악 (LLM 기반 의미 매핑, confidence >= 0.75)
        # (이미 fork_entered 플래그가 있는 경우에만 실행됨)
        user_input = state.user_input.content.lower()
        choices = stage_data.get("choices", [])

        self.logger.log(
            "Parent",
            "choice_user_input",
            {"input": user_input, "available_choices": len(choices)},
        )

        matched_choice = None
        best_confidence = 0.0

        if self.use_llm and choices:
            # LLM으로 의미 매핑
            try:
                choice_descriptions = [
                    f"{i + 1}. {c.get('text', '')}: {', '.join(c.get('intent_keywords', []))}"
                    for i, c in enumerate(choices)
                ]

                prompt = f"""사용자의 발화 의도를 정확히 분석하여 가장 적합한 선택지를 찾아주세요.

## 사용자 발화
"{state.user_input.content}"

## 선택지
{chr(10).join(choice_descriptions)}

## 분석 지침
1. **핵심 의도 파악**: 사용자가 정확히 무엇을 원하는지 파악
2. **키워드 해석**: 각 선택지의 intent_keywords와 사용자 발화의 연관성 분석
   - "동료", "함께", "찾자" → 동료를 모으는 선택지
   - "혼자", "직접", "나 혼자" → 혼자 행동하는 선택지
3. **맥락 고려**: 현재 상황(렌고쿠 위험)과 사용자 의도의 관계
4. **모호성 판단**: 의도가 불명확하면 confidence 낮게 설정

JSON 형식으로 응답:
{{
  "choice_index": 선택지 번호 (1부터 시작),
  "confidence": 신뢰도 (0.0~1.0),
  "reasoning": "선택 이유"
}}

**중요**: 신뢰도가 0.75 미만이면 choice_index를 -1로 설정하세요."""

                result = self.llm_client.call_json(
                    system_prompt="당신은 사용자 발화 의도를 정확히 분석하는 전문 AI입니다. 키워드의 미묘한 차이(예: '동료'와 '직접')를 정확히 구분하여 선택지를 매핑합니다.",
                    user_prompt=prompt,
                    temperature=0.2,  # 0.3 → 0.2로 낮춤 (더 일관된 해석)
                )
                choice_idx = result.get("choice_index", -1)
                confidence = result.get("confidence", 0.0)

                if choice_idx > 0 and confidence >= 0.75:
                    matched_choice = choices[choice_idx - 1]
                    best_confidence = confidence

            except Exception as e:
                _debug_print(f"LLM 선택 매핑 실패, 키워드 기반으로 전환: {e}")

        # LLM 실패 시 키워드 기반 폴백 (개선: 부분 매칭 지원)
        if matched_choice is None:
            for choice in choices:
                intent_keywords = choice.get("intent_keywords", [])
                match_score = 0

                # 각 키워드에 대해 부분 매칭 체크
                for kw in intent_keywords:
                    # 정확히 일치하는 경우 (예: "동료" in "동료들을 찾아보자")
                    if kw in user_input:
                        match_score += 1
                    # 키워드가 사용자 입력의 일부인 경우 (예: "찾" in "찾아보자")
                    elif any(kw in token for token in user_input.split()):
                        match_score += 0.5

                if match_score > 0:
                    # 키워드 매칭 점수를 confidence로 변환 (최대 0.95)
                    # 🔥 개선: 단일 키워드 매칭만으로도 0.75 이상이 되도록 base를 0.75로 설정
                    keyword_confidence = min(0.75 + (match_score * 0.10), 0.95)
                    if keyword_confidence > best_confidence:
                        matched_choice = choice
                        best_confidence = keyword_confidence

                        self.logger.log(
                            "Parent",
                            "keyword_match",
                            {
                                "choice_id": choice.get("id"),
                                "match_score": match_score,
                                "confidence": keyword_confidence,
                                "keywords_matched": intent_keywords,
                            },
                        )

        # 선택이 명확하면 (confidence >= 0.75) 확정
        if matched_choice and best_confidence >= 0.75:
            choice_id = matched_choice["id"]
            choice_text = matched_choice.get("text", choice_id)

            # 선택 확정
            state.game.user_choice = choice_id
            state.game.add_flag(f"choice_{choice_id}")
            state.game.add_flag(f"{state.game.current_stage}_completed")
            # 🔥 선택 대기 플래그 제거
            if f"{state.game.current_stage}_awaiting_choice" in state.game.flags:
                state.game.flags.remove(f"{state.game.current_stage}_awaiting_choice")

            # 친밀도 변화 적용
            affinity_changes = matched_choice.get("affinity_changes", {})
            for character, change in affinity_changes.items():
                state.characters.update_affinity(character, change)

            # 🔥 탄지로가 선택을 확인하고 격려 (Children Agent를 통해)
            guide_char = stage_data.get(
                "guide_character", self.config.get("main_guide_character", "tanjiro")
            )
            state.characters.available_characters = [guide_char]
            confirmation = f'좋아! "{choice_text}" 그 선택 좋은 것 같아! 함께 가자!'
            state.parent_decisions.dialogue_context = confirmation

            self.logger.log(
                "Parent",
                "choice_confirmed",
                {
                    "choice_id": choice_id,
                    "confidence": best_confidence,
                    "user_input": state.user_input.content[:50],
                },
            )

        else:
            # 🔥 의도가 불명확하면 탄지로가 상황을 설명하고 구체적인 가이드 제공
            guide_char = stage_data.get(
                "guide_character", self.config.get("main_guide_character", "tanjiro")
            )
            state.characters.available_characters = [guide_char]

            # 상황 설명과 구체적인 가이드
            reguide = f"""지금 렌고쿠 선생님이 아카자와 싸우고 계셔! 시간이 별로 없어... 
우리가 할 수 있는 선택은 두 가지야:

💡 **동료들을 모아서 함께 싸우기**
→ 이노스케와 젠이츠를 찾아서 설득해보자! (예: "동료들", "함께", "모아서")

⚔️ **혼자서 바로 달려가기** 
→ 시간이 없으니까 무모하지만 직접 도와보자! (예: "직접", "혼자", "바로")

어떤 방법으로 할까? 상황을 간단히 말해줘!"""

            state.parent_decisions.dialogue_context = reguide
            state.parent_decisions.speaking_rules["guide_mode"] = True

        return state

    def _show_situation_deterioration(
        self, state: AgentState, stage_data: Dict, remaining_turns: int
    ):
        """
        상황 악화 묘사 출력 (cutscene5 턴제 긴박감 연출)

        Args:
            state: 현재 게임 상태
            stage_data: 현재 스테이지 데이터
            remaining_turns: 남은 턴 수
        """
        deteriorations = stage_data.get("situation_deterioration", [])

        for det in deteriorations:
            if det.get("remaining_turns") == remaining_turns:
                message = det.get("message", "")
                if message:
                    state.output.add_system_message(f"⚠️  {message}")
                break

    def _handle_conversation_stages(
        self, state: AgentState, char_id: str, char_data: Dict, user_input_lower: str
    ) -> tuple:
        """
        다단계 대화 시스템 처리 (conversation_stages)

        Returns:
            (success: bool, stage_index: int, response_data: dict)
        """
        _debug_print(
            f"\n🔍 [CONV_STAGES] char_id={char_id}, input='{user_input_lower}'"
        )

        conversation_stages = char_data.get("conversation_stages")
        if not conversation_stages:
            # conversation_stages가 없으면 기존 방식 사용
            _debug_print(f"  → No conversation_stages, returning None")
            return None

        # 현재 대화 단계 가져오기
        stage_key = f"{char_id}_conversation_stage"
        current_stage_index = state.game.temp_data.get(stage_key, 0)

        _debug_print(f"  → temp_data at start: {state.game.temp_data}")
        _debug_print(f"  → stage_key: {stage_key}")
        _debug_print(f"  → current_stage_index: {current_stage_index}")
        _debug_print(f"  → total stages: {len(conversation_stages)}")

        # 모든 단계를 완료했으면
        if current_stage_index >= len(conversation_stages):
            _debug_print(f"  → All stages completed!")
            return (True, current_stage_index, None)

        current_stage = conversation_stages[current_stage_index]
        _debug_print(f"  → current_stage name: {current_stage.get('name')}")

        # 첫 만남: greeting 표시
        if current_stage_index == 0 and "greeting" in current_stage:
            greeting_shown_key = f"{char_id}_greeting_shown"
            if not state.game.has_flag(greeting_shown_key):
                # greeting을 dialogue_context로 전달
                greeting = current_stage["greeting"]
                state.parent_decisions.dialogue_context = [
                    {
                        "speaker": greeting["speaker"],
                        "situation": greeting[
                            "content"
                        ],  # children_agent가 "situation" 키를 기대
                        "emotion": greeting.get("emotion", "neutral"),
                    }
                ]
                state.game.add_flag(greeting_shown_key)

                # 🔥 greeting 표시 후 다음 단계로 자동 진행
                state.game.temp_data[stage_key] = current_stage_index + 1
                _debug_print(
                    f"  → Greeting shown! Auto-progressing to stage {current_stage_index + 1}"
                )
                _debug_print(f"  → temp_data after update: {state.game.temp_data}")

                return (False, current_stage_index, {"greeting": True})

        # 키워드 매칭
        required_keywords = current_stage.get("required_keywords", [])
        keyword_matched = False

        _debug_print(f"  → required_keywords: {required_keywords}")

        for kw in required_keywords:
            _debug_print(
                f"    - Checking '{kw}' in '{user_input_lower}': {kw in user_input_lower}"
            )
            if kw in user_input_lower:
                keyword_matched = True
                _debug_print(f"    - ✅ Match found with '{kw}'!")
                break

        _debug_print(f"  → keyword_matched: {keyword_matched}")

        if keyword_matched:
            # 성공 응답
            success_response = current_stage.get("success_response", {})

            dialogues = []

            # 캐릭터 응답 추가
            if success_response:
                dialogues.append(
                    {
                        "speaker": success_response.get("speaker", char_id),
                        "situation": success_response.get(
                            "content", ""
                        ),  # children_agent가 "situation" 키를 기대
                        "emotion": success_response.get("emotion", "neutral"),
                    }
                )

            # 탄지로 지원 대사 추가 (있으면)
            if "tanjiro_support" in current_stage:
                support = current_stage["tanjiro_support"]
                dialogues.append(
                    {
                        "speaker": support.get("speaker", "tanjiro"),
                        "situation": support.get(
                            "content", ""
                        ),  # children_agent가 "situation" 키를 기대
                        "emotion": support.get("emotion", "neutral"),
                    }
                )

            # dialogue_context에 전달
            state.parent_decisions.dialogue_context = dialogues

            # 다음 단계로 진행
            state.game.temp_data[stage_key] = current_stage_index + 1

            # 최종 설득 성공 체크
            if "success_flag" in current_stage:
                success_flag = current_stage["success_flag"]
                state.game.add_flag(success_flag)

                # 🔥 correct_order 체크: 올바른 순서로 첫 설득했는지 플래그 설정
                correct_order = char_data.get("correct_order")
                if correct_order is not None:
                    # 다른 캐릭터 중에 correct_order가 이 캐릭터보다 낮은 캐릭터가 있는지 확인
                    # 예: inosuke의 correct_order가 1이면, order가 1인 캐릭터는 반드시 먼저 설득되어야 함

                    # 현재 스테이지의 모든 캐릭터 확인
                    stage_data = state.game.scenario_data.get("stages", {}).get(
                        state.game.current_stage, {}
                    )
                    all_chars = stage_data.get("characters", {})

                    is_first_in_order = True
                    for other_char_id, other_char_data in all_chars.items():
                        other_order = other_char_data.get("correct_order")
                        if other_order is not None and other_order < correct_order:
                            # 이 캐릭터보다 먼저 설득되어야 하는 캐릭터가 있음
                            if not state.game.has_flag(f"{other_char_id}_recruited"):
                                is_first_in_order = False
                                break

                    # 올바른 순서로 첫 설득이면 {char}_first 플래그 설정
                    if is_first_in_order and correct_order == 1:
                        state.game.add_flag(f"{char_id}_first")
                        _debug_print(
                            f"  → ✅ First in correct order: {char_id}_first flag set!"
                        )

                return (
                    True,
                    current_stage_index + 1,
                    {"success": True, "dialogues": dialogues},
                )

            return (
                False,
                current_stage_index + 1,
                {"success": False, "dialogues": dialogues},
            )

        else:
            # 실패 응답
            failure_response = current_stage.get("failure_response", {})

            if failure_response:
                dialogues = [
                    {
                        "speaker": failure_response.get("speaker", char_id),
                        "situation": failure_response.get(
                            "content", ""
                        ),  # children_agent가 "situation" 키를 기대
                        "emotion": failure_response.get("emotion", "neutral"),
                    }
                ]

                state.parent_decisions.dialogue_context = dialogues
                return (
                    False,
                    current_stage_index,
                    {"success": False, "dialogues": dialogues},
                )

            return (False, current_stage_index, None)

    def _handle_mission_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """
        🔄 미션 스테이지 처리 (MissionManager 통합)

        MissionManager를 사용하여 턴 관리, 순서 검증, 친밀도 변화를 처리합니다.
        """
        self.logger.log(
            "Parent",
            "mission_stage_entered",
            {
                "stage": state.game.current_stage,
                "characters": list(stage_data.get("characters", {}).keys()),
            },
        )

        # 🔥 MissionManager 인스턴스 생성 또는 재사용
        manager_key = f"{state.game.current_stage}_manager"

        if manager_key not in state.game.temp_data:
            # 첫 진입: MissionManager 초기화
            manager = MissionManager(stage_data)
            mission_state = manager.start_mission()

            state.game.temp_data[manager_key] = {
                "manager": manager,
                "mission_state": mission_state,
            }
            state.game.add_flag(f"{state.game.current_stage}_entered")

            # 가이드 캐릭터 설정
            guide_char = stage_data.get(
                "guide_character", self.config.get("main_guide_character", "tanjiro")
            )
            state.characters.available_characters = [guide_char]

            # 미션 안내 메시지
            objective = stage_data.get("objective", "동료들을 설득하세요!")
            state.parent_decisions.dialogue_context = [
                {
                    "speaker": guide_char,
                    "situation": f"🎯 임무: {objective}",
                    "emotion": "determined",
                }
            ]

            return state

        # MissionManager와 상태 가져오기
        manager_data = state.game.temp_data[manager_key]
        manager = manager_data["manager"]
        mission_state = manager_data["mission_state"]

        user_input = state.user_input.content

        # 🔥 현재 대화 중인 캐릭터 찾기 (이동 감지)
        characters = stage_data.get("characters", {})
        user_input_lower = user_input.lower()
        current_target = None

        # 1. 현재 available_characters에서 타겟 찾기 (가이드 제외)
        guide_char = stage_data.get(
            "guide_character", self.config.get("main_guide_character", "tanjiro")
        )
        for char_id in state.characters.available_characters:
            if char_id != guide_char and char_id in characters:
                current_target = char_id
                break

        # 2. 새로운 캐릭터 언급 감지 (이동)
        for char_id, char_data in characters.items():
            if mission_state.character_progress[char_id].recruited:
                continue

            char_mentioned = False

            # 영문 ID 체크
            if char_id in user_input_lower:
                char_mentioned = True
            # conversation_stages 첫 키워드 체크
            elif "conversation_stages" in char_data:
                first_stage = char_data["conversation_stages"][0]
                first_keywords = first_stage.get("required_keywords", [])
                for kw in first_keywords:
                    if kw in user_input_lower:
                        char_mentioned = True
                        break

            # 새로운 캐릭터로 이동
            if char_mentioned and char_id not in state.characters.available_characters:
                current_target = char_id
                state.characters.available_characters = [char_id, guide_char]

                # Greeting 표시
                if "conversation_stages" in char_data:
                    first_stage = char_data["conversation_stages"][0]
                    if "greeting" in first_stage:
                        greeting = first_stage["greeting"]
                        state.parent_decisions.dialogue_context = [
                            {
                                "speaker": greeting["speaker"],
                                "situation": greeting["content"],
                                "emotion": greeting.get("emotion", "neutral"),
                            }
                        ]
                        # 단계 초기화
                        stage_key = f"{char_id}_conversation_stage"
                        state.game.temp_data[stage_key] = 0
                        return state
                break

        # 3. 타겟이 없으면 자동 타겟팅 (아직 설득 안 된 첫 캐릭터)
        if not current_target:
            for char_id in manager.correct_order:
                if not mission_state.character_progress[char_id].recruited:
                    current_target = char_id
                    state.characters.available_characters = [char_id, guide_char]
                    break

        # 🔥 MissionManager를 사용하여 입력 처리
        if current_target:
            success, msg, response = manager.process_user_input(
                mission_state,
                user_input,
                current_target,
                increment_turn_on_success=True,
            )

            # 응답 데이터를 dialogue_context로 전달
            if response:
                dialogues = []

                # 캐릭터 응답
                content = response.get("content", "")
                speaker = response.get("speaker", current_target)
                emotion = response.get("emotion", "neutral")

                if content:
                    dialogues.append(
                        {"speaker": speaker, "situation": content, "emotion": emotion}
                    )

                # Tanjiro 지원 메시지
                if "tanjiro_support" in response:
                    support = response["tanjiro_support"]
                    dialogues.append(
                        {
                            "speaker": support.get("speaker", "tanjiro"),
                            "situation": support.get("content", ""),
                            "emotion": support.get("emotion", "neutral"),
                        }
                    )

                if dialogues:
                    state.parent_decisions.dialogue_context = dialogues

            # 🔥 친밀도 변화 적용
            if success and response:
                affinity_impact = response.get("affinity_impact", {})
                for char, change in affinity_impact.items():
                    state.characters.update_affinity(char, change)

            # 위기 메시지 표시
            crisis_msg = manager.get_crisis_message(mission_state.current_turn)
            if crisis_msg:
                state.output.add_system_message(f"🚨 {crisis_msg}")

            # 🔥 미션 완료 체크
            status, status_msg = manager.check_completion(mission_state)

            if status == MissionStatus.SUCCESS:
                # 히든 엔딩으로 전환
                state.output.add_system_message(status_msg)
                state.game.add_flag(f"{state.game.current_stage}_completed")
                state.game.add_flag("all_allies_recruited")

                # end_hidden 스테이지로 전환
                next_stage = "end_hidden"
                state.game.stage_history.append(next_stage)
                state.game.current_stage = next_stage

                self.logger.log(
                    "Parent",
                    "mission_success",
                    {
                        "turns_used": mission_state.current_turn,
                        "recruitment_order": mission_state.recruitment_order,
                    },
                )

            elif status == MissionStatus.TIMEOUT:
                # 타임아웃 엔딩으로 전환
                state.output.add_system_message(status_msg)
                state.game.add_flag(f"{state.game.current_stage}_failed")

                # end_timeout 스테이지로 전환
                next_stage = "end_timeout"
                state.game.stage_history.append(next_stage)
                state.game.current_stage = next_stage

                self.logger.log(
                    "Parent",
                    "mission_timeout",
                    {
                        "turns_used": mission_state.current_turn,
                        "recruitment_order": mission_state.recruitment_order,
                    },
                )

            elif status == MissionStatus.FAILED:
                # 실패 (순서 오류 등) - 타임아웃과 동일하게 처리
                state.output.add_system_message(status_msg)
                state.game.add_flag(f"{state.game.current_stage}_failed")

                next_stage = "end_timeout"
                state.game.stage_history.append(next_stage)
                state.game.current_stage = next_stage

                self.logger.log(
                    "Parent",
                    "mission_failed",
                    {
                        "reason": status_msg,
                        "recruitment_order": mission_state.recruitment_order,
                    },
                )

        # 상태 저장
        state.game.temp_data[manager_key] = {
            "manager": manager,
            "mission_state": mission_state,
        }

        return state

    def _handle_branch_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """
        🔄 분기 스테이지 처리 (JSON 기반)

        JSON 구조:
        {
            "type": "branch",
            "branches": [
                {"id": "hidden_ending", "conditions": [...], "next_stage": "end_hidden"},
                {"id": "bad_ending", "conditions": ["default"], "next_stage": "end_bad"}
            ]
        }
        """
        from scenario_loader import scenario_loader

        # 조건 평가
        conditions = scenario_loader.evaluate_branch_conditions(state, stage_data)

        # 다음 스테이지 결정
        next_stage_id = scenario_loader.get_next_stage_id(
            state.game.scenario_data, state.game.current_stage, conditions=conditions
        )

        if next_stage_id:
            # 분기 완료 플래그
            state.game.add_flag(f"{state.game.current_stage}_completed")
            state.game.add_flag(f"branch_to_{next_stage_id}")

        return state

    def _handle_ending_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """
        🔄 엔딩 스테이지 처리 (JSON 기반)

        JSON 구조:
        {
            "type": "ending",
            "ending_type": "good" | "bad" | "hidden",
            "dialogues": [...],
            "final_message": "엔딩 메시지"
        }
        """
        # 첫 진입 시
        if not state.game.has_flag(f"{state.game.current_stage}_entered"):
            state.game.add_flag(f"{state.game.current_stage}_entered")

            # 엔딩 타입 설정
            ending_type = stage_data.get("ending_type", "normal")
            state.game.add_flag(f"ending_{ending_type}")

            # 엔딩 메시지
            final_message = stage_data.get("final_message", "")
            if final_message:
                state.output.narration = final_message

        # 가이드 캐릭터 설정
        guide_char = stage_data.get(
            "guide_character", self.config.get("main_guide_character", "tanjiro")
        )
        state.characters.available_characters = [guide_char]

        # 엔딩 스테이지는 즉시 완료
        if not state.game.has_flag(f"{state.game.current_stage}_completed"):
            state.game.add_flag(f"{state.game.current_stage}_completed")

        return state

    def _handle_generic_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
        """범용 스테이지 처리"""
        state.output.add_system_message("스테이지 진행 중...")
        return state

    def _check_stage_transition(
        self, state: AgentState, current_stage_data: Dict
    ) -> AgentState:
        """
        🔄 다음 스테이지로 전환 여부 확인 및 즉시 처리

        현재 스테이지가 완료되었으면 next_stage로 이동하고 즉시 처리
        """
        from scenario_loader import scenario_loader

        stage_completed = state.game.has_flag(f"{state.game.current_stage}_completed")

        if stage_completed:
            # 다음 스테이지 결정
            stage_type = current_stage_data.get("type")

            if stage_type == "choice":
                # choice: 사용자 선택에 따라
                next_stage_id = scenario_loader.get_next_stage_id(
                    state.game.scenario_data,
                    state.game.current_stage,
                    user_choice=state.game.user_choice,
                )
            elif stage_type == "branch":
                # branch: 조건에 따라 (이미 handle_branch_stage에서 처리됨)
                conditions = scenario_loader.evaluate_branch_conditions(
                    state, current_stage_data
                )
                next_stage_id = scenario_loader.get_next_stage_id(
                    state.game.scenario_data,
                    state.game.current_stage,
                    conditions=conditions,
                )
            else:
                # cutscene, mission: next_stage 직접 사용
                next_stage_id = current_stage_data.get("next_stage")

            if next_stage_id:
                # 전환 전 검증: 불필요한 전환 방지
                current_stage = state.game.current_stage

                # 🔥 중복 전환 방지: 이미 다음 스테이지에 있으면 전환하지 않음
                if current_stage == next_stage_id:
                    self.logger.log(
                        "Parent",
                        "skip_duplicate_transition",
                        {"stage": current_stage, "reason": "already_in_target_stage"},
                    )
                    return state

                # 🔥 Choice 스테이지 예외 처리: 모호한 입력 시 즉시 전환 방지
                if stage_type == "choice":
                    # user_choice가 명확하게 설정된 경우에만 전환
                    if not state.game.user_choice:
                        self.logger.log(
                            "Parent",
                            "block_premature_choice_transition",
                            {
                                "reason": "unclear_user_choice",
                                "current_stage": current_stage,
                                "next_stage": next_stage_id,
                                "user_input": state.user_input.content[:50],
                            },
                        )
                        return state  # 전환 취소

                    # choice 데이터에서 유효한 선택지 ID 확인
                    choices = current_stage_data.get("choices", [])
                    valid_choice_ids = [c.get("id") for c in choices]

                    if state.game.user_choice not in valid_choice_ids:
                        self.logger.log(
                            "Parent",
                            "invalid_choice_id",
                            {
                                "user_choice": state.game.user_choice,
                                "valid_choices": valid_choice_ids,
                            },
                        )
                        return state  # 전환 취소

                # 🔥 무한루프 방지: 스테이지 전환 횟수 체크
                transition_count = state.game.temp_data.get("_transition_count", 0)
                if transition_count > 5:
                    _debug_print(
                        f"❌ 스테이지 전환 무한루프 감지! transition_count={transition_count}"
                    )
                    state.output.add_system_message(
                        "⚠️  스테이지 전환 오류가 발생했습니다."
                    )
                    return state

                state.game.temp_data["_transition_count"] = transition_count + 1

                # 스테이지 전환
                state.game.stage_history.append(next_stage_id)
                state.game.current_stage = next_stage_id

                self.logger.log(
                    "Parent",
                    "stage_transition",
                    {
                        "from": current_stage,
                        "to": next_stage_id,
                        "user_choice": state.game.user_choice,
                        "transition_count": transition_count + 1,
                    },
                )

                # 엔딩 스테이지 확인
                if "end" in next_stage_id.lower():
                    state.scene.current_scene = next_stage_id

                # 🔥 다음 스테이지 진입 준비 (무한 루프 방지: 다음 턴에 처리)
                next_stage_data = state.game.scenario_data["stages"].get(
                    next_stage_id, {}
                )
                next_stage_type = next_stage_data.get("type")

                self.logger.log(
                    "Parent",
                    "next_stage_prepared",
                    {
                        "stage": next_stage_id,
                        "type": next_stage_type,
                        "note": "will_be_processed_next_turn",
                    },
                )

                # 🔥 스테이지 전환 후 dialogue_context/available_characters 초기화
                # (cutscene에서 fork로 전환 시 기존 대사가 남아있지 않도록)
                state.parent_decisions.dialogue_context = None
                state.characters.available_characters = []

        else:
            # 스테이지 완료되지 않은 경우 transition_count 초기화
            if "_transition_count" in state.game.temp_data:
                del state.game.temp_data["_transition_count"]

        return state

    def _request_scene_assets(self, state: AgentState) -> AgentState:
        """Scene Tools에 에셋 요청"""
        asset_type = "cutscene"  # 기본값

        # 씬과 턴에 따른 에셋 타입 결정
        if state.scene.current_scene.endswith("_intro"):
            asset_type = "cutscene"
        elif state.game.turn % 3 == 0:  # 3턴마다 감정 이미지
            asset_type = "emotion"
        elif state.scene.current_scene.endswith("_ending"):
            if state.validate_hidden_ending_conditions():
                asset_type = "special_clear"
            else:
                asset_type = "cutscene"

        # 대화에서 마지막 캐릭터의 감정 파악
        last_emotion = "neutral"
        if state.output.dialogues:
            last_dialogue = state.output.dialogues[-1]
            last_emotion = last_dialogue.emotion or "neutral"

        state.scene_tool_request = SceneToolRequest(
            action=f"get_{asset_type}",
            scene_id=state.scene.current_scene,
            turn=state.game.turn,
            character_id=state.characters.active_character,
            emotion=last_emotion,
            asset_type=asset_type,
            summary_context=state.message_history.get_recent_context()
            if asset_type == "special_clear"
            else None,
        )

        return state

    def _set_dialogue_rules(self, state: AgentState) -> AgentState:
        """Children Agent용 대화 규칙 설정"""
        available_chars = state.characters.available_characters

        # 🔥 기존 guide_mode 보존
        existing_guide_mode = False
        if (
            hasattr(state.parent_decisions, "speaking_rules")
            and state.parent_decisions.speaking_rules
        ):
            existing_guide_mode = state.parent_decisions.speaking_rules.get(
                "guide_mode", False
            )

        # 기본 규칙
        dialogue_rules = {
            "min_characters": 1,  # 최소 1명은 반드시 말해야 함
            "max_characters": min(2, len(available_chars)),  # 최대 2명까지
            "max_per_character": 3,  # 캐릭터당 최대 3번
            "required_speakers": available_chars,
            "mood": state.scene.mood or "neutral",
            "context": state.message_history.get_recent_context(),
            "affinity_levels": state.characters.affinity_levels,
            "guide_mode": existing_guide_mode,  # 🔥 기존 guide_mode 보존
        }

        # 🔄 스테이지 타입별 특별 규칙 (동적)
        if state.game.scenario_data and state.game.current_stage:
            stages = state.game.scenario_data.get("stages", {})
            current_stage_data = stages.get(state.game.current_stage, {})
            stage_type = current_stage_data.get("type")

            if stage_type == "cutscene":
                # 컷신에서는 정해진 대사만 출력
                dialogue_rules.update(
                    {
                        "cutscene_mode": True,
                        "current_turn": state.scene.current_cutscene_turn,
                        "auto_dialogue": True,
                    }
                )
            elif stage_type == "mission":
                dialogue_rules.update(
                    {
                        "focus_character": state.characters.available_characters[0]
                        if state.characters.available_characters
                        else None,
                        "persuasion_context": True,
                        "emotional_intensity": "high",
                    }
                )
            elif stage_type == "choice":
                dialogue_rules.update(
                    {"show_choices": True, "wait_for_selection": True}
                )

        # 🔥 dialogue_context 보존 (cutscene에서 설정한 상황 컨텍스트 유지)
        existing_context = None
        if state.parent_decisions and hasattr(
            state.parent_decisions, "dialogue_context"
        ):
            existing_context = state.parent_decisions.dialogue_context
        if not existing_context:
            existing_context = state.output.narration

        state.parent_decisions = ParentDecisions(
            active_characters=available_chars,
            dialogue_context=existing_context,  # 기존 컨텍스트 보존
            emotion_context=state.scene.mood,
            speaking_rules=dialogue_rules,
        )

        return state

    def _check_ending_conditions(self, state: AgentState) -> AgentState:
        """
        🔄 엔딩 조건 확인 (시나리오 JSON 기반)

        엔딩 조건은 branch 스테이지의 conditions로 처리되므로
        여기서는 기본 실패 조건만 체크
        """
        # 실패 조건 체크 (시나리오 JSON에서 max_turns 가져오기)
        if state.game.scenario_data and state.game.current_stage:
            stages = state.game.scenario_data.get("stages", {})
            current_stage_data = stages.get(state.game.current_stage, {})
            max_turns = current_stage_data.get("max_turns", 999)

            if state.game.turn >= max_turns or state.game.total_remaining_turns <= 0:
                if not state.game.has_flag("time_out"):
                    state.game.add_flag("time_out")
                    # crisis_messages로 처리하도록 메시지 제거

        return state

    def _calculate_affinity_changes(self, state: AgentState) -> Dict[str, int]:
        """친밀도 변화 계산"""
        # LLM 사용 가능하면 LLM으로 계산
        if self.use_llm:
            llm_changes = self._calculate_affinity_with_llm(state)
            if llm_changes is not None:
                return llm_changes

        # LLM 실패 시 또는 미사용 시 규칙 기반 계산
        return self._calculate_affinity_with_rules(state)

    def _calculate_affinity_with_llm(
        self, state: AgentState
    ) -> Optional[Dict[str, int]]:
        """LLM을 이용한 친밀도 변화 계산"""
        try:
            # 현재 활성 캐릭터만 분석
            active_chars = state.characters.available_characters
            if not active_chars:
                return {}

            system_prompt = """당신은 게임 캐릭터의 친밀도 변화를 분석하는 AI입니다.
사용자의 입력이 각 캐릭터에게 어떤 영향을 미치는지 분석하세요.

캐릭터 성향:
- 탄지로: 정직, 배려, 동료애 중시
- 이노스케: 자유분방, 호승심 강함, 강함 인정받는 것 좋아함
- 젠이츠: 겁 많음, 네즈코 좋아함, 용기 인정받으면 기뻐함
- 렌고쿠: 정의로움, 열정, 후배 격려

친밀도 변화 규칙:
- 캐릭터 성향에 맞는 긍정적 말: +5 ~ +30
- 캐릭터 성향에 맞지 않는 부정적 말: -3 ~ -10
- 무관한 말: 0

JSON 형식으로 응답하세요:
{
  "affinity_changes": {
    "character_id": change_value (정수)
  },
  "reasoning": "판단 근거"
}"""

            characters_info = "\n".join(
                [
                    f"- {char_id}: 현재 친밀도 {state.characters.affinity.get(char_id, 0)}"
                    for char_id in active_chars
                ]
            )

            user_prompt = f"""현재 상황:
씬: {state.scene.current_scene}
활성 캐릭터: {", ".join(active_chars)}
{characters_info}

사용자 입력: "{state.user_input.content}"

위 사용자 입력이 각 활성 캐릭터의 친밀도에 미치는 영향을 분석하세요."""

            response = self.llm_client.call_json(
                system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.5
            )

            affinity_changes = response.get("affinity_changes", {})

            # 정수로 변환 및 검증
            validated_changes = {}
            for char, change in affinity_changes.items():
                if char in state.characters.affinity:
                    try:
                        validated_changes[char] = int(change)
                    except (ValueError, TypeError):
                        pass

            return validated_changes

        except Exception as e:
            _debug_print(f"LLM 친밀도 계산 실패: {str(e)}")
            return None

    def _calculate_affinity_with_rules(self, state: AgentState) -> Dict[str, int]:
        """
        🔄 규칙 기반 친밀도 변화 계산 (시나리오 JSON 기반)

        시나리오 JSON의 affinity_changes를 우선 사용,
        없으면 현재 스테이지의 keywords 기반 계산
        """
        changes = {}

        # None 체크
        if not state.user_input or not state.user_input.content:
            return changes

        user_input = state.user_input.content.lower()

        # 🔄 시나리오 JSON에서 키워드 가져오기
        if not state.game.scenario_data:
            return changes

        stages = state.game.scenario_data.get("stages", {})
        current_stage_data = stages.get(state.game.current_stage, {})

        # mission 스테이지: characters의 keywords 사용
        if current_stage_data.get("type") == "mission":
            characters_data = current_stage_data.get("characters", {})

            for char_id, char_data in characters_data.items():
                if char_id in state.characters.available_characters:
                    keywords = char_data.get("keywords", [])
                    matched = sum(1 for kw in keywords if kw in user_input)

                    if matched > 0:
                        # 키워드 매칭 수에 비례한 친밀도 증가
                        changes[char_id] = matched * 10

        # choice 스테이지: affinity_changes 직접 사용 (이미 handle_choice_stage에서 처리됨)

        return changes


def run_parent_agent(state: AgentState) -> AgentState:
    """
    Parent Agent 실행 함수 - 개선된 버전
    🎮 게임 마스터 역할: 현재 씬 정보를 분석하여 서사를 적극적으로 진행
    """
    from src.utils.scenario_loader import get_current_scene_data, scenario_loader

    print(f"[PARENT] 🎮 Game Master processing...")

    # 1. 현재 상태 확인
    user_input = state.get("user_input", "")
    current_stage = state.get("current_stage")
    turn_count = state.get("turn_count", 0)

    print(f"[PARENT] Current stage: {current_stage}")
    print(f"[PARENT] Turn count: {turn_count}")
    print(f"[PARENT] User input: {user_input[:50] if user_input else '(empty)'}...")

    # 2. 현재 씬 데이터 가져오기
    current_scene_data = get_current_scene_data(state)
    
    if not current_scene_data:
        print(f"[PARENT] ❌ No scene data found for stage: {current_stage}")
        state["agent_responses"] = [
            {
                "speaker": "시스템",
                "text": "오류: 현재 스테이지 데이터를 찾을 수 없습니다.",
            }
        ]
        return state

    stage_type = current_scene_data.get("type")
    print(f"[PARENT] Stage type: {stage_type}")

    # 3. 스테이지 타입별 처리
    if stage_type == "cutscene":
        return _handle_cutscene_stage(state, current_scene_data, current_stage)
    elif stage_type == "choice":
        return _handle_choice_stage(state, current_scene_data, current_stage, user_input)
    elif stage_type == "mission":
        return _handle_mission_stage(state, current_scene_data, current_stage, user_input)
    elif stage_type == "ending":
        return _handle_ending_stage(state, current_scene_data, current_stage)
    else:
        print(f"[PARENT] ❌ Unknown stage type: {stage_type}")
        state["agent_responses"] = [
            {
                "speaker": "시스템",
                "text": f"알 수 없는 스테이지 타입: {stage_type}",
            }
        ]
        return state

def _handle_cutscene_stage(state: AgentState, scene_data: Dict, current_stage: str) -> AgentState:
    """
    컷신 스테이지 처리
    """
    print(f"[PARENT] Handling cutscene stage: {current_stage}")
    
    dialogues = scene_data.get("dialogues", [])
    current_turn = state.get("turn_count", 0)
    
    # 현재 턴에 해당하는 대사 찾기
    turn_dialogue = next(
        (d for d in dialogues if d.get("turn") == current_turn), None
    )
    
    if not turn_dialogue:
        # 대사가 없으면 다음 스테이지로
        next_stage = scene_data.get("next_stage")
        if next_stage:
            print(f"[PARENT] 🎬 Auto-advancing: Cutscene {current_stage} → {next_stage}")
            state["current_stage"] = next_stage
            state["stage_history"] = state.get("stage_history", []) + [next_stage]
            state["turn_count"] = 0  # 새 스테이지에서 턴 리셋
            # 재귀 호출로 다음 스테이지 즉시 처리
            return run_parent_agent(state)
        else:
            # 다음 스테이지가 없으면 게임 종료
            state["final_ending"] = "cutscene_complete"
            state["next_node"] = "END"
            state["agent_responses"] = [
                {
                    "speaker": "시스템",
                    "text": "🎬 컷신이 완료되었습니다.\n\n게임이 종료되었습니다. 감사합니다!",
                }
            ]
            return state
    else:
        # 현재 턴의 대사 처리
        speakers = turn_dialogue.get("speakers", [])
        contents = turn_dialogue.get("contents", [])
        emotions = turn_dialogue.get("emotions", [])
        user_prompt = turn_dialogue.get("user_prompt", "입력하세요")
        
        # Children Agent로 대사 생성 요청
        state["agent_responses"] = []
        state = _generate_dialogue_with_children(
            state=state,
            speakers=speakers,
            contents=contents,
            emotions=emotions,
            stage_type="cutscene",
        )
        
        # user_prompt 저장
        state["user_input_prompt"] = user_prompt
        
        # 친밀도 업데이트: 일반 상호작용
        if state.get("user_input", "").strip():
            for resp in state.get("agent_responses", []):
                speaker = resp.get("speaker", "").lower()
                if speaker in ["tanjiro", "inosuke", "zenitsu", "rengoku"]:
                    changes = {speaker: ["general_interaction"]}
                    new_affinity, amounts = affinity_calculator.apply_affinity_change(
                        state.get("affinity_scores", {}), changes
                    )
                    state["affinity_scores"] = new_affinity
                    if amounts.get(speaker, 0) > 0:
                        print(f"[AFFINITY] {speaker}: +{amounts[speaker]} (general interaction)")
        
        print(f"[PARENT] Cutscene dialogues: {len(state['agent_responses'])} loaded")
        
    return state


def _handle_choice_stage(state: AgentState, scene_data: Dict, current_stage: str, user_input: str) -> AgentState:
    """
    선택 스테이지 처리
    """
    print(f"[PARENT] Handling choice stage: {current_stage}")
    
    choice_started_key = f"{current_stage}_choice_started"
    system_flags = state.get("system_flags", [])
    
    if choice_started_key not in system_flags:
        # 첫 진입: pre_choice 대화 표시
        speakers = scene_data.get("pre_choice_speakers", [])
        contents = scene_data.get("pre_choice_contents", [])
        emotions = scene_data.get("pre_choice_emotions", [])
        user_prompt = scene_data.get("user_prompt", "선택하세요")
        
        state["agent_responses"] = []
        state = _generate_dialogue_with_children(
            state=state,
            speakers=speakers,
            contents=contents,
            emotions=emotions,
            stage_type="choice",
        )
        
        state["user_input_prompt"] = user_prompt
        
        # 플래그 설정
        state["system_flags"] = system_flags + [choice_started_key]
        print(f"[PARENT] Choice pre-dialogues: {len(state['agent_responses'])} loaded")
        return state
    
    # 두 번째 진입: 선택 매칭
    choices = scene_data.get("choices", [])
    
    # LLM을 사용한 자연어 의도 판단
    matched_choice = _match_choice_with_llm(user_input, choices, state)
    
    if not matched_choice:
        # LLM 실패 시 폴백: 키워드 매칭
        matched_choice = _match_choice_with_keywords(user_input, choices)
    
    # 매칭 결과 처리
    if matched_choice:
        next_stage = matched_choice.get("next_stage")
        choice_id = matched_choice.get("id", "")
        print(f"[PARENT] 선택 매칭: {choice_id} → {next_stage}")
        
        state["current_stage"] = next_stage
        state["stage_history"] = state.get("stage_history", []) + [next_stage]
        
        # 친밀도 업데이트: 긍정적 상호작용
        if "recruit" in choice_id or "allies" in choice_id:
            changes = {
                "tanjiro": ["positive_interaction"],
                "inosuke": ["positive_interaction"],
                "zenitsu": ["positive_interaction"],
            }
            new_affinity, amounts = affinity_calculator.apply_affinity_change(
                state.get("affinity_scores", {}), changes
            )
            state["affinity_scores"] = new_affinity
            for char, amount in amounts.items():
                if amount > 0:
                    print(f"[AFFINITY] {char}: +{amount} (positive choice)")
        
        # 선택 완료 - 다음 스테이지로 진행
        state["agent_responses"] = []
        state["user_input_prompt"] = "계속 진행하려면 아무 키나 입력하세요"
    else:
        print(f"[PARENT] 선택지 미매칭, 다시 입력 요청")
        state["agent_responses"] = [
            {
                "speaker": "시스템",
                "text": "선택을 이해하지 못했습니다. 다시 선택해주세요.",
            }
        ]
    
    return state


def _handle_mission_stage(state: AgentState, scene_data: Dict, current_stage: str, user_input: str) -> AgentState:
    """
    미션 스테이지 처리
    """
    print(f"[PARENT] Handling mission stage: {current_stage}")
    
    mission_started_key = f"{current_stage}_mission_started"
    system_flags = state.get("system_flags", [])
    
    if mission_started_key not in system_flags:
        # 첫 진입: intro 대화 표시
        speakers = scene_data.get("intro_speakers", [])
        contents = scene_data.get("intro_contents", [])
        emotions = scene_data.get("intro_emotions", [])
        user_prompt = scene_data.get("user_prompt", "선택하세요")
        
        state["agent_responses"] = []
        state = _generate_dialogue_with_children(
            state=state,
            speakers=speakers,
            contents=contents,
            emotions=emotions,
            stage_type="mission",
        )
        
        state["user_input_prompt"] = user_prompt
        
        # 플래그 설정
        state["system_flags"] = system_flags + [mission_started_key]
        print(f"[PARENT] Mission intro: {len(state['agent_responses'])} dialogues loaded")
        return state
    
    # 미션 진행 중: 캐릭터 선택 또는 설득
    characters = scene_data.get("characters", {})
    
    # 유저 입력에서 캐릭터 감지
    target_char = None
    if "이노스케" in user_input:
        target_char = "inosuke"
    elif "젠이츠" in user_input:
        target_char = "zenitsu"
    
    # 이미 진행 중인 캐릭터 확인
    current_char_key = f"{current_stage}_current_char"
    current_char = state.get("temp_data", {}).get(current_char_key)
    
    if current_char and current_char in characters:
        # 설득 진행 중
        char_data = characters[current_char]
        stages = char_data.get("stages", [])
        
        # 현재 stage 가져오기
        stage_idx_key = f"{current_stage}_{current_char}_stage"
        stage_idx = state.get("temp_data", {}).get(stage_idx_key, 0)
        
        if stage_idx < len(stages):
            stage = stages[stage_idx]
            
            # success_keywords 확인
            success_keywords = stage.get("success_keywords", [])
            
            # LLM 기반 키워드 매칭
            char_names = {"inosuke": "이노스케", "zenitsu": "젠이츠"}
            context = f"{char_names.get(current_char, current_char)}를 설득하는 상황 (stage {stage_idx})"
            
            is_success, confidence, reasoning = _match_keywords_with_llm(
                user_input=user_input,
                keywords=success_keywords,
                context=context,
                confidence_threshold=70,
            )
            
            print(f"[PARENT] Mission keyword check: stage={stage_idx}, success={is_success}, confidence={confidence}%")
            print(f"[PARENT] Keywords: {success_keywords}, Reasoning: {reasoning}")
            
            # 대사 표시 (LLM 생성)
            speakers = stage.get("speakers", [])
            contents = stage.get("contents", [])
            emotions = stage.get("emotions", [])
            user_prompt = stage.get("user_prompt", "입력하세요")
            
            state["agent_responses"] = []
            state = _generate_dialogue_with_children(
                state=state,
                speakers=speakers,
                contents=contents,
                emotions=emotions,
                stage_type="mission",
            )
            
            state["user_input_prompt"] = user_prompt
            
            # 성공 여부에 따라 다음 stage로 진행 또는 재시도
            if is_success:
                print(f"[PARENT] Mission keyword matched! Advancing to next stage...")
                
                # 턴 증가 (성공 시에만)
                char_turn_key = f"{current_stage}_{current_char}_turns"
                mission_turn_key = f"{current_stage}_total_mission_turns"
                
                if "temp_data" not in state:
                    state["temp_data"] = {}
                
                # 캐릭터별 턴 증가
                char_turns = state["temp_data"].get(char_turn_key, 0) + 1
                state["temp_data"][char_turn_key] = char_turns
                
                # 미션 전체 턴 증가
                mission_turns = state["temp_data"].get(mission_turn_key, 0) + 1
                state["temp_data"][mission_turn_key] = mission_turns
                
                print(f"[PARENT] Turn tracking: {current_char}={char_turns}/3, mission_total={mission_turns}/5")
                
                # 턴 제한 검증
                MAX_CHAR_TURNS = 3
                MAX_MISSION_TURNS = 5
                
                if char_turns > MAX_CHAR_TURNS:
                    # 캐릭터별 턴 초과 → 실패
                    state["agent_responses"] = [
                        {
                            "speaker": "시스템",
                            "text": f"❌ {characters[current_char].get('name', current_char)} 설득 실패! (턴 제한 {MAX_CHAR_TURNS}턴 초과)",
                        }
                    ]
                    state["user_input_prompt"] = scene_data.get("user_prompt", "선택하세요")
                    return state
                
                if mission_turns > MAX_MISSION_TURNS:
                    # 미션 전체 턴 초과 → 실패
                    state["agent_responses"] = [
                        {
                            "speaker": "시스템",
                            "text": f"❌ 미션 실패! (전체 턴 제한 {MAX_MISSION_TURNS}턴 초과)",
                        }
                    ]
                    state["user_input_prompt"] = scene_data.get("user_prompt", "선택하세요")
                    return state
                
                # 다음 stage로 진행
                state["temp_data"][stage_idx_key] = stage_idx + 1
                
                # 모든 stage 완료 시 성공
                if stage_idx + 1 >= len(stages):
                    print(f"[PARENT] Mission completed for {current_char}!")
                    state["mission_result"] = "success"
                    # 다음 스테이지로 진행
                    next_stage = scene_data.get("next_stage")
                    if next_stage:
                        state["current_stage"] = next_stage
                        state["stage_history"] = state.get("stage_history", []) + [next_stage]
                        state["turn_count"] = 0
                        return run_parent_agent(state)
            else:
                # 실패 - 재시도
                print(f"[PARENT] Mission keyword not matched, retry...")
    
    return state


def _handle_ending_stage(state: AgentState, scene_data: Dict, current_stage: str) -> AgentState:
    """
    엔딩 스테이지 처리
    """
    print(f"[PARENT] Handling ending stage: {current_stage}")
    
    dialogues = scene_data.get("dialogues", [])
    ending_turn_key = f"{current_stage}_ending_turn"
    ending_turn = state.get("temp_data", {}).get(ending_turn_key, 0)
    
    turn_dialogue = next(
        (d for d in dialogues if d.get("turn") == ending_turn), None
    )
    
    if not turn_dialogue:
        # 모든 엔딩 대사 완료
        print(f"[PARENT] 🎬 Auto-completing: Ending {current_stage}")
        state["final_ending"] = current_stage
        state["next_node"] = "END"
        state["agent_responses"] = [
            {
                "speaker": "시스템",
                "text": f"🎬 '{scene_data.get('title', '엔딩')}' 완료\n\n게임이 종료되었습니다. 감사합니다!",
            }
        ]
        return state
    else:
        # 현재 턴의 엔딩 대사 처리
        speakers = turn_dialogue.get("speakers", [])
        contents = turn_dialogue.get("contents", [])
        emotions = turn_dialogue.get("emotions", [])
        user_prompt = turn_dialogue.get("user_prompt", "입력하세요")
        
        state["agent_responses"] = []
        state = _generate_dialogue_with_children(
            state=state,
            speakers=speakers,
            contents=contents,
            emotions=emotions,
            stage_type="ending",
        )
        
        state["user_input_prompt"] = user_prompt
        
        # 다음 엔딩 턴으로 증가
        if "temp_data" not in state:
            state["temp_data"] = {}
        state["temp_data"][ending_turn_key] = ending_turn + 1
        
        print(f"[PARENT] Ending dialogues: {len(state['agent_responses'])} loaded")
    
    return state


# 테스트용 함수
def test_parent_agent():
    from src.core.graph_state import create_initial_graph_state

    # 테스트: 동료 설득 시나리오
    state = create_initial_graph_state("test", "scene5_recruit_mission")
    state["user_input"] = "이노스케야, 함께 싸우자! 너는 정말 강하니까!"

    result_state = run_parent_agent(state)

    print("=== Parent Agent 테스트 결과 ===")
    print(f"씬: {result_state.get('current_stage')}")
    print(f"플래그: {result_state.get('system_flags')}")
    print(f"친밀도: {result_state.get('affinity_scores')}")
    print(f"다음 노드: {result_state.get('next_node')}")


if __name__ == "__main__":
    test_parent_agent()

                # 현재 stage 가져오기
                stage_idx_key = f"{current_stage}_{current_char}_stage"
                stage_idx = state.get("temp_data", {}).get(stage_idx_key, 0)

                if stage_idx < len(stages):
                    stage = stages[stage_idx]

                    # success_keywords 확인
                    success_keywords = stage.get("success_keywords", [])
                    success_flag = stage.get("success_flag")

                    # 🔥 LLM 기반 키워드 매칭
                    char_names = {"inosuke": "이노스케", "zenitsu": "젠이츠"}
                    context = f"{char_names.get(current_char, current_char)}를 설득하는 상황 (stage {stage_idx})"

                    is_success, confidence, reasoning = _match_keywords_with_llm(
                        user_input=user_input,
                        keywords=success_keywords,
                        context=context,
                        confidence_threshold=70,
                    )

                    print(
                        f"[PARENT] Mission keyword check: stage={stage_idx}, success={is_success}, confidence={confidence}%"
                    )
                    print(
                        f"[PARENT] Keywords: {success_keywords}, Reasoning: {reasoning}"
                    )

                    # 대사 표시 (LLM 생성)
                    speakers = stage.get("speakers", [])
                    contents = stage.get("contents", [])
                    emotions = stage.get("emotions", [])
                    user_prompt = stage.get("user_prompt", "입력하세요")

                    state["agent_responses"] = []
                    state = _generate_dialogue_with_children(
                        state=state,
                        speakers=speakers,
                        contents=contents,
                        emotions=emotions,
                        stage_type="mission",
                    )

                    state["user_input_prompt"] = user_prompt

                    # 성공 여부에 따라 다음 stage로 진행 또는 재시도
                    if is_success:
                        print(
                            f"[PARENT] Mission keyword matched! Advancing to next stage..."
                        )

                        # 🔥 턴 증가 (성공 시에만)
                        char_turn_key = f"{current_stage}_{current_char}_turns"
                        mission_turn_key = f"{current_stage}_total_mission_turns"

                        if "temp_data" not in state:
                            state["temp_data"] = {}

                        # 캐릭터별 턴 증가
                        char_turns = state["temp_data"].get(char_turn_key, 0) + 1
                        state["temp_data"][char_turn_key] = char_turns

                        # 미션 전체 턴 증가
                        mission_turns = state["temp_data"].get(mission_turn_key, 0) + 1
                        state["temp_data"][mission_turn_key] = mission_turns

                        print(
                            f"[PARENT] Turn tracking: {current_char}={char_turns}/3, mission_total={mission_turns}/5"
                        )

                        # 🔥 턴 제한 검증
                        MAX_CHAR_TURNS = 3
                        MAX_MISSION_TURNS = 5

                        if char_turns > MAX_CHAR_TURNS:
                            # 캐릭터별 턴 초과 → 실패
                            state["agent_responses"] = [
                                {
                                    "speaker": "시스템",
                                    "text": f"❌ {characters[current_char].get('name', current_char)} 설득 실패! (턴 제한 {MAX_CHAR_TURNS}턴 초과)",
                                }
                            ]
                            state["user_input_prompt"] = current_scene_data.get(
                                "user_prompt", "선택하세요"
                            )

                            # 캐릭터 진행 초기화
                            state["temp_data"].pop(current_char_key, None)
                            state["temp_data"].pop(stage_idx_key, None)
                            state["temp_data"].pop(char_turn_key, None)

                            print(
                                f"[PARENT] Character turn limit exceeded: {current_char} > {MAX_CHAR_TURNS}"
                            )
                            return state

                        # 친밀도 업데이트
                        if success_flag:
                            # 최종 설득 성공: 결정적 상호작용 (+8) + 핵심 목표 달성 (+10)
                            changes = {
                                current_char: [
                                    "optimal_interaction",
                                    "core_goal_achievement",
                                ]
                            }
                            print(
                                f"[AFFINITY] {current_char}: Applying recruitment success bonuses"
                            )
                        else:
                            # 중간 단계 성공: 긍정적 상호작용 (+5)
                            changes = {current_char: ["positive_interaction"]}

                        new_affinity, amounts = (
                            affinity_calculator.apply_affinity_change(
                                state.get("affinity_scores", {}), changes
                            )
                        )
                        state["affinity_scores"] = new_affinity
                        for char, amount in amounts.items():
                            if amount != 0:
                                print(
                                    f"[AFFINITY] {char}: +{amount} (mission progress)"
                                )

                        # 다음 stage로
                        state["temp_data"][stage_idx_key] = stage_idx + 1

                        # success_flag가 있으면 캐릭터 설득 완료
                        if success_flag:
                            if "system_flags" not in state:
                                state["system_flags"] = []
                            state["system_flags"].append(success_flag)
                            print(f"[PARENT] Character recruited: {success_flag}")

                            # 캐릭터 완료, 초기화
                            state["temp_data"].pop(current_char_key, None)
                            state["temp_data"].pop(stage_idx_key, None)

                            # 모든 캐릭터 완료 확인
                            all_recruited = all(
                                f"{c_data.get('stages', [{}])[-1].get('success_flag')}"
                                in state.get("system_flags", [])
                                for c_data in characters.values()
                            )

                            if all_recruited:
                                # 🔥 미션 완료: 히든 엔딩 조건 확인
                                mission_turn_key = (
                                    f"{current_stage}_total_mission_turns"
                                )
                                total_mission_turns = state.get("temp_data", {}).get(
                                    mission_turn_key, 0
                                )

                                MAX_MISSION_TURNS_FOR_HIDDEN = 5

                                # 히든 엔딩 조건: 5턴 이하
                                if total_mission_turns <= MAX_MISSION_TURNS_FOR_HIDDEN:
                                    # 히든 엔딩
                                    next_stage = current_scene_data.get(
                                        "hidden_ending_stage",
                                        current_scene_data.get("next_stage"),
                                    )
                                    state["system_flags"].append(
                                        "hidden_ending_unlocked"
                                    )
                                    print(
                                        f"[PARENT] 🌟 히든 엔딩 달성! (미션 턴: {total_mission_turns}/{MAX_MISSION_TURNS_FOR_HIDDEN}) → {next_stage}"
                                    )
                                else:
                                    # 일반 엔딩
                                    next_stage = current_scene_data.get("next_stage")
                                    print(
                                        f"[PARENT] 일반 엔딩 (미션 턴: {total_mission_turns} > {MAX_MISSION_TURNS_FOR_HIDDEN}) → {next_stage}"
                                    )

                                if next_stage:
                                    state["current_stage"] = next_stage
                                    state["stage_history"].append(next_stage)
                    else:
                        print(
                            f"[PARENT] Keywords not matched. Showing current stage dialogue again."
                        )

                    print(
                        f"[PARENT] Mission stage {stage_idx}: {len(state['agent_responses'])} dialogues"
                    )
                    return state

            elif target_char:
                # 🔥 순서 검증: 이노스케 → 젠이츠 순서 강제
                correct_order = ["inosuke", "zenitsu"]
                recruited_flags = state.get("system_flags", [])

                # 이미 모집된 캐릭터 확인
                recruited_chars = []
                if "inosuke_recruited" in recruited_flags:
                    recruited_chars.append("inosuke")
                if "zenitsu_recruited" in recruited_flags:
                    recruited_chars.append("zenitsu")

                # 다음으로 모집해야 할 캐릭터 결정
                expected_next = None
                for char_id in correct_order:
                    if char_id not in recruited_chars:
                        expected_next = char_id
                        break

                # 순서 검증
                if expected_next and target_char != expected_next:
                    char_names = {"inosuke": "이노스케", "zenitsu": "젠이츠"}
                    state["agent_responses"] = [
                        {
                            "speaker": "시스템",
                            "text": f"❌ 순서 오류! 먼저 {char_names.get(expected_next, expected_next)}를 설득해야 합니다.",
                        }
                    ]
                    state["user_input_prompt"] = current_scene_data.get(
                        "user_prompt", "선택하세요"
                    )
                    print(
                        f"[PARENT] Order validation failed: expected {expected_next}, got {target_char}"
                    )
                    return state

                # 새 캐릭터 선택
                if "temp_data" not in state:
                    state["temp_data"] = {}
                state["temp_data"][current_char_key] = target_char
                state["temp_data"][f"{current_stage}_{target_char}_stage"] = 0

                # 캐릭터별 턴 카운터 초기화
                char_turn_key = f"{current_stage}_{target_char}_turns"
                if char_turn_key not in state.get("temp_data", {}):
                    state["temp_data"][char_turn_key] = 0

                print(f"[PARENT] Mission target: {target_char} (순서 검증 통과)")

                # 첫 stage 대사 표시 (LLM 생성)
                char_data = characters[target_char]
                stages = char_data.get("stages", [])
                if stages:
                    stage = stages[0]
                    speakers = stage.get("speakers", [])
                    contents = stage.get("contents", [])
                    emotions = stage.get("emotions", [])
                    user_prompt = stage.get("user_prompt", "입력하세요")

                    state["agent_responses"] = []
                    state = _generate_dialogue_with_children(
                        state=state,
                        speakers=speakers,
                        contents=contents,
                        emotions=emotions,
                        stage_type="mission",
                    )

                    state["user_input_prompt"] = user_prompt
                    print(f"[PARENT] Mission char start: {target_char}, stage 0")
                    return state

        elif stage_type == "branch":
            # 분기 처리 - 조건 평가 필요
            scenario_data = state.get("scenario_data")
            if scenario_data:
                conditions = scenario_loader.evaluate_branch_conditions(
                    state, current_scene_data
                )
                print(f"[PARENT] Branch conditions: {conditions}")

                # 조건에 맞는 분기 찾기
                branches = current_scene_data.get("branches", [])
                for branch in branches:
                    branch_conds = branch.get("conditions", [])

                    # default는 항상 매칭
                    if "default" in branch_conds:
                        next_stage = branch.get("next_stage")
                        print(f"[PARENT] Default branch → {next_stage}")
                        state["current_stage"] = next_stage
                        break

                    # 모든 조건 만족 확인
                    if all(conditions.get(cond, False) for cond in branch_conds):
                        next_stage = branch.get("next_stage")
                        print(
                            f"[PARENT] Branch matched: {branch.get('id')} → {next_stage}"
                        )
                        state["current_stage"] = next_stage
                        break

        elif stage_type == "ending":
            # 🔥 Ending 처리: 대사 표시
            dialogues = current_scene_data.get("dialogues", [])

            # 엔딩 전용 턴 카운터 사용 (temp_data에 저장)
            ending_turn_key = f"{current_stage}_ending_turn"
            if "temp_data" not in state:
                state["temp_data"] = {}

            ending_turn = state["temp_data"].get(ending_turn_key, 0)
            turn_dialogue = next(
                (d for d in dialogues if d.get("turn") == ending_turn), None
            )

            if not turn_dialogue:
                # 대사 완료, 엔딩
                print(f"[PARENT] Ending complete: {current_stage}")
                state["final_ending"] = current_stage
                state["next_node"] = "END"

                # 엔딩 완료 메시지 추가
                state["agent_responses"] = [
                    {
                        "speaker": "시스템",
                        "text": f"🎬 '{current_scene_data.get('title', '엔딩')}' 완료\n\n게임이 종료되었습니다. 감사합니다!",
                    }
                ]
                state["user_input_prompt"] = "게임 종료 (exit 입력)"
                return state
            else:
                # 엔딩 대사 표시 (LLM 생성)
                speakers = turn_dialogue.get("speakers", [])
                contents = turn_dialogue.get("contents", [])
                emotions = turn_dialogue.get("emotions", [])
                user_prompt = turn_dialogue.get("user_prompt", "계속하려면 입력하세요")

                state["agent_responses"] = []
                state = _generate_dialogue_with_children(
                    state=state,
                    speakers=speakers,
                    contents=contents,
                    emotions=emotions,
                    stage_type="ending",
                )

                # 엔딩 턴 증가
                state["temp_data"][ending_turn_key] = ending_turn + 1

                state["user_input_prompt"] = user_prompt
                print(
                    f"[PARENT] Ending dialogues (turn {ending_turn}): {len(state['agent_responses'])} loaded"
                )
                return state
    else:
        print(f"[PARENT] No scene data, continuing normal dialogue")

    # 4. 다음 노드 결정
    state["next_node"] = "state_tools"

    # Meta 업데이트
    if "meta" in state and isinstance(state["meta"], dict):
        state["meta"]["processed_by"] = "parent"

    print(f"[PARENT] Done → {state['next_node']}")
    return state


# 테스트용 함수
def test_parent_agent():
    from src.core.graph_state import create_enhanced_initial_state

    # 테스트: 동료 설득 시나리오
    state = create_enhanced_initial_state("test", scene_id="scene5_recruit_mission")
    state.user_input.content = "이노스케야, 함께 싸우자! 너는 정말 강하니까!"
    state.characters.available_characters = ["inosuke"]

    result_state = run_parent_agent(state)

    print("=== Parent Agent 테스트 결과 ===")
    _debug_print(f"씬: {result_state.scene.current_scene}")
    _debug_print(f"플래그: {result_state.game.flags}")
    _debug_print(f"친밀도: {result_state.characters.affinity}")
    _debug_print(
        f"대화 규칙: {result_state.parent_decisions.speaking_rules if result_state.parent_decisions else 'None'}"
    )
    _debug_print(f"다음 노드: {result_state.next_node}")


if __name__ == "__main__":
    test_parent_agent()
