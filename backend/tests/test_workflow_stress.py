#!/usr/bin/env python3
"""
워크플로우 경계 스트레스 테스트
50회 반복 실행으로 안정성 검증
"""
import pytest
from agent_state_enhanced import create_enhanced_initial_state, UserChatInput
from langgraph_workflow import KimeChatWorkflow
from scenario_loader import scenario_loader
from datetime import datetime


class TestWorkflowStress:
    """워크플로우 스트레스 테스트"""

    def test_workflow_stability_50_iterations(self):
        """워크플로우 50회 반복 안정성 테스트"""
        workflow = KimeChatWorkflow()
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        success_count = 0

        for iteration in range(50):
            try:
                # 매 반복마다 새로운 상태 생성
                state = create_enhanced_initial_state(f"stress_test_{iteration}")
                state.game.scenario_data = scenario
                state.game.current_stage = "intro"

                # intro 스테이지 1턴 실행
                user_input = UserChatInput(
                    content="다음",
                    chat_no=1,
                    timestamp=datetime.now().isoformat()
                )

                # dict로 변환하여 workflow 호출
                state_dict = {
                    "session_id": state.session_id,
                    "user_input": {
                        "content": user_input.content,
                        "chat_no": user_input.chat_no,
                        "timestamp": user_input.timestamp
                    },
                    "game": {
                        "scenario_id": state.game.scenario_id,
                        "scenario_data": state.game.scenario_data,
                        "current_stage": state.game.current_stage,
                        "turn": state.game.turn,
                        "flags": state.game.flags,
                        "temp_data": state.game.temp_data
                    },
                    "characters": {
                        "available_characters": state.characters.available_characters,
                        "affinity": state.characters.affinity
                    },
                    "output": {
                        "dialogues": [],
                        "choices": [],
                        "system_messages": []
                    },
                    "meta": {
                        "processed_by": state.meta.processed_by,
                        "timestamp": state.meta.timestamp
                    },
                    "next_node": state.next_node
                }

                result = workflow.invoke(state_dict)

                # 결과 검증
                assert result is not None
                assert "game" in result
                assert "output" in result

                success_count += 1

            except Exception as e:
                pytest.fail(f"Iteration {iteration + 1} failed: {str(e)}")

        assert success_count == 50, f"Expected 50 successes, got {success_count}"

    def test_workflow_memory_leak_prevention(self):
        """메모리 누수 방지 검증 (temp_data 정리)"""
        workflow = KimeChatWorkflow()
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        for iteration in range(10):
            state = create_enhanced_initial_state(f"memory_test_{iteration}")
            state.game.scenario_data = scenario
            state.game.current_stage = "intro"

            # temp_data에 임시 데이터 추가
            state.game.temp_data["test_data"] = "x" * 1000

            user_input = UserChatInput(
                content="다음",
                chat_no=1,
                timestamp=datetime.now().isoformat()
            )

            state_dict = {
                "session_id": state.session_id,
                "user_input": {
                    "content": user_input.content,
                    "chat_no": user_input.chat_no,
                    "timestamp": user_input.timestamp
                },
                "game": {
                    "scenario_id": state.game.scenario_id,
                    "scenario_data": state.game.scenario_data,
                    "current_stage": state.game.current_stage,
                    "turn": state.game.turn,
                    "flags": state.game.flags,
                    "temp_data": state.game.temp_data
                },
                "characters": {
                    "available_characters": state.characters.available_characters,
                    "affinity": state.characters.affinity
                },
                "output": {
                    "dialogues": [],
                    "choices": [],
                    "system_messages": []
                },
                "meta": {
                    "processed_by": state.meta.processed_by,
                    "timestamp": state.meta.timestamp
                },
                "next_node": state.next_node
            }

            result = workflow.invoke(state_dict)

            # temp_data에 _process_depth만 남아있어야 함 (또는 비어있음)
            temp_data = result.get("game", {}).get("temp_data", {})
            # process_depth는 dialogue_agent에서 삭제되므로 비어있거나 manager 데이터만 존재
            assert len(temp_data) <= 2, f"temp_data not cleaned: {temp_data.keys()}"

    def test_concurrent_state_isolation(self):
        """동시 세션 상태 격리 검증"""
        workflow = KimeChatWorkflow()
        scenario = scenario_loader.load_scenario("cutscene5_akaza_encounter.json")

        # 3개의 독립적인 세션 생성
        sessions = []
        for i in range(3):
            state = create_enhanced_initial_state(f"concurrent_session_{i}")
            state.game.scenario_data = scenario
            state.game.current_stage = "intro"
            state.game.flags.add(f"session_{i}_flag")
            sessions.append(state)

        # 각 세션 개별 실행
        results = []
        for state in sessions:
            user_input = UserChatInput(
                content="다음",
                chat_no=1,
                timestamp=datetime.now().isoformat()
            )

            state_dict = {
                "session_id": state.session_id,
                "user_input": {
                    "content": user_input.content,
                    "chat_no": user_input.chat_no,
                    "timestamp": user_input.timestamp
                },
                "game": {
                    "scenario_id": state.game.scenario_id,
                    "scenario_data": state.game.scenario_data,
                    "current_stage": state.game.current_stage,
                    "turn": state.game.turn,
                    "flags": list(state.game.flags),
                    "temp_data": state.game.temp_data
                },
                "characters": {
                    "available_characters": state.characters.available_characters,
                    "affinity": state.characters.affinity
                },
                "output": {
                    "dialogues": [],
                    "choices": [],
                    "system_messages": []
                },
                "meta": {
                    "processed_by": state.meta.processed_by,
                    "timestamp": state.meta.timestamp
                },
                "next_node": state.next_node
            }

            result = workflow.invoke(state_dict)
            results.append(result)

        # 세션별 플래그가 격리되어 있는지 확인
        for i, result in enumerate(results):
            session_id = result.get("session_id")
            assert session_id == f"concurrent_session_{i}"

            # 다른 세션의 플래그가 섞이지 않았는지 확인
            flags = set(result.get("game", {}).get("flags", []))
            for j in range(3):
                if i == j:
                    # 자신의 플래그는 존재해야 함
                    assert f"session_{j}_flag" in flags
                else:
                    # 다른 세션의 플래그는 없어야 함
                    assert f"session_{j}_flag" not in flags
