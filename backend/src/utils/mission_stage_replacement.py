"""
MissionManager 통합 버전의 _handle_mission_stage
parent_agent_enhanced.py의 line 759-1144를 대체할 코드
"""

def _handle_mission_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
    """
    🔄 미션 스테이지 처리 (MissionManager 통합)

    MissionManager를 사용하여 턴 관리, 순서 검증, 친밀도 변화를 처리합니다.
    """
    self.logger.log("Parent", "mission_stage_entered", {
        "stage": state.game.current_stage,
        "characters": list(stage_data.get("characters", {}).keys())
    })

    # 🔥 MissionManager 인스턴스 생성 또는 재사용
    manager_key = f"{state.game.current_stage}_manager"

    if manager_key not in state.game.temp_data:
        # 첫 진입: MissionManager 초기화
        manager = MissionManager(stage_data)
        mission_state = manager.start_mission()

        state.game.temp_data[manager_key] = {
            "manager": manager,
            "mission_state": mission_state
        }
        state.game.add_flag(f"{state.game.current_stage}_entered")

        # 가이드 캐릭터 설정
        guide_char = stage_data.get("guide_character", self.config.get("main_guide_character", "tanjiro"))
        state.characters.available_characters = [guide_char]

        # 미션 안내 메시지
        objective = stage_data.get("objective", "동료들을 설득하세요!")
        state.parent_decisions.dialogue_context = [
            {
                "speaker": guide_char,
                "situation": f"🎯 임무: {objective}",
                "emotion": "determined"
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
    guide_char = stage_data.get("guide_character", self.config.get("main_guide_character", "tanjiro"))
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
                            "emotion": greeting.get("emotion", "neutral")
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
            increment_turn_on_success=True
        )

        # 응답 데이터를 dialogue_context로 전달
        if response:
            dialogues = []

            # 캐릭터 응답
            content = response.get("content", "")
            speaker = response.get("speaker", current_target)
            emotion = response.get("emotion", "neutral")

            if content:
                dialogues.append({
                    "speaker": speaker,
                    "situation": content,
                    "emotion": emotion
                })

            # Tanjiro 지원 메시지
            if "tanjiro_support" in response:
                support = response["tanjiro_support"]
                dialogues.append({
                    "speaker": support.get("speaker", "tanjiro"),
                    "situation": support.get("content", ""),
                    "emotion": support.get("emotion", "neutral")
                })

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

            self.logger.log("Parent", "mission_success", {
                "turns_used": mission_state.current_turn,
                "recruitment_order": mission_state.recruitment_order
            })

        elif status == MissionStatus.TIMEOUT:
            # 타임아웃 엔딩으로 전환
            state.output.add_system_message(status_msg)
            state.game.add_flag(f"{state.game.current_stage}_failed")

            # end_timeout 스테이지로 전환
            next_stage = "end_timeout"
            state.game.stage_history.append(next_stage)
            state.game.current_stage = next_stage

            self.logger.log("Parent", "mission_timeout", {
                "turns_used": mission_state.current_turn,
                "recruitment_order": mission_state.recruitment_order
            })

        elif status == MissionStatus.FAILED:
            # 실패 (순서 오류 등) - 타임아웃과 동일하게 처리
            state.output.add_system_message(status_msg)
            state.game.add_flag(f"{state.game.current_stage}_failed")

            next_stage = "end_timeout"
            state.game.stage_history.append(next_stage)
            state.game.current_stage = next_stage

            self.logger.log("Parent", "mission_failed", {
                "reason": status_msg,
                "recruitment_order": mission_state.recruitment_order
            })

    # 상태 저장
    state.game.temp_data[manager_key] = {
        "manager": manager,
        "mission_state": mission_state
    }

    return state
