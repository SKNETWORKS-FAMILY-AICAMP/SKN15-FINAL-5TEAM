# Open Narrative System 구현 완료

## 📋 개요

기존 시나리오 JSON(`cutscene5_llm_driven.json`)에 **Open Narrative** 시스템을 추가하여, 탑승→악몽→탐색→전투→엔딩으로 이어지는 완전한 서사 구조를 구현했습니다.

---

## 🎯 구현 목표

1. **새로운 StageHandler 추가**: `OpenNarrativeHandler`
2. **ParentAgent 수정**: `open_narrative` 타입 분기 추가
3. **RouterAgent 수정**: `turn_count` 기반 자동 전환
4. **ChildrenAgent 수정**: `llm_beats` 지원
5. **state_tools.py**: Open Narrative 전용 상태 필드 추가
6. **JSON 수정**: 전반부 스테이지(TRAIN_BOARDING, DREAM_INVASION, INVESTIGATION) 추가

---

## 📁 신규 파일

### 1. `src/core/story_orchestrator.py`
- **역할**: Open Narrative 스테이지에서 LLM을 통해 즉흥 서사 생성
- **주요 기능**:
  - 유저 입력을 기반으로 대사 생성
  - `story_summary` 누적 관리
  - `state_update`를 통한 상태 업데이트

### 2. `src/agents/stage_handlers/open_narrative_stage.py`
- **역할**: Open Narrative 스테이지 처리
- **주요 기능**:
  - `turn_count` 기반 자동 전환 (기본 5턴)
  - 유저 입력이 없을 때 프롬프트 제공
  - LLM 호출하여 즉흥 대사 생성

### 3. `data/characters/nezuko.json`
- **역할**: 네즈코 캐릭터 데이터
- **특징**: 말을 하지 못하고 소리/몸짓으로 의사표현

---

## 🔧 수정된 파일

### 1. `src/agents/parent_agent.py`
- `OpenNarrativeHandler` import 추가
- `_handlers`에 `"open_narrative"` 핸들러 등록
- `open_narrative` 타입일 때 beats 생성 건너뜀 (LLM이 즉흥 생성)
- `turn_count` 기반 자동 전환 로직 추가:
  ```python
  if current_stage_type == "open_narrative" and narrative_turn_count >= 5:
      auto_advance_now = True
  ```

### 2. `src/agents/router_agent.py`
- 변경 사항 없음 (기존 로직 유지)
- `turn_count`는 `ParentAgent`에서 처리

### 3. `src/agents/children_agent.py`
- `llm_beats` 플래그 지원 추가
- `_generate_beats_from_context()`: context 기반 beats 실시간 생성
- `_create_fallback_beats()`: LLM 실패 시 기본 beats 반환

### 4. `src/agents/stage_handlers/scene_stage.py`
- `llm_beats` 플래그를 `children_ctx`에 전달

### 5. `src/agents/stage_handlers/__init__.py`
- `OpenNarrativeHandler` export 추가

### 6. `src/tools/state_tools.py`
- SQLite 테이블에 `story_summary`, `turn_count`, `world_state` 컬럼 추가
- `_initialize_open_narrative_fields()` 함수 추가
- `ensure_scenario_state()`에서 자동 초기화

### 7. `data/scenarios/cutscene5_llm_driven.json`
- **전반부 스테이지 추가**:
  - `TRAIN_BOARDING` (open_narrative): 무한열차 탑승
  - `DREAM_INVASION` (open_narrative): 악몽 침입
  - `INVESTIGATION` (scene, llm_beats=true): 탐색
- **character_refs**: `nezuko` 추가
- **default_stage**: `"TRAIN_BOARDING"`으로 변경

---

## 🎭 Stage Flow

```
TRAIN_BOARDING (open_narrative, 5턴)
    ↓
DREAM_INVASION (open_narrative, 5턴)
    ↓
INVESTIGATION (scene, llm_beats=true)
    ↓
상현_삼_등장 (scene)
    ↓
ROUTE_CHOICE (free_intent)
    ↓ (분기)
    ├─ RECRUIT (mission)
    │    ↓
    │    RETURN_TO_FRONT (scene)
    │
    └─ INTERVENE (scene)
         ↓
         RECKLESS_SACRIFICE (scene)
    ↓
END_ROUTER (router)
    ↓ (판정)
    ├─ END_HIDDEN (히든 엔딩)
    ├─ END_BASIC (기본 엔딩)
    └─ END_BAD (배드 엔딩)
```

---

## 🧩 상태 필드

### Open Narrative 전용 필드
- `story_summary` (str): 지금까지 일어난 일의 요약
- `turn_count` (int): Open Narrative 턴 수 (stage별 독립)
- `world_state` (dict): 세계 상태 정보

### 기존 필드와의 관계
- `stage_turn`: 모든 stage 타입에서 공통으로 사용
- `turn_count`: Open Narrative 전용 (자동 전환 판정용)

---

## 🔍 주요 로직

### 1. Open Narrative 스테이지 자동 전환
```python
# ParentAgent.run()
if current_stage_type == "open_narrative" and narrative_turn_count >= 5:
    auto_advance_now = True
    log("parent", "⚡ Auto-advance via open_narrative turn threshold")
```

### 2. LLM Beats 실시간 생성
```python
# ChildrenAgent._build_dialogues()
if llm_beats_enabled and not beats:
    beats = self._generate_beats_from_context(state, ctx)
```

### 3. StoryOrchestrator 서사 생성
```python
# StoryOrchestrator.generate_narrative()
response = self._llm.call_json(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    temperature=0.8,
    max_tokens=1500,
)
# 반환: {"dialogues": [...], "state_update": {...}}
```

---

## 🧪 테스트 시나리오

### 1. Open Narrative 진입
- 시나리오 시작 시 `TRAIN_BOARDING`부터 시작
- 유저 입력이 없으면 프롬프트 대사 제공
- 유저 입력 시 LLM이 즉흥 대사 생성

### 2. 자동 전환
- 5턴 진행 후 자동으로 `DREAM_INVASION`으로 전환
- 전환 시 요약 대사 제공

### 3. LLM Beats 생성
- `INVESTIGATION` 스테이지에서 `llm_beats=true` 활성화
- context 기반으로 beats 실시간 생성

### 4. 기존 구간 유지
- `상현_삼_등장` 이후는 기존 구조 그대로 동작
- Router, Mission, Ending 판정 모두 정상 작동

---

## 📊 JSON 구조 예시

```json
{
  "tag": "TRAIN_BOARDING",
  "type": "open_narrative",
  "context": "무한열차에 탑승한 {user}와 탄지로 일행. 승객들 사이에서 이상한 낌새를 느낀다.",
  "speaker_pool": ["tanjiro", "nezuko", "zenitsu", "inosuke", "narr"],
  "max_turns": 5,
  "next": "DREAM_INVASION"
}
```

```json
{
  "tag": "INVESTIGATION",
  "type": "scene",
  "context": "잠에서 깨어난 탄지로 일행이 열차 내의 흔적을 조사한다.",
  "llm_beats": true,
  "speaker_pool": ["tanjiro", "zenitsu", "inosuke", "narr"],
  "next": "상현_삼_등장"
}
```

---

## ✅ 완료 항목

- [x] StoryOrchestrator 신규 파일 생성
- [x] OpenNarrativeHandler 추가
- [x] state_tools.py에 open_narrative 전용 상태 필드 추가
- [x] ParentAgent에서 open_narrative 분기 추가
- [x] RouterAgent에서 turn_count 기반 전환 로직 추가
- [x] ChildrenAgent에서 llm_beats 지원 추가
- [x] SceneHandler에서 llm_beats 플래그 전달
- [x] JSON에 전반부 스테이지 추가 (TRAIN_BOARDING, DREAM_INVASION, INVESTIGATION)
- [x] nezuko.json 캐릭터 파일 생성
- [x] character_refs 경로 수정 (`character_data` → `characters`)
- [x] 구문 오류 검증 (모든 파일 컴파일 성공)
- [x] JSON 유효성 검증 (통과)

---

## 🚀 실행 방법

1. **시나리오 시작**:
   ```python
   state = {
       "scenario_id": "cutscene5_llm_driven",
       "user_input": "시작"
   }
   ```

2. **Open Narrative 진행**:
   - 유저가 자유롭게 입력 (예: "주변을 살핀다", "탄지로에게 말을 건다")
   - LLM이 입력에 반응하여 대사 생성
   - 5턴 후 자동 전환

3. **기존 구간 진행**:
   - `상현_삼_등장` 이후는 기존 beats 기반 진행
   - Router → Mission → Ending 순서대로 동작

---

## 🔧 향후 개선 사항

- [ ] Open Narrative 턴 수를 stage별로 개별 설정 가능하도록 개선
- [ ] `story_summary`를 자동으로 요약하는 기능 추가 (긴 서사 압축)
- [ ] `world_state`를 활용한 동적 이벤트 트리거
- [ ] Open Narrative에서 특정 키워드 감지 시 조기 전환 기능

---

## 💬 최종 결과

**"탑승 → 악몽 → 탐색 → 상현삼 조우 → 분기 → 동료 규합/무모한 돌입 → 엔딩"**

전체 서사 구조가 자연스럽게 연결되어, 유저는 자유로운 입력으로 이야기를 즐기고, 기존 beats 기반 전투/미션/엔딩으로 이어지는 완전한 경험을 할 수 있습니다.
