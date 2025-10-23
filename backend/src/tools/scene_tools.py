# 5. Scene Tools 구현 (이미지/에셋 관리)

"""
Scene Tools - 게임 씬 관련 이미지 및 에셋 관리
- 컷신 이미지: 턴에 따라 변화하는 배경/장면 이미지
- 감정 이미지: 캐릭터별 감정 상태에 따른 표정 이미지
- 특별 이미지: 히든엔딩 등 특별 상황용 생성 이미지

Router → ParentAgent
              ↓
        ChildrenAgent
              ↓
     ├─ SceneDialogueTools (LLM prompt / tone loader)
     └─ SceneTools (이미지 / 에셋)
     
"""

from typing import Dict, List, Optional
import json
import random
from datetime import datetime
from src.core.graph_state import AgentState, SceneToolRequest, SceneToolResponse

class SceneTools:
    def __init__(self, assets_db_path: str = "data/images_catalog.json"):
        """Scene Tools 초기화"""
        self.assets_db = self._load_assets_db(assets_db_path)
        
        # 에셋 타입별 처리 함수 매핑
        self.asset_handlers = {
            "cutscene": self._get_cutscene_image,
            "emotion": self._get_emotion_image,
            "special_clear": self._generate_special_image
        }
    
    def _load_assets_db(self, path: str) -> Dict:
        """이미지 에셋 데이터베이스 로드"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_assets_db()
    
    def _get_default_assets_db(self) -> Dict:
        """기본 이미지 에셋 데이터베이스"""
        return {
            "cutscene_images": {
                "scene5_cutscene_intro": {
                    "turn_1": "scene5_train_crash_01",
                    "turn_2": "scene5_akaza_appears_01", 
                    "turn_3": "scene5_rengoku_ready_01",
                    "turn_4": "scene5_standoff_01",
                    "turn_5": "scene5_decision_moment_01"
                },
                "scene5_fork1": {
                    "turn_1": "scene5_critical_choice_01",
                    "turn_2": "scene5_tension_builds_01",
                    "turn_3": "scene5_final_decision_01"
                },
                "scene5_recruit_mission": {
                    "turn_1": "scene5_inosuke_suspicious_01",
                    "turn_2": "scene5_zenitsu_scared_01", 
                    "turn_3": "scene5_persuasion_01",
                    "turn_4": "scene5_team_forming_01"
                }
            },
            "emotion_images": {
                "tanjiro": {
                    "worried": "tanjiro_worried_01",
                    "determined": "tanjiro_determined_01",
                    "happy": "tanjiro_happy_01",
                    "sad": "tanjiro_sad_01"
                },
                "inosuke": {
                    "excited": "inosuke_excited_01",
                    "competitive": "inosuke_competitive_01", 
                    "confused": "inosuke_confused_01",
                    "angry": "inosuke_angry_01"
                },
                "zenitsu": {
                    "scared": "zenitsu_scared_01",
                    "brave": "zenitsu_brave_01",
                    "determined": "zenitsu_determined_01",
                    "crying": "zenitsu_crying_01"
                },
                "rengoku": {
                    "encouraging": "rengoku_encouraging_01",
                    "serious": "rengoku_serious_01",
                    "proud": "rengoku_proud_01",
                    "battle_ready": "rengoku_battle_ready_01"
                }
            },
            "image_metadata": {
                "scene5_train_crash_01": {
                    "path": "assets/images/cutscenes/scene5_train_crash_01.png",
                    "url": "/static/images/cutscenes/scene5_train_crash_01.png",
                    "description": "탈선한 열차와 흩어진 잔해",
                    "mood": "dramatic"
                },
                "tanjiro_determined_01": {
                    "path": "assets/images/emotions/tanjiro_determined_01.png",
                    "url": "/static/images/emotions/tanjiro_determined_01.png",
                    "description": "결연한 의지를 보이는 탄지로",
                    "character": "tanjiro",
                    "emotion": "determined"
                }
            }
        }
    
    def process_request(self, state: AgentState) -> AgentState:
        """Scene Tools 요청 처리"""
        if not state.scene_tool_request:
            return state
        
        request = state.scene_tool_request
        asset_type = request.asset_type
        
        # 에셋 타입에 따른 처리
        if asset_type in self.asset_handlers:
            response = self.asset_handlers[asset_type](request, state)
        else:
            response = SceneToolResponse(
                status="error",
                error_message=f"지원하지 않는 에셋 타입: {asset_type}"
            )
        
        state.scene_tool_response = response
        
        # 성공적으로 처리된 경우 출력에 반영
        if response.status == "success" and response.image_id:
            self._apply_image_to_output(state, response, asset_type)
        
        return state
    
    def _get_cutscene_image(self, request: SceneToolRequest, state: AgentState) -> SceneToolResponse:
        """컷신 이미지 가져오기"""
        scene_id = request.scene_id
        turn = request.turn or state.game.turn

        # 씬별 컷신 이미지 찾기
        scene_cutscenes = self.assets_db["cutscene_images"].get(scene_id, {})

        # 턴에 맞는 이미지 찾기
        turn_key = f"turn_{turn}"
        turn_data = scene_cutscenes.get(turn_key)

        # turn_data가 dict인 경우 image_id 추출
        if isinstance(turn_data, dict):
            image_id = turn_data.get("image_id")
        elif isinstance(turn_data, str):
            image_id = turn_data
        else:
            image_id = None

        # 턴에 맞는 이미지가 없으면 마지막 이미지나 첫 번째 이미지 사용
        if not image_id and scene_cutscenes:
            available_turns = [int(k.split('_')[1]) for k in scene_cutscenes.keys() if k.startswith('turn_')]
            if available_turns:
                # 현재 턴보다 작거나 같은 가장 큰 턴의 이미지 사용
                suitable_turn = max([t for t in available_turns if t <= turn] or [min(available_turns)])
                turn_data = scene_cutscenes.get(f"turn_{suitable_turn}")

                # 다시 image_id 추출
                if isinstance(turn_data, dict):
                    image_id = turn_data.get("image_id")
                elif isinstance(turn_data, str):
                    image_id = turn_data

        if image_id:
            metadata = self.assets_db["image_metadata"].get(image_id, {})
            return SceneToolResponse(
                status="success",
                image_id=image_id,
                image_url=metadata.get("url"),
                generated=False
            )
        else:
            return SceneToolResponse(
                status="error",
                error_message=f"씬 {scene_id} 턴 {turn}에 해당하는 컷신 이미지를 찾을 수 없음"
            )
    
    def _get_emotion_image(self, request: SceneToolRequest, state: AgentState) -> SceneToolResponse:
        """감정 이미지 가져오기"""
        character_id = request.character_id
        emotion = request.emotion or "neutral"

        # 캐릭터별 감정 이미지 찾기
        character_emotions = self.assets_db["emotion_images"].get(character_id, {})
        emotion_data = character_emotions.get(emotion)

        # emotion_data가 dict인 경우 image_id 추출
        if isinstance(emotion_data, dict):
            image_id = emotion_data.get("image_id")
        elif isinstance(emotion_data, str):
            image_id = emotion_data
        else:
            image_id = None

        # 해당 감정 이미지가 없으면 기본 감정으로 대체
        if not image_id and character_emotions:
            # 기본 감정 우선순위
            fallback_emotions = ["neutral", "normal", list(character_emotions.keys())[0]]
            for fallback in fallback_emotions:
                if fallback in character_emotions:
                    fallback_data = character_emotions[fallback]
                    # 다시 image_id 추출
                    if isinstance(fallback_data, dict):
                        image_id = fallback_data.get("image_id")
                    elif isinstance(fallback_data, str):
                        image_id = fallback_data
                    if image_id:
                        break

        if image_id:
            metadata = self.assets_db["image_metadata"].get(image_id, {})
            return SceneToolResponse(
                status="success",
                image_id=image_id,
                image_url=metadata.get("url"),
                generated=False
            )
        else:
            return SceneToolResponse(
                status="error",
                error_message=f"캐릭터 {character_id}의 {emotion} 감정 이미지를 찾을 수 없음"
            )
    
    def _generate_special_image(self, request: SceneToolRequest, state: AgentState) -> SceneToolResponse:
        """특별 이미지 생성 (히든엔딩용)"""
        summary_context = request.summary_context or "특별한 결말"
        
        # 실제로는 이미지 생성 API를 호출하겠지만, 여기서는 시뮬레이션
        generated_image_id = f"special_generated_{state.meta.session_id}_{state.game.turn}"
        
        # 이미지 생성 프롬프트 구성
        generation_prompt = self._create_generation_prompt(state, summary_context)
        
        # 시뮬레이션: 실제로는 외부 API 호출
        success = self._simulate_image_generation(generation_prompt)
        
        if success:
            # 생성된 이미지 메타데이터 저장
            generated_metadata = {
                "path": f"assets/images/generated/{generated_image_id}.png",
                "url": f"/static/images/generated/{generated_image_id}.png",
                "description": f"특별 생성 이미지: {summary_context[:50]}...",
                "generation_prompt": generation_prompt,
                "generated_at": datetime.now().isoformat()
            }
            
            self.assets_db["image_metadata"][generated_image_id] = generated_metadata
            
            return SceneToolResponse(
                status="success",
                image_id=generated_image_id,
                image_url=generated_metadata["url"],
                generated=True
            )
        else:
            return SceneToolResponse(
                status="error",
                error_message="특별 이미지 생성에 실패했습니다",
                generated=False
            )
    
    def _create_generation_prompt(self, state: AgentState, summary_context: str) -> str:
        """이미지 생성 프롬프트 작성"""
        # 게임 상황과 대화 내용을 바탕으로 프롬프트 구성
        characters = ", ".join(state.characters.available_characters)
        scene_mood = state.scene.mood or "neutral"
        
        prompt = f"""
        demon slayer anime style illustration, 
        characters: {characters},
        scene: {state.scene.current_scene},
        mood: {scene_mood},
        context: {summary_context},
        high quality, detailed, emotional moment
        """
        
        return prompt.strip()
    
    def _simulate_image_generation(self, prompt: str) -> bool:
        """이미지 생성 시뮬레이션 (실제로는 외부 API)"""
        # 실제 구현에서는 DALL-E, Midjourney, Stable Diffusion 등의 API 호출
        # 여기서는 90% 확률로 성공하는 것으로 시뮬레이션
        return random.random() > 0.1
    
    def _apply_image_to_output(self, state: AgentState, response: SceneToolResponse, asset_type: str):
        """이미지를 출력에 적용"""
        if asset_type == "cutscene":
            state.output.cutscene_image = response.image_id
            state.output.ui_updates.show_cutscene = True
            state.output.ui_updates.background_change = True
            
        elif asset_type == "emotion":
            # 활성 캐릭터의 감정 이미지 설정
            if state.characters.active_character:
                state.output.emotion_images[state.characters.active_character] = response.image_id
            state.output.ui_updates.show_emotion_image = True
            
        elif asset_type == "special_clear":
            state.output.special_image = response.image_id
            state.output.ui_updates.show_special_image = True
    
    def get_image_metadata(self, image_id: str) -> Optional[Dict]:
        """이미지 메타데이터 조회"""
        return self.assets_db["image_metadata"].get(image_id)
    
    def list_available_images(self, character_id: str = None, emotion: str = None) -> List[str]:
        """사용 가능한 이미지 목록"""
        if character_id and emotion:
            character_emotions = self.assets_db["emotion_images"].get(character_id, {})
            image_id = character_emotions.get(emotion)
            return [image_id] if image_id else []
        elif character_id:
            return list(self.assets_db["emotion_images"].get(character_id, {}).values())
        else:
            return list(self.assets_db["image_metadata"].keys())

def run_scene_tools(state: AgentState) -> AgentState:
    """Scene Tools 실행 함수"""
    tools = SceneTools()
    return tools.process_request(state)

# 테스트용 함수
def test_scene_tools():
    from src.core.graph_state import create_enhanced_initial_state, SceneToolRequest
    
    # 테스트: 컷신 이미지 요청
    state = create_enhanced_initial_state("test", scene_id="scene5_cutscene_intro")
    state.game.turn = 2
    state.scene_tool_request = SceneToolRequest(
        action="get_cutscene",
        scene_id="scene5_cutscene_intro",
        turn=2,
        asset_type="cutscene"
    )
    
    result_state = run_scene_tools(state)
    
    print("=== Scene Tools 테스트 결과 ===")
    print(f"상태: {result_state.scene_tool_response.status}")
    print(f"이미지 ID: {result_state.scene_tool_response.image_id}")
    print(f"이미지 URL: {result_state.scene_tool_response.image_url}")
    print(f"컷신 이미지: {result_state.output.cutscene_image}")
    print(f"UI 업데이트: 컷신 표시={result_state.output.ui_updates.show_cutscene}")
    
    # 테스트: 감정 이미지 요청
    state.scene_tool_request = SceneToolRequest(
        action="get_emotion_image",
        scene_id="scene5_cutscene_intro",
        character_id="tanjiro",
        emotion="determined",
        asset_type="emotion"
    )
    
    result_state = run_scene_tools(state)
    
    print(f"\n감정 이미지 테스트:")
    print(f"상태: {result_state.scene_tool_response.status}")
    print(f"이미지 ID: {result_state.scene_tool_response.image_id}")
    print(f"감정 이미지들: {result_state.output.emotion_images}")

if __name__ == "__main__":
    test_scene_tools()