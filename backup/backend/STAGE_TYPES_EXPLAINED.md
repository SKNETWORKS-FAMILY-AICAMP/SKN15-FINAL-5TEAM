# Stage Types 완벽 가이드

## 🎯 질문: `"type": "open_narrative"` vs `"llm_beats": true` 차이점?

---

## 📚 세 가지 Stage 방식

### 1️⃣ **Open Narrative** - 완전 자유 대화

```json
{
  "tag": "TRAIN_PRELUDE",
  "type": "open_narrative",
  "context": "렌고쿠와 {user}는 무한열차에 탑승한다...",
  "speaker_pool": ["rengoku", "narr"],
  "max_turns": 3,
  "next": "HEROES_ARRIVE"
}
```

#### 특징:
- ✅ **유저가 완전히 자유롭게 입력**
  - 예: "주변을 살핀다", "렌고쿠에게 말을 건다", "승객을 관찰한다"
- ✅ **LLM이 유저 입력에 맞춰 즉흥 대사 생성**
  - StoryOrchestrator가 context + user_input 기반으로 서사 생성
- ✅ **턴 수 제한 후 자동 전환**
  - `max_turns: 3` → 3번 대화 후 자동으로 다음 stage
- ✅ **story_summary에 자동 누적**
  - 지금까지 일어난 일을 요약하여 저장

#### 용도:
- 탐색 구간 (열차 탑승, 조사)
- 자유 대화 (NPC와의 대화)
- 선택지 없는 자유도 높은 구간

#### Handler:
- `OpenNarrativeHandler` 사용
- `StoryOrchestrator`가 LLM 호출

---

### 2️⃣ **LLM Beats** - 구조는 있지만 내용은 즉흥

```json
{
  "tag": "HEROES_ARRIVE",
  "type": "scene",
  "context": "탄지로 일행이 객차 문을 열고 들어온다...",
  "llm_beats": true,
  "speaker_pool": ["rengoku", "tanjiro", "zenitsu", "inosuke", "narr"],
  "next": "RENGOKU_TRAIN_DIALOGUE"
}
```

#### 특징:
- ✅ **고정 beats는 없지만, scene 구조는 유지**
- ✅ **LLM이 context 기반으로 beats를 실시간 생성**
  - ChildrenAgent가 `_generate_beats_from_context()` 호출
  - 3~5개의 beats를 즉흥 생성
- ✅ **유저 입력에 반응**
  - 유저가 말하면 그에 맞춰 대사 생성
- ✅ **stage_turn 기반 자동 전환**
  - 보통 3턴 이상 진행 시 다음 stage

#### 용도:
- 고정 스크립트 없이 **유연하게 진행하고 싶은 scene**
- 등장인물이 많고 **즉흥 연출이 필요한 장면**
- 유저 입력에 따라 **다르게 반응해야 하는 구간**

#### Handler:
- `SceneHandler` 사용
- `ChildrenAgent._generate_beats_from_context()` 호출

---

### 3️⃣ **Fixed Beats (i18n)** - 고정 스크립트

```json
{
  "tag": "ENMU_REAL_BATTLE",
  "type": "scene",
  "context": "엔무가 열차와 융합해 공격해온다...",
  "beats_i18n": "beats_enmu_real_battle",
  "speaker_pool": ["tanjiro", "inosuke", "rengoku", "enmu", "narr"],
  "next": "상현_삼_등장"
}
```

#### 특징:
- ✅ **미리 작성된 고정 beats 사용**
- ✅ **JSON의 i18n 섹션에 정의**
  ```json
  "beats_enmu_real_battle": [
    {"goal": "엔무의 목소리가 울려 퍼진다", "speaker_hint": ["enmu"]},
    {"goal": "탄지로가 기관실로 향한다", "speaker_hint": ["tanjiro"]},
    {"goal": "엔무의 목이 잘린다", "speaker_hint": ["enmu", "narr"]}
  ]
  ```
- ✅ **순서대로 진행**
  - Beat 1 → Beat 2 → Beat 3 → ... 완료
- ✅ **LLM은 goal을 대사로 변환만 함**
  - Beat의 내용은 변경 안 됨

#### 용도:
- **핵심 스토리 포인트** (반드시 일어나야 하는 사건)
- **보스전 결말** (엔무 죽음, 아카자 등장)
- **엔딩 장면**

#### Handler:
- `SceneHandler` 사용
- `ChildrenAgent`가 beats를 대사로 변환

---

## 🚨 문제점 & 해결

### ❌ **기존 ENMU_REAL_BATTLE의 문제**

```json
{
  "tag": "ENMU_REAL_BATTLE",
  "llm_beats": true  // ⚠️ 문제!
}
```

**문제**:
- LLM이 즉흥으로 생성하면 "엔무가 죽었다"는 보장이 없음
- Context에만 "탄지로가 목을 찾는다"라고 써있지, 실제 성공 여부는 LLM 마음대로
- 엔무가 안 죽고 다음 stage(상현_삼_등장)로 넘어갈 수 있음!

### ✅ **해결 방법**

```json
{
  "tag": "ENMU_REAL_BATTLE",
  "beats_i18n": "beats_enmu_real_battle"  // ✅ 고정 beats 사용
}
```

**해결**:
- 12개의 고정 beats 추가
- Beat 9: "엔무의 목이 잘린다"
- Beat 10: "엔무가 사라지며 마지막 말을 남긴다"
- Beat 11-12: 열차 탈선 → 아카자 등장으로 자연스럽게 연결

---

## 📊 현재 시나리오 구조

```
1. TRAIN_PRELUDE (open_narrative, 3턴)
   → 렌고쿠와 제자의 자유 대화

2. HEROES_ARRIVE (scene, llm_beats)
   → 탄지로 일행 등장 (즉흥 연출)

3. RENGOKU_TRAIN_DIALOGUE (scene, beats_i18n: 5 beats)
   → 제자 소개 & 히노카미 대화 (고정 스크립트)

4. ENMU_APPEAR (scene, beats_i18n: 7 beats)
   → 엔무 등장 & 모두 잠듦 (고정 스크립트)

5. ENMU_DREAM_WAR (scene, llm_beats)
   → 꿈속 전투 (즉흥 연출)

6. ENMU_REAL_BATTLE (scene, beats_i18n: 12 beats) ✅ 수정!
   → 열차 융합 전투 & 엔무 죽음 (고정 스크립트)

7. 상현_삼_등장 (scene, beats_i18n: 10 beats)
   → 아카자 등장 (고정 스크립트)

... 이후 기존 구조 유지
```

---

## 🎯 언제 어떤 방식을 써야 할까?

### ✅ **Open Narrative 사용 시기**
- 탐색 구간 (장소 조사, 자유 이동)
- 자유 대화 (NPC와의 대화, 선택지 없는 대화)
- 오픈 월드형 구간 (유저가 원하는 대로 행동)

### ✅ **LLM Beats 사용 시기**
- 고정 스크립트는 없지만 유연한 연출이 필요한 scene
- 등장인물이 많고 즉흥 연출이 필요한 장면
- 유저 입력에 따라 다르게 반응해야 하는 구간

### ✅ **Fixed Beats (i18n) 사용 시기**
- **핵심 스토리 포인트** (반드시 일어나야 하는 사건)
- **보스전 결말** (적 사망 확정)
- **중요한 대화** (캐릭터 관계 변화)
- **엔딩 장면**

---

## 🔍 비교표

| 항목 | Open Narrative | LLM Beats | Fixed Beats |
|------|----------------|-----------|-------------|
| **Handler** | OpenNarrativeHandler | SceneHandler + LLM | SceneHandler |
| **Beats** | 없음 | LLM 실시간 생성 | 미리 작성 |
| **자유도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **일관성** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **전환** | turn_count | stage_turn | beats 완료 |
| **용도** | 탐색, 자유 대화 | 유연한 scene | 핵심 스토리 |

---

## ✅ 결론

### 🎯 **ENMU_REAL_BATTLE 수정 완료!**

- ❌ 기존: `llm_beats: true` → 엔무가 안 죽을 수도 있음
- ✅ 수정: `beats_i18n: "beats_enmu_real_battle"` → 엔무가 **확실히** 죽음

### 📊 **12개 고정 Beats 구조:**
1. 유저 응답
2. 열차 융합
3. 탄지로가 기관실로 이동 제안
4. 렌고쿠가 승객 보호
5. 열차 지붕 위 전투
6. 이노스케가 길을 연다
7. 탄지로가 목덜미 발견
8. {user}와 탄지로가 동시 공격 ✅
9. **엔무의 목이 잘린다** ✅
10. **엔무가 사라진다** ✅
11. 열차 탈선, 렌고쿠가 보호
12. 충격음, 먼지 가라앉음 → **상현_삼_등장으로 연결**

---

## 🚀 최종 검증

```bash
✅ JSON valid
✅ beats_enmu_real_battle: 12 beats
✅ ENMU_REAL_BATTLE type: scene
✅ ENMU_REAL_BATTLE beats_i18n: beats_enmu_real_battle
✅ ENMU_REAL_BATTLE llm_beats: False

핵심 Beat 확인:
   [9] ✅ 엔무의 목이 잘린다. 비명과 함께 엔무의 육체가 무너져 내린다.
   [10] ✅ 엔무가 사라지며 마지막 말을 남긴다. '무잔 님... 죄송합니다...'

✅ 결론: 엔무가 확실히 죽습니다!
```

---

**이제 엔무전이 확실하게 완결되고, 열차 탈선 → 아카자 등장으로 자연스럽게 연결됩니다!** 🔥
