# KIME Chat Agent 시스템 분석 및 개선 권장사항

## 요청 사항 분석

### 사용자 요구사항
1. **시나리오 기획대로 정확히 진행**
   - 컷신 5-6의 복잡한 분기와 턴제 시스템
   - 이노스케 → 젠이츠 순서 강제
   - 3가지 엔딩 (히든/중간/기본)

2. **다중 캐릭터 대화**
   - 1대1이 아닌 다중 대화
   - 탄지로 → 유저 → 이노스케 → 젠이츠 형태
   - 각 분기에서 최소 3회 대화

3. **캐릭터 주도 대화 시작**
   - 유저가 먼저 입력하지 않음
   - 캐릭터가 먼저 상황 설명/질문
   - 유저가 어떻게 답할지 호응 가능

## 현재 시스템 문제점

### 1. 구조적 문제
**LangGraph 워크플로우**
```
Router → Parent → Children → Dialogue → (다시 Router)
```

**문제:**
- 각 노드가 독립적으로 실행
- 한 턴에 여러 캐릭터 발화 불가
- 유저 입력 대기 시점 제어 어려움

### 2. State 관리 문제
**GraphState 구조:**
```python
{
  "agent_responses": [{"speaker": "tanjiro", "text": "..."}],  # 단일 응답만 가능
  "turn_count": 5,  # 턴 증가 타이밍 불명확
  "available_characters": ["tanjiro"],  # 다중 캐릭터 처리 안 됨
}
```

**문제:**
- `agent_responses`가 턴당 1개만 저장
- 다중 발화를 위한 구조 없음

### 3. 시나리오 JSON 문제
**현재 cutscene5_akaza_encounter.json:**
- 너무 복잡 (620 lines)
- 코드와 구조 불일치
- conversation_stages가 제대로 작동 안 함

## 해결 방안 비교

### 방안 A: 전면 재설계 (추정 5-7일)
**변경 사항:**
1. LangGraph 워크플로우 재설계
   - Multi-turn Conversation Node 신규 추가
   - Router → Parent → MultiConversation → Dialogue

2. GraphState 확장
   ```python
   {
     "current_exchanges": [  # 현재 진행 중인 대화 리스트
       {"order": 0, "speaker": "system", "content": "..."},
       {"order": 1, "speaker": "tanjiro", "content": "..."},
       {"order": 2, "speaker": "user", "awaiting_input": True}
     ],
     "exchange_index": 0,  # 현재 진행 위치
     "exchanges_completed": False
   }
   ```

3. 시나리오 JSON 재설계
   - exchanges 구조 도입
   - user 입력 포인트 명시

**장점:**
- ✅ 완전한 다중 대화 지원
- ✅ 시나리오 흐름 완벽 재현
- ✅ 확장성 우수

**단점:**
- ❌ 대규모 코드 수정 (15+ 파일)
- ❌ 기존 기능 호환성 깨짐
- ❌ 디버깅 시간 많이 소요 (2-3일)

---

### 방안 B: 최소 수정 (추정 4-6시간) ⭐ **추천**
**변경 사항:**
1. Parent Agent 개선
   - `dialogue_context`를 list로 확장
   - 여러 캐릭터 대사를 순차 전달

2. Children Agent 개선
   - list 순회하며 대사 생성
   - system speaker는 narration 처리

3. play.py 개선
   - `agent_responses` 전체 출력
   - 턴 내 다중 응답 표시

4. JSON 단순화
   - exchanges 제거
   - 간단한 list 구조 사용

**구현 예시:**
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

**장점:**
- ✅ 빠른 구현 (4-6시간)
- ✅ 기존 시스템 안정성 유지
- ✅ 요구사항 80% 만족

**단점:**
- ⚠️ 완전한 다중 대화 아님 (순차 출력)
- ⚠️ 유저 입력 중간 대기 어려움 (턴 종료 시에만)

---

### 방안 C: 하이브리드 (추정 2-3일)
**변경 사항:**
1. Sub-turn 시스템 도입
   - 1 turn = 여러 sub-turns
   - sub-turn마다 캐릭터 1명 발화 가능

2. GraphState에 sub_turn 추가
   ```python
   {
     "turn": 5,
     "sub_turn": 2,  # 턴 내 대화 순서
     "sub_turn_max": 4  # 이 턴의 총 대화 수
   }
   ```

3. Parent Agent: sub_turn 관리
4. Dialogue Agent: sub_turn 완료 체크

**장점:**
- ✅ 진정한 다중 대화 가능
- ✅ 기존 구조 대부분 유지
- ✅ 유저 입력 중간 대기 가능

**단점:**
- ⚠️ 중간 복잡도 (새 개념 도입)
- ⚠️ 2-3일 소요

---

## 권장사항

### 즉시 구현 가능: 방안 B (4-6시간)
**이유:**
1. 최소 위험도
2. 빠른 프로토타입
3. 요구사항 80% 만족

**구현 순서:**
1. `cutscene5_simple.json` 작성 (1시간)
2. `parent_agent.py` 수정 (1.5시간)
3. `children_agent.py` 수정 (1시간)
4. `play.py` 수정 (1시간)
5. 테스트 및 디버깅 (1.5시간)

**결과:**
- ✅ 캐릭터가 먼저 대화 시작
- ✅ 턴당 2-3개 캐릭터 대사 표시
- ⚠️ 유저 입력은 턴 종료 시에만 (완전한 다중 대화는 아님)

### 장기 목표: 방안 A 또는 C
**타임라인:**
- Week 1: 방안 B 구현 및 테스트
- Week 2-3: 방안 C 또는 A로 점진적 업그레이드

---

## 방안 B 구현 가이드

### Step 1: JSON 작성
파일: `data/scenarios/cutscene5_simple.json`

```json
{
  "scenario_id": "cutscene5_simple",
  "title": "컷신5: 상현 삼의 등장",
  "stages": {
    "intro": {
      "type": "cutscene",
      "dialogues": [
        {
          "turn": 0,
          "speakers": ["system", "tanjiro"],
          "contents": [
            "열차의 충격으로 당신이 눈을 뜬다.",
            "{{user}}!! 괜찮아?!"
          ],
          "emotions": ["neutral", "worried"],
          "user_prompt": "탄지로에게 대답하세요"
        },
        {
          "turn": 1,
          "speakers": ["tanjiro", "rengoku", "tanjiro"],
          "contents": [
            "다행이다... 엔무는 쓰러뜨렸지만, 렌고쿠 씨가 보이지 않아!",
            "음! 여깄다! 대단하다!",
            "렌고쿠 씨... 복부 출혈이 심해서..."
          ],
          "emotions": ["anxious", "proud", "pain"],
          "user_prompt": "대답하세요"
        }
      ],
      "next_stage": "fork"
    },
    "fork": {
      "type": "choice",
      "pre_choice_speakers": ["system", "tanjiro", "tanjiro"],
      "pre_choice_contents": [
        "아카자가 술식을 전개한다!",
        "{{user}}! 렌고쿠 씨가 위험해!",
        "우리에게는 3가지 방법이 있어..."
      ],
      "choices": [
        {
          "id": "recruit",
          "text": "1. 동료들을 찾아 함께 싸운다",
          "intent_keywords": ["동료", "함께", "찾"],
          "next_stage": "recruit_mission"
        },
        {
          "id": "direct",
          "text": "2. 탄지로와 둘이서 바로 돕는다",
          "intent_keywords": ["탄지로", "둘", "바로"],
          "next_stage": "end_medium"
        }
      ]
    }
  }
}
```

### Step 2: Parent Agent 수정
파일: `src/agents/parent_agent.py`

```python
def _handle_cutscene_stage(self, state, stage_data):
    current_turn = state.game.turn
    dialogues = stage_data.get("dialogues", [])

    turn_dialogue = next((d for d in dialogues if d.get("turn") == current_turn), None)

    if not turn_dialogue:
        # 턴 완료, 다음 스테이지로
        next_stage = stage_data.get("next_stage")
        if next_stage:
            state.game.current_stage = next_stage
        return state

    # 여러 캐릭터 대사를 list로 전달
    speakers = turn_dialogue.get("speakers", [])
    contents = turn_dialogue.get("contents", [])
    emotions = turn_dialogue.get("emotions", [])
    user_prompt = turn_dialogue.get("user_prompt", "입력하세요")

    dialogue_list = []
    for i, speaker in enumerate(speakers):
        dialogue_list.append({
            "speaker": speaker,
            "situation": contents[i] if i < len(contents) else "",
            "emotion": emotions[i] if i < len(emotions) else "neutral"
        })

    state.parent_decisions.dialogue_context = dialogue_list
    state.parent_decisions.user_input_prompt = user_prompt
    state.characters.available_characters = [s for s in speakers if s != "system"]

    return state
```

### Step 3: Children Agent 수정
파일: `src/agents/children_agent.py`

```python
def process(self, state):
    dialogue_context = state.parent_decisions.dialogue_context

    # list가 아니면 기존 방식
    if not isinstance(dialogue_context, list):
        # ...기존 로직
        return state

    # list면 순회하며 대사 생성
    generated_dialogues = []

    for ctx in dialogue_context:
        speaker = ctx.get("speaker")

        if speaker == "system":
            state.output.add_system_message(ctx.get("situation", ""))
        else:
            dialogue = self._generate_dialogue(speaker, ctx, state)
            generated_dialogues.append(dialogue)

    state.output.dialogues = generated_dialogues
    return state
```

### Step 4: play.py 수정
파일: `play.py`

```python
# 최종 결과 출력
if final_state and final_state.get("agent_responses"):
    print("\n" + "="*50)

    # 모든 응답 출력
    for response in final_state["agent_responses"]:
        speaker = response.get("speaker", "시스템")
        text = response.get("text", "")
        print(f"\n[{speaker}]: {text}")

    print("\n" + "="*50)

    # 유저 입력 프롬프트
    user_prompt = final_state.get("user_input_prompt", "입력하세요")
    print(f"\n💡 {user_prompt}")
```

---

## 예상 결과

### 실행 예시 (방안 B 적용 후)
```
==========================================
턴 1
==========================================

[시스템]: 열차의 충격으로 당신이 눈을 뜬다.

[탄지로]: {{user}}!! 괜찮아?!

==========================================

💡 탄지로에게 대답하세요

[당신]: 괜찮아, 무슨 일이야?

==========================================
턴 2
==========================================

[탄지로]: 다행이다... 엔무는 쓰러뜨렸지만, 렌고쿠 씨가 보이지 않아!

[렌고쿠]: 음! 여깄다! 대단하다!

[탄지로]: 렌고쿠 씨... 복부 출혈이 심해서...

==========================================

💡 대답하세요

[당신]: ...
```

### 특징
- ✅ 캐릭터가 먼저 대화 시작
- ✅ 한 턴에 2-3명 캐릭터 발화
- ✅ 명확한 입력 프롬프트
- ⚠️ 유저 입력은 턴 종료 시에만 (턴 중간 대기 불가)

---

## 다음 단계

1. **방안 B 구현** (4-6시간)
   - 즉시 프로토타입 완성

2. **테스트 및 피드백**
   - cutscene5 intro, fork, recruit 테스트
   - 사용자 경험 평가

3. **선택:**
   - **만족하면**: 나머지 시나리오 확장
   - **불만족하면**: 방안 C 또는 A로 업그레이드

---

## 결론

**방안 B를 먼저 구현하여 빠르게 프로토타입을 만들고, 사용자 피드백을 받은 후 추가 개선을 결정하는 것이 가장 실용적입니다.**

**시작 명령:**
```bash
# 1. JSON 작성
cat > data/scenarios/cutscene5_simple.json << 'EOF'
...
EOF

# 2. Parent 수정
vim src/agents/parent_agent.py

# 3. Children 수정
vim src/agents/children_agent.py

# 4. play.py 수정
vim play.py

# 5. 테스트
python play.py
```
