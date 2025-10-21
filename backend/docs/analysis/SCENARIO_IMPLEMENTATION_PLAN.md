# 시나리오 구현 계획서

## 현재 상황 분석

### 문제점
1. **단일 대화 구조**: 현재 시스템은 턴당 1명의 캐릭터만 발화
   - 요구사항: 탄지로 → 유저 → 이노스케 → 젠이츠 등 다중 대화

2. **시나리오 진행 오류**: Parent Agent가 JSON 시나리오를 제대로 따르지 못함
   - JSON 구조와 코드 로직이 불일치
   - 하드코딩된 진행 로직

3. **유저 주도 대화**: 캐릭터가 먼저 상황 설명 없이 유저 입력만 대기
   - 요구사항: 캐릭터가 먼저 대화를 시작하여 유저에게 힌트 제공

### 현재 구조
- **LangGraph 워크플로우**: Router → Parent → Children → Dialogue
- **단일 턴 처리**: 1 유저 입력 → 1 캐릭터 응답
- **시나리오 JSON**: cutscene5_akaza_encounter.json (복잡하지만 제대로 작동 안 함)

## 해결 방안

### 옵션 1: 전면 리팩토링 (소요 시간: 1-2일)
**장점:**
- 완전한 다중 대화 시스템 구현
- JSON 기반 시나리오 진행
- 확장성 우수

**단점:**
- 대규모 코드 수정 필요
- 기존 기능 호환성 깨질 위험
- 디버깅 시간 많이 소요

**구현 항목:**
1. GraphState에 `exchanges` 필드 추가
2. Parent Agent: exchanges 기반 dialogue_context 설정
3. Children Agent: exchanges 순회 및 user 입력 대기 처리
4. Dialogue Agent: order 기반 정렬 및 출력
5. play.py: 다중 대화 출력 루프

---

### 옵션 2: 최소 수정 (소요 시간: 2-3시간) ⭐ **추천**
**장점:**
- 빠른 구현
- 기존 시스템 안정성 유지
- 즉시 테스트 가능

**단점:**
- 완전한 다중 대화는 아님 (유사 구현)
- JSON 구조 단순화 필요

**구현 항목:**
1. **시나리오 JSON 단순화**
   - 복잡한 exchanges 구조 제거
   - dialogues에 여러 speaker 나열 (순차 출력)

2. **Parent Agent 개선**
   - cutscene: 턴당 모든 dialogues 순차 전달
   - choice: pre_choice_dialogues 처리
   - mission: conversation_stages 단계별 처리

3. **Children Agent 개선**
   - dialogue_context가 list면 순회하며 대사 생성
   - system speaker는 narration으로 처리

4. **play.py 개선**
   - agent_responses가 여러 개면 모두 출력
   - 각 응답마다 구분선 표시

---

## 옵션 2 상세 구현 (추천)

### 1단계: JSON 구조 단순화

#### 기존 (복잡)
```json
{
  "dialogues": [
    {
      "turn": 0,
      "exchanges": [
        {"order": 0, "speaker": "system", "content": "..."},
        {"order": 1, "speaker": "tanjiro", "content": "..."},
        {"order": 2, "speaker": "user", "input_prompt": "..."}
      ]
    }
  ]
}
```

#### 개선 (단순)
```json
{
  "dialogues": [
    {
      "turn": 0,
      "speakers": ["system", "tanjiro"],
      "contents": [
        "💨 열차의 충격으로...",
        "{{user}}!! 괜찮아?!"
      ],
      "emotions": ["neutral", "worried"],
      "user_prompt": "탄지로에게 대답하세요"
    }
  ]
}
```

### 2단계: Parent Agent 수정

```python
def _handle_cutscene_stage(self, state, stage_data):
    current_turn = state.game.turn
    dialogues = stage_data.get("dialogues", [])

    turn_dialogue = next((d for d in dialogues if d.get("turn") == current_turn), None)

    if turn_dialogue:
        speakers = turn_dialogue.get("speakers", [])
        contents = turn_dialogue.get("contents", [])
        emotions = turn_dialogue.get("emotions", [])
        user_prompt = turn_dialogue.get("user_prompt", "입력하세요")

        # 여러 캐릭터 대사를 list로 전달
        dialogue_list = []
        for i, speaker in enumerate(speakers):
            dialogue_list.append({
                "speaker": speaker,
                "situation": contents[i],
                "emotion": emotions[i] if i < len(emotions) else "neutral"
            })

        state.parent_decisions.dialogue_context = dialogue_list
        state.parent_decisions.user_input_prompt = user_prompt
        state.characters.available_characters = [s for s in speakers if s != "system"]

    return state
```

### 3단계: Children Agent 수정

```python
def process(self, state):
    dialogue_context = state.parent_decisions.dialogue_context

    # list가 아니면 기존 방식
    if not isinstance(dialogue_context, list):
        # 기존 로직...
        return state

    # list면 순회하며 대사 생성
    generated_dialogues = []

    for ctx in dialogue_context:
        speaker = ctx.get("speaker")

        if speaker == "system":
            # system은 narration으로
            state.output.add_system_message(ctx.get("situation", ""))
        else:
            # 캐릭터 대사 생성
            dialogue = self._generate_dialogue(speaker, ctx, state)
            generated_dialogues.append(dialogue)

    state.output.dialogues = generated_dialogues
    return state
```

### 4단계: play.py 수정

```python
# 5. 최종 결과 출력
if final_state and final_state.get("agent_responses"):
    # ✅ 모든 응답 출력 (다중 대화)
    for response in final_state["agent_responses"]:
        speaker = response.get("speaker", "나레이션")
        text = response.get("text", "")

        print(f"\n[{speaker}]: {text}")

    print("\n----------------------------------------------")

    # 유저 입력 프롬프트 표시
    user_prompt = final_state.get("user_input_prompt", "입력하세요")
    print(f"💡 {user_prompt}")
```

## 구현 순서

1. **JSON 파일 작성** (30분)
   - `data/scenarios/cutscene5_simple.json` 생성
   - intro, fork, recruit_mission 3개 스테이지만 구현

2. **Parent Agent 수정** (30분)
   - `_handle_cutscene_stage` 수정
   - `_handle_choice_stage` 수정

3. **Children Agent 수정** (30분)
   - `process` 메서드에 list 처리 로직 추가

4. **play.py 수정** (30분)
   - agent_responses 전체 출력 로직
   - user_input_prompt 표시

5. **테스트** (30분)
   - intro 3회 대화 테스트
   - fork 선택지 테스트
   - recruit_mission 설득 테스트

**총 소요 시간: 2.5시간**

## 다음 단계

### Phase 1 완료 후
- cutscene5 전체 구현
- recruit_mission에 이노스케/젠이츠 대화 추가
- ending 대화 추가

### Phase 2
- cutscene6 구현
- 친밀도 시스템 개선
- 이미지 시스템 통합

### Phase 3
- 전체 시나리오 테스트
- 버그 수정
- 문서화

## 결론

**옵션 2 (최소 수정)**를 추천합니다:
- ✅ 빠른 구현 (2-3시간)
- ✅ 기존 시스템 안정성 유지
- ✅ 요구사항 90% 만족 (최소 3회 대화 가능)
- ⚠️ 완전한 다중 대화는 아니지만, 실용적

**시작 방법:**
```bash
# 1. JSON 파일 작성
vim data/scenarios/cutscene5_simple.json

# 2. Parent Agent 수정
vim src/agents/parent_agent.py

# 3. Children Agent 수정
vim src/agents/children_agent.py

# 4. play.py 수정
vim play.py

# 5. 테스트
python play.py
```
