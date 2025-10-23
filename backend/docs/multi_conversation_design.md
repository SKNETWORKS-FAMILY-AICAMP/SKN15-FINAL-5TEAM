# 다중 대화 시스템 설계

## 문제점 분석

### 현재 시스템의 한계
1. **턴당 1명만 발화**: Children Agent가 턴당 단일 캐릭터만 대사 생성
2. **시나리오 진행 오류**: Parent Agent가 JSON 시나리오를 제대로 따르지 못함
3. **유저 주도 대화**: 캐릭터가 먼저 상황 설명 없이 유저 입력만 기다림

### 요구사항
- **다중 캐릭터 대화**: 한 턴에 탄지로 → 유저 → 이노스케 → 젠이츠 → 유저 등 3-5회 대화
- **시나리오 준수**: JSON에 정의된 흐름대로 정확히 진행
- **캐릭터 주도**: 각 턴 시작 시 캐릭터가 먼저 상황 설명/질문

## 해결 방안

### 1. 다중 대화 턴 시스템

```
한 턴의 구조:
1. 시스템 나레이션 (상황 설명)
2. 캐릭터 A 발화 (상황 대응/질문)
3. 유저 입력
4. 캐릭터 B 발화 (유저 응답)
5. 캐릭터 C 발화 (추가 반응)
6. 유저 입력 (선택적)
...

최소 3회 대화 (캐릭터 → 유저 → 캐릭터)
```

### 2. JSON 구조 개선

#### cutscene 스테이지
```json
{
  "type": "cutscene",
  "dialogues": [
    {
      "turn": 0,
      "exchanges": [
        {"order": 0, "speaker": "system", "content": "..."},
        {"order": 1, "speaker": "tanjiro", "content": "...", "emotion": "worried"},
        {"order": 2, "speaker": "user", "input_prompt": "탄지로에게 대답하세요"},
        {"order": 3, "speaker": "rengoku", "content": "...", "emotion": "proud"}
      ]
    }
  ]
}
```

#### choice 스테이지
```json
{
  "type": "choice",
  "pre_choice_dialogues": [
    {
      "exchanges": [
        {"order": 0, "speaker": "system", "content": "..."},
        {"order": 1, "speaker": "tanjiro", "content": "...", "emotion": "urgent"},
        {"order": 2, "speaker": "user", "input_prompt": "어떻게 할지 결정하세요"}
      ]
    }
  ],
  "choices": [...]
}
```

#### mission 스테이지 (대화 중심)
```json
{
  "type": "mission",
  "characters": {
    "inosuke": {
      "conversation_stages": [
        {
          "stage": 0,
          "exchanges": [
            {"order": 0, "speaker": "inosuke", "content": "크하하! 누구냐!"},
            {"order": 1, "speaker": "user", "input_prompt": "이노스케에게 말을 걸어보세요"},
            {"order": 2, "speaker": "tanjiro", "content": "이노스케, 우리 힘이 필요해!"}
          ],
          "success_condition": {"keywords": ["이노스케", "함께"]}
        },
        {
          "stage": 1,
          "exchanges": [
            {"order": 0, "speaker": "user", "input_prompt": "이노스케를 설득하세요"},
            {"order": 1, "speaker": "inosuke", "content": "흥! 왜 내가 도와야 하냐!"},
            {"order": 2, "speaker": "user", "input_prompt": "계속 설득하세요"},
            {"order": 3, "speaker": "tanjiro", "content": "{{user}}, 도발해봐!"}
          ],
          "success_condition": {"keywords": ["약", "겁쟁이", "못"]}
        }
      ]
    }
  }
}
```

### 3. Children Agent 다중 발화 로직

```python
def process(self, state: AgentState) -> AgentState:
    # dialogue_context는 이제 exchanges 리스트
    exchanges = state.parent_decisions.dialogue_context

    if not exchanges:
        return state

    generated_dialogues = []

    for exchange in exchanges:
        order = exchange.get("order", 0)
        speaker = exchange.get("speaker")

        if speaker == "user":
            # 유저 입력 대기 플래그 설정
            state.game.add_flag("awaiting_user_input")
            state.parent_decisions.user_input_prompt = exchange.get("input_prompt", "입력하세요")
            break  # 유저 입력 대기

        elif speaker == "system":
            # 시스템 나레이션
            state.output.add_system_message(exchange.get("content", ""))

        else:
            # 캐릭터 대사 생성
            dialogue = self._generate_dialogue(speaker, exchange, state)
            generated_dialogues.append(dialogue)

    state.output.dialogues = generated_dialogues
    return state
```

### 4. Parent Agent 시나리오 진행 개선

```python
def _handle_cutscene_stage(self, state: AgentState, stage_data: Dict) -> AgentState:
    current_turn = state.game.turn
    dialogues = stage_data.get("dialogues", [])

    # 현재 턴의 exchanges 찾기
    turn_dialogue = next((d for d in dialogues if d.get("turn") == current_turn), None)

    if turn_dialogue:
        exchanges = turn_dialogue.get("exchanges", [])

        # user 입력 대기 중인지 확인
        if state.game.has_flag("awaiting_user_input"):
            # 유저가 입력했으므로 다음 exchange로 진행
            current_exchange_idx = state.game.temp_data.get("current_exchange_idx", 0)
            remaining_exchanges = exchanges[current_exchange_idx + 1:]

            if remaining_exchanges:
                # 다음 exchange 처리
                state.parent_decisions.dialogue_context = remaining_exchanges
                state.game.temp_data["current_exchange_idx"] = current_exchange_idx + 1
            else:
                # 턴 완료, 다음 턴으로
                state.game.remove_flag("awaiting_user_input")
                state.game.temp_data.pop("current_exchange_idx", None)
                state.game.increment_turn()
        else:
            # 첫 진입: 전체 exchanges 설정
            state.parent_decisions.dialogue_context = exchanges
            state.game.temp_data["current_exchange_idx"] = 0

    return state
```

### 5. Dialogue Agent 출력 처리

```python
def process(self, state: AgentState) -> AgentState:
    # 다중 대사 정렬 (order 기준)
    state.output.dialogues.sort(key=lambda d: d.order)

    # 순차 출력
    for dialogue in state.output.dialogues:
        print(f"[{dialogue.speaker}]: {dialogue.content}")

    # 유저 입력 대기 확인
    if state.game.has_flag("awaiting_user_input"):
        prompt = state.parent_decisions.user_input_prompt or "입력하세요"
        print(f"\n[시스템]: {prompt}")
        state.next_node = "wait_user_input"
    else:
        # 모든 대사 출력 완료, 다음 턴으로
        state.next_node = "router"  # Parent로 돌아가서 다음 exchanges 처리

    return state
```

## 구현 순서

1. **Phase 1**: JSON 구조 개선
   - cutscene5 시나리오에 exchanges 구조 적용
   - order, speaker, input_prompt 필드 추가

2. **Phase 2**: Parent Agent 수정
   - exchanges 기반 dialogue_context 설정
   - awaiting_user_input 플래그 관리
   - current_exchange_idx 추적

3. **Phase 3**: Children Agent 수정
   - exchanges 순회 로직
   - user speaker 처리 (입력 대기)
   - 다중 대사 생성

4. **Phase 4**: Dialogue Agent 수정
   - order 기반 정렬
   - 유저 입력 프롬프트 표시
   - 다음 노드 결정 (wait_user_input vs router)

5. **Phase 5**: 통합 테스트
   - cutscene5 intro 3회 대화 테스트
   - mission 단계 설득 대화 테스트
   - choice 단계 선택 전 대화 테스트
