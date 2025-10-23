"""
ImageManager - 시나리오 진행에 따른 이미지 전환 관리 (v2.0)

확장성과 성능을 위한 완전 재설계:
- 우선순위 기반 매칭 시스템
- 다중 조건 지원 (stage, dialogue_count, turn, flags)
- 상세 디버깅 로그
- 스마트 Fallback 체인
- LLM 기반 이미지 선택 (v2.1)
"""

import json
import os
from typing import Dict, Any, List, Optional, Union
from src.utils.llm_client import LLMClient


class ImageManager:
    """
    시나리오 진행 상태에 따라 적절한 이미지를 결정하는 클래스 (v2.0)

    JSON 설정 파일 형식:
    {
        "default_image": "default.png",
        "mappings": [
            {
                "priority": 100,
                "stage": "INTRO" or ["INTRO", "STAGE1"],
                "turn": [0, 5] or 3,
                "dialogue_count": [0, 13],
                "flags": ["akaza_encountered"],  # optional
                "image": "cutscene_01_derail.png",
                "description": "설명"
            },
            ...
        ]
    }
    """

    def __init__(self, config_path: str, debug: bool = True,
                 use_llm: bool = True, llm_metadata_path: Optional[str] = None):
        """
        Args:
            config_path: 이미지 매핑 JSON 파일 경로
            debug: 디버깅 로그 출력 여부
            use_llm: LLM 기반 이미지 선택 사용 여부
            llm_metadata_path: 이미지 메타데이터 JSON 파일 경로 (LLM용)
        """
        self.config_path = config_path
        self.debug = debug
        self.mappings: List[Dict] = []
        self.default_image = "default.png"

        # LLM 기반 이미지 선택 설정
        self.use_llm = use_llm
        self.llm_metadata_path = llm_metadata_path
        self.image_metadata: List[Dict] = []
        self.llm_client: Optional[LLMClient] = None

        self._load_config()

        # LLM 설정이 활성화된 경우 초기화
        if self.use_llm and llm_metadata_path:
            self._load_image_metadata()
            self._init_llm_client()

    def _load_config(self):
        """JSON 설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.default_image = config.get('default_image', 'default.png')
                self.mappings = config.get('mappings', [])

                # 우선순위 기준으로 정렬 (높은 순서대로)
                self.mappings.sort(key=lambda m: m.get('priority', 0), reverse=True)

                print(f"✅ ImageManager loaded: {len(self.mappings)} mappings from {self.config_path}")
                if self.debug:
                    print(f"   Default image: {self.default_image}")
                    print(f"   Priority range: {self.mappings[0].get('priority', 0)} ~ {self.mappings[-1].get('priority', 0)}")
        except FileNotFoundError:
            print(f"⚠️ Image config not found: {self.config_path}, using defaults")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing image config: {e}")

    def get_current_image(self, state: Dict[str, Any]) -> str:
        """
        현재 state에 맞는 이미지 파일명 반환 (LLM 우선, 규칙 기반 fallback)

        Args:
            state: GraphState 또는 state dict
                - current_stage: str (e.g., "INTRO", "ROUTE_CHOICE")
                - scene.turn_count: int
                - dialogues_generated_count: int
                - stage_dialogue_counts: dict (스테이지별 대화 수)
                - event_flags: list (선택적)
                - output.dialogues: list (최근 대화 목록, LLM 분석용)

        Returns:
            이미지 파일명 (e.g., "cutscene_01_derail.png" or "3")
        """
        # 1단계: LLM 기반 이미지 선택 시도
        if self.use_llm and self.image_metadata:
            llm_result = self.select_with_llm(state)
            if llm_result:
                return llm_result

        # 2단계: 규칙 기반 매칭 (기존 로직)
        current_stage = (state.get('current_stage', '') or '').upper()
        turn_count = state.get('scene', {}).get('turn_count', 0)
        total_dialogue_count = state.get('dialogues_generated_count', 0)

        # 스테이지별 대화 수 (우선 사용)
        stage_dialogue_counts = state.get('stage_dialogue_counts', {})
        stage_dialogue_count = stage_dialogue_counts.get(current_stage, 0)

        # fallback: 전체 대화 수 사용
        dialogue_count = stage_dialogue_count if stage_dialogue_count > 0 else total_dialogue_count

        event_flags = state.get('event_flags', [])

        if self.debug:
            print(f"🔍 [ImageManager] Matching image:")
            print(f"   Stage: {current_stage}")
            print(f"   Turn: {turn_count}")
            print(f"   Dialogue (total): {total_dialogue_count}")
            print(f"   Dialogue (stage): {stage_dialogue_count}")
            print(f"   Flags: {event_flags}")
            print(f"   Checking {len(self.mappings)} mappings...")

        # 우선순위 순으로 매핑 검사
        for idx, mapping in enumerate(self.mappings):
            priority = mapping.get('priority', 0)

            if self.debug:
                print(f"\n   [{idx+1}/{len(self.mappings)}] Priority {priority}: {mapping.get('description', 'N/A')}")

            # 모든 조건 체크
            if not self._matches_stage(mapping, current_stage):
                if self.debug:
                    print(f"      ❌ Stage mismatch (expected: {mapping.get('stage')})")
                continue

            if not self._matches_turn(mapping, turn_count):
                if self.debug:
                    print(f"      ❌ Turn mismatch (expected: {mapping.get('turn')})")
                continue

            if not self._matches_dialogue_count(mapping, dialogue_count):
                if self.debug:
                    print(f"      ❌ Dialogue count mismatch (expected: {mapping.get('dialogue_count')})")
                continue

            if not self._matches_flags(mapping, event_flags):
                if self.debug:
                    print(f"      ❌ Flags mismatch (expected: {mapping.get('flags')})")
                continue

            # 모든 조건 만족!
            selected_image = mapping['image']
            if self.debug:
                print(f"      ✅ ALL CONDITIONS MET!")
                print(f"      → Selected image: {selected_image}")

            return selected_image

        # 모든 매핑이 실패하면 None 반환 (기존 이미지 유지)
        if self.debug:
            print(f"\n   ⚠️ No matching mapping found, keeping current image")

        return None

    def _matches_stage(self, mapping: Dict, current_stage: str) -> bool:
        """스테이지 매칭 검사"""
        stage_condition = mapping.get('stage')

        if stage_condition is None:
            return True  # 조건 없음 = 모든 스테이지 허용

        # 단일 문자열
        if isinstance(stage_condition, str):
            return current_stage == stage_condition.upper()

        # 리스트 (여러 스테이지 중 하나)
        if isinstance(stage_condition, list):
            return current_stage in [s.upper() for s in stage_condition]

        return False

    def _matches_turn(self, mapping: Dict, turn_count: int) -> bool:
        """턴 카운트 매칭 검사"""
        turn_condition = mapping.get('turn')

        if turn_condition is None:
            return True  # 조건 없음

        # 범위 [min, max]
        if isinstance(turn_condition, list) and len(turn_condition) == 2:
            min_turn, max_turn = turn_condition
            return min_turn <= turn_count <= max_turn

        # 정확한 값
        if isinstance(turn_condition, int):
            return turn_count == turn_condition

        return False

    def _matches_dialogue_count(self, mapping: Dict, dialogue_count: int) -> bool:
        """대화 카운트 매칭 검사"""
        dialogue_condition = mapping.get('dialogue_count')

        if dialogue_condition is None:
            return True  # 조건 없음

        # 범위 [min, max]
        if isinstance(dialogue_condition, list) and len(dialogue_condition) == 2:
            min_count, max_count = dialogue_condition
            return min_count <= dialogue_count <= max_count

        # 정확한 값
        if isinstance(dialogue_condition, int):
            return dialogue_count == dialogue_condition

        return False

    def _matches_flags(self, mapping: Dict, event_flags: List[str]) -> bool:
        """이벤트 플래그 매칭 검사"""
        required_flags = mapping.get('flags')

        if not required_flags:
            return True  # 조건 없음

        # 모든 required_flags가 event_flags에 포함되어야 함
        if isinstance(required_flags, list):
            return all(flag in event_flags for flag in required_flags)

        return False

    # ==================== LLM 기반 이미지 선택 (v2.1) ====================

    def _load_image_metadata(self):
        """이미지 메타데이터 JSON 로드 (LLM 분석용)"""
        try:
            with open(self.llm_metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.image_metadata = data.get('images', [])
                print(f"✅ Image metadata loaded: {len(self.image_metadata)} images from {self.llm_metadata_path}")
        except FileNotFoundError:
            print(f"⚠️ Image metadata not found: {self.llm_metadata_path}")
            self.use_llm = False
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing image metadata: {e}")
            self.use_llm = False

    def _init_llm_client(self):
        """LLM 클라이언트 초기화 (이미지 선택 전용 모델)"""
        try:
            # 환경변수에서 이미지 선택 전용 모델 가져오기
            image_model = os.getenv("IMAGE_SELECTOR_MODEL", "gpt-3.5-turbo")
            self.llm_client = LLMClient(model=image_model)
            print(f"✅ LLM client initialized for image selection: {image_model}")
        except Exception as e:
            print(f"⚠️ Failed to initialize LLM client: {e}")
            self.use_llm = False

    def _get_recent_dialogues(self, state: Dict[str, Any], limit: int = 15) -> List[Dict]:
        """
        최근 N개 대화 추출 (LLM 분석용)

        Args:
            state: GraphState
            limit: 추출할 대화 수 (기본: 15)

        Returns:
            최근 대화 리스트
        """
        # output.dialogues에서 대화 추출
        dialogues = state.get('output', {}).get('dialogues', [])

        # 리스트가 아닌 경우 빈 리스트 반환
        if not isinstance(dialogues, list):
            return []

        # 최근 N개만 반환
        if len(dialogues) > limit:
            return dialogues[-limit:]
        return dialogues

    def select_with_llm(self, state: Dict[str, Any]) -> Optional[str]:
        """
        LLM을 사용하여 대화 내용 기반으로 이미지 선택

        Args:
            state: GraphState

        Returns:
            선택된 이미지 인덱스 (e.g., "3") 또는 None (실패 시)
        """
        if not self.llm_client or not self.image_metadata:
            return None

        try:
            # 최근 대화 추출
            recent_dialogues = self._get_recent_dialogues(state, limit=15)

            # 대화가 없으면 LLM 분석 스킵
            if not recent_dialogues:
                if self.debug:
                    print(f"🤖 [LLM] No dialogues to analyze, skipping LLM selection")
                return None

            # 대화를 텍스트로 포맷
            dialogue_lines = []
            for d in recent_dialogues:
                speaker = d.get('speaker', 'unknown')
                text = d.get('text', d.get('content', ''))
                dialogue_lines.append(f"[{speaker}] {text}")

            dialogue_text = "\n".join(dialogue_lines)

            # 이미지 목록을 텍스트로 포맷
            image_lines = []
            for img in self.image_metadata:
                index = img['index']
                name = img['name']
                description = img['description']
                image_lines.append(f"{index}. {name} - {description}")

            images_text = "\n".join(image_lines)

            # 현재 상태 정보
            current_stage = state.get('current_stage', 'unknown')
            dialogue_count = state.get('dialogues_generated_count', 0)
            event_flags = state.get('event_flags', [])
            flags_text = ", ".join(event_flags) if event_flags else "없음"

            # LLM 프롬프트 생성
            system_prompt = """당신은 애니메이션 장면 분석 전문가입니다.
주어진 대화 내용을 분석하여 가장 어울리는 배경 이미지를 선택하세요.

선택 기준:
1. 대화에 등장하는 캐릭터
2. 대화의 분위기와 감정
3. 현재 스토리 진행 상황
4. 중요한 사건이나 전환점"""

            user_prompt = f"""=== 최근 대화 ({len(recent_dialogues)}개) ===
{dialogue_text}

=== 현재 게임 상태 ===
Stage: {current_stage}
Dialogue Count: {dialogue_count}
Event Flags: {flags_text}

=== 선택 가능한 이미지 ({len(self.image_metadata)}개) ===
{images_text}

위 대화 내용을 분석하여 가장 어울리는 배경 이미지를 선택하세요.
대화에 등장하는 캐릭터, 감정, 상황을 고려하세요.

JSON 형식으로 응답하세요:
{{
  "selected_index": "3",
  "reason": "선택 이유 (간단히)"
}}"""

            if self.debug:
                print(f"\n🤖 [LLM] Analyzing {len(recent_dialogues)} dialogues for image selection...")

            # LLM 호출
            response = self.llm_client.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200
            )

            # 응답 파싱
            selected_index = response.get('selected_index')
            reason = response.get('reason', 'N/A')

            if selected_index:
                if self.debug:
                    print(f"🤖 [LLM] Selected image: {selected_index}")
                    print(f"    Reason: {reason}")
                return str(selected_index)
            else:
                if self.debug:
                    print(f"⚠️ [LLM] No image selected in response")
                return None

        except Exception as e:
            if self.debug:
                print(f"⚠️ [LLM] Image selection failed: {e}")
            return None
