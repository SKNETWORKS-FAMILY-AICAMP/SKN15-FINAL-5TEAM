# 🎭 LLM 기반 대사 생성 시스템 통합 가이드

## ✅ 완료된 작업

### 1. 자동 변환 스크립트 ✅
- **파일:** `scripts/convert_to_situations.py`
- **기능:** 기존 JSON의 하드코딩 대사를 상황 설명으로 자동 변환
- **사용법:**
  ```bash
  python scripts/convert_to_situations.py data/scenarios/cutscene5_simple.json
  ```

### 2. Parent Agent 확장 모듈 ✅
- **파일:** `src/agents/parent_agent_situations.py`
- **기능:** situations 기반 컷신 처리 로직
- **포함 기능:**
  - `handle_situation_based_cutscene()` - situations 처리
  - `should_use_situations()` - 자동 감지
  - `process_cutscene_with_fallback()` - 하이브리드 지원

### 3. 예제 시나리오 ✅
- **파일:** `data/scenarios/cutscene5_llm_driven.json`
- **특징:** Turn 2는 완전히 보완된 예시 포함
- **상태:** 나머지 TODO는 수동 보완 필요

---

## 🔧 통합 방법

### Step 1: Parent Agent에 통합

**방법 A: 기존 코드 최소 수정**

`src/agents/parent_agent.py` 파일 수정:

```python
# 파일 상단에 import 추가 (10번 줄 근처)
from src.agents.parent_agent_situations import (
    should_use_situations,
    handle_situation_based_cutscene
)

# 563번 줄 근처 (cutscene 처리 부분)을 찾아서:
def _handle_cutscene_stage(self, state, stage_data):
    """컷신 스테이지 처리"""

    # 🔥 새로운 situations 처리 추가
    if should_use_situations(stage_data):
        print(f"[PARENT] Using situation-based processing", flush=True)
        return handle_situation_based_cutscene(state, stage_data)

    # 기존 dialogues 처리 로직 (폴백)
    print(f"[PARENT] Using legacy dialogue processing", flush=True)
    dialogues = stage_data.get("dialogues", [])
    # ... (기존 코드 유지)
```

**방법 B: 완전 통합 (권장)**

```python
from src.agents.parent_agent_situations import process_cutscene_with_fallback

def _handle_cutscene_stage(self, state, stage_data):
    """컷신 스테이지 처리 (situations 우선, dialogues 폴백)"""
    return process_cutscene_with_fallback(state, stage_data)
```

---

### Step 2: config.json에 시나리오 추가

```json
{
  "scenarios": [
    {
      "id": "cutscene5_llm_driven",
      "name": "🎭 컷신5: LLM 기반 동적 대사",
      "description": "캐릭터가 상황에 맞게 자유롭게 대사를 생성하는 버전",
      "difficulty": "보통",
      "file": "cutscene5_llm_driven.json"
    }
  ]
}
```

---

### Step 3: 테스트

```bash
cd /Users/kwondowon/Downloads/kime_chat_agent/kime_chat_agent_dev/kime_chat_agent_dev

# 1. 게임 실행
python play.py

# 2. 시나리오 선택 메뉴에서
# "🎭 컷신5: LLM 기반 동적 대사" 선택

# 3. 플레이하며 대사가 동적으로 생성되는지 확인
```

---

## 📝 시나리오 작성 가이드

### 기존 방식 (❌ 하드코딩)

```json
{
  "intro": {
    "dialogues": [
      {
        "turn": 0,
        "speakers": ["tanjiro"],
        "contents": ["괜찮아?! 정신 차려!"],
        "emotions": ["worried"]
      }
    ]
  }
}
```

### 새 방식 (✅ LLM 활용)

```json
{
  "intro": {
    "situations": [
      {
        "turn": 0,
        "scene_description": "유저가 의식을 잃었고, 탄지로가 다급하게 달려온다",
        "atmosphere": "긴장, 걱정",
        "characters": [
          {
            "id": "tanjiro",
            "order": 0,
            "role": "유저의 안전을 확인하려는 동료",
            "emotion": "worried",
            "motivation": "유저가 다쳤는지 확인하고 깨우고 싶다",
            "context": "방금 전 엔무를 쓰러뜨렸지만 유저가 열차 탈선으로 튕겨나갔다"
          }
        ],
        "user_prompt": "탄지로에게 대답하세요"
      }
    ]
  }
}
```

---

## 🎯 핵심 필드 설명

### `scene_description`
- **역할:** 전체 상황을 간결하게 설명
- **예시:** "렌고쿠가 탄지로를 격려하는 순간, 아카자가 등장했다"
- **팁:** 대사 없이 객관적 상황만 기술

### `characters[].role`
- **역할:** 이 장면에서 캐릭터가 맡은 역할
- **예시:** "부상당한 후배를 격려하는 스승", "강력한 적"
- **팁:** 캐릭터의 입장을 명확히

### `characters[].motivation`
- **역할:** 캐릭터가 왜 말하는가?
- **예시:** "탄지로가 출혈을 멈추도록 격려하고 싶다"
- **팁:** 대사의 목적을 구체적으로

### `characters[].context`
- **역할:** 캐릭터가 처한 상황
- **예시:** "엔무를 쓰러뜨렸지만 탄지로가 부상당했다"
- **팁:** 캐릭터가 알고 있는 정보, 현재 상태

---

## 🔄 하이브리드 운영

**기존 시나리오와 새 시나리오 동시 지원:**

```python
# Parent Agent가 자동으로 감지
if "situations" in stage_data:
    # LLM 기반 처리
    use_llm_generation()
elif "dialogues" in stage_data:
    # 기존 방식
    use_hardcoded_dialogues()
```

**장점:**
- 기존 시나리오 그대로 사용 가능
- 새 시나리오는 LLM 활용
- 점진적 마이그레이션

---

## 📊 비교표

| 항목 | 기존 (dialogues) | 개선 (situations) |
|------|------------------|-------------------|
| 대사 생성 | 하드코딩 | LLM 동적 생성 |
| 유연성 | 고정 대사 | 상황에 맞게 변화 |
| 다양성 | 항상 동일 | 매번 다름 |
| 작업량 | 모든 대사 작성 | 상황만 설명 |
| Parent 역할 | 대사 전달 | 상황 분석 |
| Children 역할 | 그대로 출력 | LLM 연기 |

---

## 🚀 다음 단계

### 1. 전체 시나리오 변환
```bash
# 모든 시나리오 자동 변환
for file in data/scenarios/*.json; do
    python scripts/convert_to_situations.py "$file"
done
```

### 2. TODO 항목 수동 보완
- `cutscene5_llm_driven.json` 열기
- 각 캐릭터의 role, motivation, context 작성
- `original_dialogue` 참고하여 의도 파악

### 3. 고급 기능 추가

**동적 상황 생성:**
```python
def generate_situation_from_state(state):
    """게임 상태를 바탕으로 상황 설명을 LLM으로 생성"""
    prompt = f"""
    현재 상태:
    - 플래그: {state.system_flags}
    - 친밀도: {state.affinity_scores}
    - 유저 입력: {state.user_input}

    이 상황을 한 문장으로 설명하세요.
    """
    return llm.call(prompt)
```

**실시간 분기:**
```python
def analyze_user_choice(user_input, choices):
    """유저가 어떤 선택을 하려는지 LLM으로 분석"""
    # ...
```

---

## 📚 참고 자료

- **대사_하드코딩_제거_가이드.md** - 상세한 설명
- **하드코딩_제거_가이드.md** - 설정 외부화
- `cutscene5_llm_driven.json` Turn 2 - 완전히 보완된 예시

---

## ✅ 체크리스트

통합 전 확인사항:

- [ ] `scripts/convert_to_situations.py` 실행 권한 확인
- [ ] `src/agents/parent_agent_situations.py` 임포트 가능 확인
- [ ] `cutscene5_llm_driven.json` 생성 확인
- [ ] `config.json`에 새 시나리오 추가
- [ ] Parent Agent에 통합 코드 추가
- [ ] 테스트 실행 (최소 1개 씬)
- [ ] 대사가 동적으로 생성되는지 확인
- [ ] 기존 시나리오도 여전히 작동하는지 확인

---

## 🎉 완료!

이제 Parent가 상황을 분석하고, Children이 LLM으로 연기하는 구조가 완성되었습니다!

**사용법:**
```bash
python play.py
# "🎭 컷신5: LLM 기반 동적 대사" 선택
```

**문제 발생 ���:**
1. `DEBUG=true python play.py` 실행하여 로그 확인
2. Parent Agent가 situations를 제대로 전달하는지 확인
3. Children Agent가 LLM을 사용하는지 확인 (`use_llm=True`)
