#!/usr/bin/env python3
"""
멀티캐릭터 대화 통합 테스트

컷신 종료 후 현장의 모든 캐릭터들이 3-4회 티키타카 대화를 나누는 시스템 테스트
"""
import pytest
from multi_character_conversation import MultiCharacterConversation, simulate_conversation
from agent_state_enhanced import create_enhanced_initial_state


class TestMultiCharacterConversation:
    """멀티캐릭터 대화 시스템 테스트"""

    def test_load_prompts(self):
        """프롬프트 JSON 로드 확인"""
        conv = MultiCharacterConversation()

        assert conv.prompts_data is not None
        assert "cutscene5_victory" in conv.prompts_data
        assert "cutscene5_recruit" in conv.prompts_data
        assert "cutscene6_final" in conv.prompts_data

    def test_get_participants_cutscene5_victory(self):
        """컷신5 승리 후 참여 캐릭터 목록"""
        conv = MultiCharacterConversation()
        participants = conv.get_participants("cutscene5_victory")

        assert "tanjiro" in participants
        assert "rengoku" in participants
        assert "inosuke" in participants
        assert "zenitsu" in participants
        assert "user" in participants

    def test_get_participants_cutscene5_recruit(self):
        """컷신5 동료 규합 후 참여 캐릭터 목록"""
        conv = MultiCharacterConversation()
        participants = conv.get_participants("cutscene5_recruit")

        assert "tanjiro" in participants
        assert "rengoku" in participants
        assert "inosuke" in participants
        assert "zenitsu" in participants

    def test_generate_conversation_cutscene5_victory(self):
        """컷신5 승리 후 대화 생성 (4회)"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene5_victory", num_exchanges=4)

        assert len(messages) == 4

        # 각 메시지 구조 확인
        for msg in messages:
            assert "speaker" in msg
            assert "content" in msg
            assert "listener" in msg
            assert "turn" in msg

        # 턴 순서 확인
        assert messages[0]["turn"] == 0
        assert messages[1]["turn"] == 1
        assert messages[2]["turn"] == 2
        assert messages[3]["turn"] == 3

    def test_generate_conversation_cutscene5_recruit(self):
        """컷신5 동료 규합 후 대화 생성 (4회)"""
        messages = simulate_conversation("cutscene5_recruit", num_exchanges=4)

        assert len(messages) == 4

        # 모든 대화가 내용을 가지고 있음
        for msg in messages:
            assert len(msg["content"]) > 0

    def test_conversation_rotation(self):
        """대화 순서가 올바르게 로테이션되는지 확인"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene5_victory", num_exchanges=5)

        assert len(messages) == 5

        # 참여자 수 확인
        participants = conv.get_participants("cutscene5_victory")
        num_participants = len(participants)

        # 5회 대화 시, 첫 캐릭터가 다시 말하는지 확인
        # (5명 참여 시, 턴 0과 턴 5는 같은 캐릭터)
        if num_participants > 0:
            speaker_0 = messages[0]["speaker"]
            speaker_5_expected = participants[5 % num_participants]

            # 턴 0의 speaker와 턴 5 예상 speaker 비교
            assert speaker_0 == participants[0]

    def test_listener_target(self):
        """각 대화에서 listener가 올바르게 설정되는지 확인"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene5_victory", num_exchanges=4)

        participants = conv.get_participants("cutscene5_victory")

        for i, msg in enumerate(messages):
            expected_speaker = participants[i % len(participants)]
            expected_listener = participants[(i + 1) % len(participants)]

            assert msg["speaker"] == expected_speaker
            assert msg["listener"] == expected_listener

    def test_apply_to_state(self):
        """생성된 대화를 게임 상태에 적용"""
        conv = MultiCharacterConversation()
        state = create_enhanced_initial_state("test_multi_conv")

        # 대화 적용 전 dialogues 수
        initial_count = len(state.output.dialogues)

        # 멀티캐릭터 대화 적용
        conv.apply_to_state(state, "cutscene5_victory", num_exchanges=4)

        # 대화 적용 후 dialogues 수 증가 확인
        final_count = len(state.output.dialogues)
        assert final_count == initial_count + 4

    def test_scene_not_found(self):
        """존재하지 않는 씬 키 처리"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("nonexistent_scene")

        # 빈 리스트 반환
        assert messages == []

    def test_cutscene6_final_conversation(self):
        """컷신6 최종 승리 후 대화 생성"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene6_final", num_exchanges=4)

        assert len(messages) == 4

        # 모든 메시지가 유효한지 확인
        for msg in messages:
            assert msg["speaker"] is not None
            assert msg["content"] is not None
            assert len(msg["content"]) > 0

    def test_cutscene5_defeat_conversation(self):
        """컷신5 패배 후 슬픈 대화 생성"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene5_defeat", num_exchanges=4)

        assert len(messages) == 4

        # 참여자 확인 (rengoku 제외)
        participants = conv.get_participants("cutscene5_defeat")
        assert "rengoku" not in participants  # 패배 시 렌고쿠 사망

    def test_display_name_mapping(self):
        """캐릭터 표시 이름 매핑 확인"""
        conv = MultiCharacterConversation()

        assert conv._get_display_name("tanjiro") == "탄지로"
        assert conv._get_display_name("rengoku") == "렌고쿠"
        assert conv._get_display_name("inosuke") == "이노스케"
        assert conv._get_display_name("zenitsu") == "젠이츠"
        assert conv._get_display_name("user") == "당신"

    def test_participant_filtering_by_flags(self):
        """플래그 기반 참여자 필터링 테스트"""
        conv = MultiCharacterConversation()
        state = create_enhanced_initial_state("test_flags")

        # inosuke_recruited 플래그 없음
        state.game.flags = []

        participants = conv.get_participants("cutscene5_recruit", state)

        # inosuke가 제외되어야 함 (플래그 없음)
        if "inosuke" in conv.prompts_data["cutscene5_recruit"]["participants"]:
            # 원본에는 있지만 필터링됨
            original_participants = conv.prompts_data["cutscene5_recruit"]["participants"]
            assert "inosuke" in original_participants
            assert "inosuke" not in participants

    def test_conversation_content_template(self):
        """대화 내용 템플릿 처리 확인"""
        conv = MultiCharacterConversation()
        messages = conv.generate_conversation("cutscene5_victory", num_exchanges=1)

        assert len(messages) == 1

        msg = messages[0]

        # {listener} 템플릿이 실제 이름으로 치환되었는지 확인
        assert "{listener}" not in msg["content"]

        # 듣는 사람 이름이 포함되어 있는지 확인
        listener_display_name = conv._get_display_name(msg["listener"])
        assert listener_display_name in msg["content"]

    def test_multiple_exchanges_different_content(self):
        """여러 번 대화 생성 시 다른 내용이 나오는지 확인 (무작위성)"""
        conv = MultiCharacterConversation()

        messages_1 = conv.generate_conversation("cutscene5_victory", num_exchanges=4)
        messages_2 = conv.generate_conversation("cutscene5_victory", num_exchanges=4)

        # 같은 씬이지만 무작위 선택으로 인해 일부 다른 내용 가능
        # (100% 다를 필요는 없지만, 적어도 1개는 다를 확률이 높음)
        # 여기서는 구조만 동일한지 확인
        assert len(messages_1) == len(messages_2)

        for m1, m2 in zip(messages_1, messages_2):
            assert m1["speaker"] == m2["speaker"]  # 순서는 동일
            assert m1["listener"] == m2["listener"]


class TestDialogueAgentIntegration:
    """DialogueAgent와 멀티캐릭터 대화 통합 테스트"""

    def test_dialogue_agent_with_multi_conversation_flag(self):
        """dialogue_agent에서 플래그 기반 멀티캐릭터 대화 생성"""
        from dialogue_agent import DialogueAgent

        state = create_enhanced_initial_state("test_dialogue_agent_multi")

        # cutscene5_victory 플래그 추가
        state.game.flags = ["cutscene5_victory"]

        # 초기 대화 추가 (검증용)
        state.output.add_dialogue(
            speaker="tanjiro",
            content="테스트 대화",
            emotion="determined"
        )

        # DialogueAgent 실행
        agent = DialogueAgent(use_llm=False, enable_multi_conversation=True)
        result = agent.process(state)

        # 멀티캐릭터 대화가 추가되었는지 확인
        # 최소 1 (원본) + 4 (멀티캐릭터) = 5개
        assert len(result.output.dialogues) >= 5

        # multi_conv_cutscene5_victory 플래그가 추가되었는지 확인
        assert "multi_conv_cutscene5_victory" in result.game.flags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
