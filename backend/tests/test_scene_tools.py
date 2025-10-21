"""
Scene Tools 테스트
"""
import unittest
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent_state_enhanced import create_enhanced_initial_state, SceneToolRequest
from scene_tools_nanobanana import get_scene_tools

class TestSceneTools(unittest.TestCase):
    """Scene Tools 테스트"""

    def test_get_cutscene_image(self):
        """컷신 이미지 가져오기 테스트"""
        async def run_test():
            tools = get_scene_tools()

            state = create_enhanced_initial_state("test")
            state.game.turn = 2
            state.scene_tool_request = SceneToolRequest(
                action="get_cutscene",
                scene_id="scene5_cutscene_intro",
                turn=2,
                asset_type="cutscene"
            )

            result = await tools.process_request(state)

            self.assertEqual(result.scene_tool_response.status, "success")
            self.assertIsNotNone(result.scene_tool_response.image_url)

        asyncio.run(run_test())

    def test_get_emotion_image(self):
        """감정 이미지 가져오기 테스트"""
        async def run_test():
            tools = get_scene_tools()

            state = create_enhanced_initial_state("test")
            state.scene_tool_request = SceneToolRequest(
                action="get_emotion_image",
                scene_id="scene5_cutscene_intro",
                character_id="tanjiro",
                emotion="determined",
                asset_type="emotion"
            )

            result = await tools.process_request(state)

            self.assertEqual(result.scene_tool_response.status, "success")
            self.assertIsNotNone(result.scene_tool_response.image_url)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
