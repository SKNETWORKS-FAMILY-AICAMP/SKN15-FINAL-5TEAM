# 무한열차 완전판: 렌고쿠 제자 시점 서사

## 📋 개요

기존 '상현 삼 조우' 시나리오를 **렌고쿠의 제자({user}) 시점**으로 확장하여, 무한열차 탑승부터 엔무전, 아카자전, 엔딩까지 완전한 서사를 구현했습니다.

---

## 🎯 핵심 변경사항

### 1. **세계관 설정 재구성**
- **기존**: {user}가 탄지로 일행과 함께 탑승
- **변경**: {user}는 렌고쿠의 제자(츠구코)로, 스승과 함께 먼저 탑승하여 조사 중

### 2. **전반부 스테이지 완전 재작성**
- **TRAIN_PRELUDE**: 렌고쿠와 제자의 열차 탑승 (open_narrative, 3턴)
- **HEROES_ARRIVE**: 탄지로 일행 합류 (scene, llm_beats)
- **RENGOKU_TRAIN_DIALOGUE**: 히노카미와 제자 관계 (scene, beats_i18n)
- **ENMU_APPEAR**: 악몽의 시작 (scene, beats_i18n)
- **ENMU_DREAM_WAR**: 꿈속 전투 (scene, llm_beats)
- **ENMU_REAL_BATTLE**: 열차 융합전 (scene, llm_beats)

### 3. **기존 구조 완전 유지**
- **상현_삼_등장** 이후는 변경 없이 그대로 유지
- Router, Mission, Ending 판정 로직 유지

---

## 🎭 완전한 Stage Flow

```
[프롤로그: 렌고쿠와 제자]
TRAIN_PRELUDE (open_narrative, 3턴)
    ↓
[탄지로 일행 합류]
HEROES_ARRIVE (scene, llm_beats)
    ↓
[제자 소개 & 히노카미 대화]
RENGOKU_TRAIN_DIALOGUE (scene, beats_i18n)
    ↓
[엔무 등장]
ENMU_APPEAR (scene, beats_i18n)
    ↓
[꿈속 전투]
ENMU_DREAM_WAR (scene, llm_beats)
    ↓
[열차 융합 전투]
ENMU_REAL_BATTLE (scene, llm_beats)
    ↓
[열차 탈선 → 아카자 등장]
상현_삼_등장 (scene, beats_i18n)
    ↓
ROUTE_CHOICE (free_intent)
    ↓ (분기)
    ├─ RECRUIT (mission) → RETURN_TO_FRONT
    └─ INTERVENE → RECKLESS_SACRIFICE
    ↓
END_ROUTER (router)
    ↓ (판정)
    ├─ END_HIDDEN (히든 엔딩)
    ├─ END_BASIC (기본 엔딩)
    └─ END_BAD (배드 엔딩)
```

---

## 📊 신규 콘텐츠

### 1. **신규 캐릭터**
- **[enmu.json](data/characters/enmu.json)**: 하현의 일, 악몽의 혈귀

### 2. **신규 i18n Beats**

#### `beats_rengoku_dialogue`
```json
[
  "탄지로가 히노카미 카구라에 대해 묻는다",
  "렌고쿠가 불의 호흡과의 관계를 설명한다",
  "렌고쿠가 {user}를 제자로 소개한다",
  "탄지로가 {user}에게 감탄하며 인사한다",
  "렌고쿠가 함께 수련하자고 제안한다"
]
```

#### `beats_enmu_appear`
```json
[
  "차장이 떠나고 이상한 정적이 흐른다",
  "승객들이 잠들기 시작한다",
  "젠이츠와 이노스케가 쓰러진다",
  "탄지로가 네즈코를 보호하려 하지만 의식이 흐려진다",
  "렌고쿠가 혈귀술임을 직감한다",
  "엔무의 목소리가 들려온다",
  "모두가 잠에 빠진다"
]
```

### 3. **LLM Beats 활용 스테이지**
- **HEROES_ARRIVE**: 탄지로 일행 등장을 LLM이 즉흥 연출
- **ENMU_DREAM_WAR**: 각자의 꿈속 전투를 동적 생성
- **ENMU_REAL_BATTLE**: 열차 융합 전투를 실시간 생성

---

## 🔄 서사 흐름

### Act 1: 프롤로그 (TRAIN_PRELUDE)
**렌고쿠와 제자의 조사 시작**
- Open Narrative (3턴)
- 렌고쿠와 {user}가 먼저 무한열차에 탑승
- 승객들의 불안한 표정, 이상한 기운
- 유저 자유 입력으로 조사 진행

### Act 2: 탄지로 일행 합류 (HEROES_ARRIVE → RENGOKU_TRAIN_DIALOGUE)
**새로운 동료들과의 만남**
- 탄지로, 젠이츠, 이노스케, 네즈코 등장
- 렌고쿠가 {user}를 제자로 소개
- 히노카미 카구라와 불의 호흡 대화
- 제자로서의 정체성 확립

### Act 3: 엔무전 (ENMU_APPEAR → ENMU_DREAM_WAR → ENMU_REAL_BATTLE)
**하현의 일과의 전투**
- 차장의 검표 후 기묘한 졸음
- 엔무의 혈귀술로 모두 잠듦
- 꿈속에서의 환영과 싸움
- 열차 융합 후 본격 전투
- 렌고쿠가 승객 보호, {user}와 탄지로가 엔무 격퇴

### Act 4: 아카자전 (상현_삼_등장 ~ END_ROUTER)
**기존 구조 그대로 유지**
- 열차 탈선 후 아카자 등장
- Router 분기 (동료 규합 vs 무모한 돌입)
- Mission 또는 희생 루트
- 엔딩 판정 (히든/기본/배드)

---

## 🎯 주요 특징

### 1. **제자 정체성 강화**
- 렌고쿠와의 사제 관계가 서사 전반에 걸쳐 강조
- 제자 소개 장면 (RENGOKU_TRAIN_DIALOGUE)
- 히든 엔딩에서 "불의 계승자" 인정

### 2. **자연스러운 전개**
- 프롤로그 생략 없이 열차 탑승부터 시작
- 탄지로 일행과의 자연스러운 합류
- 엔무전 → 아카자전 연결이 매끄러움

### 3. **LLM 활용 극대화**
- Open Narrative: 유저 자유 입력 기반 즉흥 서사
- LLM Beats: 상황에 맞는 동적 beats 생성
- 기존 Beats: 핵심 장면은 고정 beats 유지

### 4. **기존 시스템 완전 호환**
- 모든 Handler (Open Narrative, Scene, Mission, Router) 정상 작동
- Affinity, Intent, Guardrail 시스템 유지
- 엔딩 판정 로직 그대로 사용

---

## 📁 파일 변경 사항

### 신규 파일 (1개)
- **[enmu.json](data/characters/enmu.json)**: 엔무 캐릭터 데이터

### 수정된 파일 (1개)
- **[cutscene5_llm_driven.json](data/scenarios/cutscene5_llm_driven.json)**:
  - character_refs에 `enmu` 추가
  - i18n에 `beats_rengoku_dialogue`, `beats_enmu_appear` 추가
  - stages 전반부 6개 완전 재작성
  - default_stage를 `TRAIN_PRELUDE`로 변경

---

## ✅ 검증 완료

```bash
✅ JSON is valid
Total stages: 16
Default stage: TRAIN_PRELUDE

📊 Stage Flow:
1. TRAIN_PRELUDE (open_narrative) → HEROES_ARRIVE
2. HEROES_ARRIVE (scene) → RENGOKU_TRAIN_DIALOGUE
3. RENGOKU_TRAIN_DIALOGUE (scene) → ENMU_APPEAR
4. ENMU_APPEAR (scene) → ENMU_DREAM_WAR
5. ENMU_DREAM_WAR (scene) → ENMU_REAL_BATTLE
6. ENMU_REAL_BATTLE (scene) → 상현_삼_등장
7. 상현_삼_등장 (scene) → ROUTE_CHOICE
```

---

## 🎮 플레이 흐름

### 1. **시작 (TRAIN_PRELUDE)**
- 렌고쿠: "오늘은 특별한 임무다. 무한열차에서 사람들이 실종되고 있어."
- {user}: 자유롭게 대답 (예: "준비되었습니다", "조심해야겠네요")
- 3턴 동안 자유 대화 후 자동 전환

### 2. **탄지로 일행 합류 (HEROES_ARRIVE)**
- LLM이 탄지로 일행의 등장 장면을 즉흥 생성
- 젠이츠와 이노스케의 소란스러운 등장
- 렌고쿠의 호탕한 웃음

### 3. **제자 소개 (RENGOKU_TRAIN_DIALOGUE)**
- 고정 beats로 핵심 대화 진행
- 렌고쿠: "이 아이는 내 제자이자, 불의 뜻을 잇는 자다."
- 탄지로의 감탄과 인사

### 4. **엔무전 (ENMU_APPEAR ~ ENMU_REAL_BATTLE)**
- 차장의 검표 → 모두 잠듦
- 꿈속 전투 (LLM 즉흥)
- 열차 융합 전투 (LLM 즉흥)
- 탄지로가 엔무의 목을 찾아 승리

### 5. **아카자전 (기존 구조)**
- 열차 탈선 → 아카자 등장
- 동료 규합 or 무모한 돌입 선택
- 엔딩 판정

---

## 💡 개발자 노트

### 설계 의도
1. **{user}의 정체성 명확화**: 렌고쿠의 제자라는 설정을 서사 전반에 통합
2. **프롤로그 필요성**: 탄지로 일행과의 자연스러운 합류 과정 구현
3. **엔무전 추가**: 원작 무한열차편의 완결성 확보
4. **기존 구조 유지**: 검증된 아카자전 시스템 그대로 활용

### 기술적 도전
- Open Narrative와 기존 Beats의 조화
- LLM Beats를 통한 동적 서사 생성
- 16개 스테이지의 매끄러운 연결

---

## 🚀 실행 방법

```python
# 시나리오 시작
state = {
    "scenario_id": "cutscene5_llm_driven",
    "user_input": "시작"
}

# TRAIN_PRELUDE에서 시작
# 렌고쿠와 함께 열차 탑승
# 3턴 자유 대화 후 탄지로 일행 합류
# 엔무전 → 아카자전 → 엔딩
```

---

## 📊 완성도

- ✅ 프롤로그 (렌고쿠-제자 탑승)
- ✅ 탄지로 일행 합류
- ✅ 제자 소개 & 히노카미 대화
- ✅ 엔무전 (악몽 → 열차 융합)
- ✅ 아카자전 (기존 구조)
- ✅ 3종 엔딩 (히든/기본/배드)

---

## 🎬 최종 결과

**"렌고쿠와 제자의 조사 → 탄지로 일행 합류 → 제자 소개 → 엔무전 → 아카자전 → 엔딩"**

완전한 무한열차 서사가 렌고쿠의 제자 시점으로 구현되어, 원작의 감동과 몰입감을 최대한 재현하면서도 {user}의 정체성을 명확히 확립했습니다.
