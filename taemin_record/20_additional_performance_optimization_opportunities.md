# 20. 추가 성능 최적화 기회 분석

**작성일**: 2025-11-02
**목적**: 기능 손실 없이 추가로 속도를 개선할 수 있는 모든 최적화 기회 파악
**전제**: 분기나 판단 같은 기본 성능(기능)은 절대 희생하지 않음

---

## 🔍 현재 상태 분석

### 이미 완료된 최적화 ([19_performance_optimization_journey.md](./19_performance_optimization_journey.md))
```
✅ max_tokens 60% 감소
✅ 프롬프트 70% 압축
✅ Entity extraction → BackgroundTasks
✅ Training logger → BackgroundTasks
```

### 현재 예상 응답 시간
```
7-12초 (이전 17-24초 대비 50-60% 개선)
```

---

## 🎯 추가 최적화 기회

### 1. Dialogue Validation 로직 분석 ⭐⭐⭐⭐

#### 현재 상황
```python
# dialogue_agent.py에서 매번 실행
def _validate_dialogue(self, dialogue):
    # LLM으로 대사 품질 검증 (2-3초)
    result = llm.invoke("대사 검증...")

    if result.score < 70:
        # LLM으로 대사 수정 (추가 2-3초)
        corrected = llm.invoke("대사 수정...")
```

**문제점**:
- 매 대사마다 validation LLM 호출 (2-3초)
- 실패 시 correction LLM 호출 (추가 2-3초)
- **총 4-6초 추가 병목** 😱

#### 최적화 옵션

**옵션 A: Validation 비활성화** (가장 빠름)
```yaml
# settings.yaml
dialogue:
  enable_validation: false  # validation 완전 스킵
```

**기대 효과**: 2-6초 즉시 단축 ⚡
**위험**: 대사 품질 하락 가능성

**옵션 B: Sampling Validation** (균형잡힌 접근)
```python
import random

def should_validate():
    # 10% 확률로만 validation 실행
    return random.random() < 0.1

if should_validate():
    validate_dialogue(...)
```

**기대 효과**: 평균 1.8-5.4초 단축 (90% 케이스)
**장점**: 품질 모니터링 가능 (10% 샘플)

**옵션 C: Rule-based Pre-filter** (추천 ⭐)
```python
def quick_validate(dialogue):
    # 빠른 rule-based 체크 (0.001초)
    text = dialogue.get("text", "")

    # 명백한 문제만 체크
    if not text or len(text) < 5:
        return False
    if "~라고 말한다" in text:  # 설명체 금지
        return False
    if text.count('"') % 2 != 0:  # 따옴표 짝 안 맞음
        return False

    return True  # LLM 호출 스킵!

# 명백한 문제만 LLM으로 수정
if not quick_validate(dialogue):
    corrected = llm.invoke("수정...")
```

**기대 효과**:
- 정상 케이스 (90%): 2-3초 단축
- 문제 케이스 (10%): 기존과 동일
- 평균: **1.8-2.7초 단축** ⚡

**추천**: **옵션 C (Rule-based Pre-filter)**
- 기능 손실 최소
- 대부분의 케이스에서 속도 개선
- 실제 문제만 LLM으로 수정

---

### 2. Intent Detection 최적화 ⭐⭐⭐

#### 현재 상황
```python
# router_agent.py에서 매번 실행
def detect_intent(user_input):
    # 1. LLM으로 intent 추출 (1-2초)
    intent = llm.invoke("의도 파악...")

    # 2. LLM으로 on_topic/off_topic 분류 (1-2초)
    classification = llm.invoke("분류...")
```

**문제점**:
- 매 요청마다 2번의 LLM 호출
- **총 2-4초** 소요

#### 최적화 옵션

**옵션 A: 1단계 Intent만 실행** (기능 유지)
```python
# topic classification을 빠른 rule로 대체
def is_on_topic(user_input, scenario_context):
    # 90% 케이스는 on_topic이므로 기본값 True

    # 명백한 off_topic만 체크
    off_topic_keywords = [
        "날씨", "뉴스", "유튜브", "검색", "알려줘",
        "설정", "시스템", "종료", "나가기"
    ]

    for keyword in off_topic_keywords:
        if keyword in user_input:
            return False  # off_topic

    return True  # on_topic (기본값)

# LLM 호출 1회만
intent = detect_intent_with_llm(user_input)
classification = is_on_topic(user_input, context)
```

**기대 효과**: 1-2초 단축 ⚡
**위험**: 거의 없음 (90%가 on_topic)

**옵션 B: 캐싱 활용**
```python
# 동일한 입력에 대해 캐싱
@lru_cache(maxsize=1000)
def classify_topic_cached(user_input_hash):
    return llm.invoke("분류...")

# 사용
classification = classify_topic_cached(hash(user_input))
```

**기대 효과**:
- 첫 요청: 기존과 동일
- 반복 요청: 0초 (캐시 히트)

**추천**: **옵션 A + B 조합**
- Rule-based로 먼저 체크
- 애매한 케이스만 LLM (캐싱 적용)

---

### 3. Image Selection 최적화 ⭐⭐

#### 현재 상황
```python
# image_manager에서 매번 실행
def select_image(dialogue_context):
    # LLM으로 이미지 선택 (1-2초)
    selected = llm.invoke("이미지 선택...")
```

**문제점**:
- 매 요청마다 LLM 호출
- 실제로 이미지가 자주 바뀌지 않음

#### 최적화 옵션

**옵션 A: Stage 기반 Default 이미지**
```python
# 시나리오에 stage별 기본 이미지 정의
STAGE_DEFAULT_IMAGES = {
    "TRAIN_ARRIVAL": "train_station_01.jpg",
    "FOREST_ENTRANCE": "forest_dark_01.jpg",
    "BOSS_FIGHT": "boss_intense_01.jpg",
}

def select_image_fast(stage_tag, dialogue_context):
    # 1. Stage default 이미지 사용 (0초)
    default_img = STAGE_DEFAULT_IMAGES.get(stage_tag)

    # 2. 특수 상황만 LLM으로 선택
    if has_special_event(dialogue_context):
        return llm.invoke("이미지 선택...")

    return default_img
```

**기대 효과**:
- 일반 케이스 (80%): 1-2초 단축
- 특수 케이스 (20%): 기존과 동일
- 평균: **0.8-1.6초 단축** ⚡

**옵션 B: 완전 비활성화** (이미지가 중요하지 않으면)
```yaml
# settings.yaml
image_manager:
  enabled: false
```

**기대 효과**: 1-2초 단축
**위험**: 시각적 경험 저하

**추천**: **옵션 A (Stage 기반 Default)**
- 시각적 경험 유지
- 속도 개선
- 중요한 순간만 LLM 사용

---

### 4. OpenAI API 캐싱 활성화 ⭐⭐⭐⭐⭐

#### 현재 상황
```python
# llm_client.py 확인 필요
def invoke(prompt, ...):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        # cache 관련 설정이 있는지 확인 필요!
    )
```

#### 최적화

**OpenAI Prompt Caching 활용**
```python
# OpenAI는 동일한 프롬프트를 자동 캐싱
# temperature=0.0인 agent는 캐싱 효과 극대화

# settings.yaml 현재 설정
agent_configs:
  router:
    temperature: 0.0  # ✅ 캐싱 가능
  mission:
    temperature: 0.0  # ✅ 캐싱 가능
  children:
    temperature: 0.8  # ❌ 캐싱 불가 (매번 다른 출력)
```

**추가 최적화**:
```python
# 시스템 프롬프트를 고정하여 캐싱 확률 높이기
def build_messages(system_prompt, user_prompt):
    return [
        {"role": "system", "content": system_prompt},  # 고정 → 캐싱
        {"role": "user", "content": user_prompt}
    ]
```

**기대 효과**:
- 캐시 히트 시: **50% 속도 향상** 🚀
- 비용: **50% 절감** 💰
- temperature=0.0인 router, mission에서 효과 큼

---

### 5. Database 쿼리 최적화 ⭐⭐⭐

#### 현재 상황 분석

**의심 포인트 1: N+1 쿼리**
```python
# dialogue 저장 시 character 정보 조회
for dialogue in dialogues:
    character = db.query("SELECT * FROM characters WHERE name = ?", dialogue.speaker)
    db.insert("INSERT INTO dialogues ...", dialogue, character.id)
    # ⬆️ 매번 쿼리 = N+1 문제!
```

**해결책: Batch Query**
```python
# 캐릭터 정보 한 번에 조회
speakers = [d.speaker for d in dialogues]
characters = db.query("SELECT * FROM characters WHERE name IN (?)", speakers)
character_map = {c.name: c for c in characters}

# 메모리에서 조회
for dialogue in dialogues:
    character = character_map.get(dialogue.speaker)
    db.insert("INSERT INTO dialogues ...", dialogue, character.id)
```

**기대 효과**: 0.5-1초 단축

**의심 포인트 2: 인덱스 누락**
```sql
-- 자주 조회되는 컬럼에 인덱스 확인
CREATE INDEX IF NOT EXISTS idx_dialogues_session_turn
  ON dialogues(session_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_training_logs_session
  ON training_logs(session_id, created_at);
```

**기대 효과**: 0.2-0.5초 단축

---

### 6. State 직렬화 최적화 ⭐⭐

#### 현재 상황
```python
# LangGraph가 agent 간 state 전달 시 직렬화/역직렬화
state = {
    "scenario": {...},  # 큰 딕셔너리
    "character_refs": {...},  # 캐릭터 JSON 전체
    "message_history": [...],  # 전체 대화 내역
    ...
}
```

**문제점**:
- 큰 state를 매번 복사/전달
- 메모리 오버헤드

#### 최적화
```python
# 필요한 것만 전달
def create_children_ctx(state):
    return {
        "beats": state["beats"],  # 필요한 것만
        "speaker_pool": state["speaker_pool"],
        "latest_user_input": state["user_input"],
        # scenario, character_refs는 agent 내부에서 참조
    }
```

**기대 효과**: 0.1-0.3초 단축 (미미하지만 누적)

---

### 7. Parallel Agent 실행 검토 ⭐

#### 현재 순차 실행
```
guardrail → router → parent → children → dialogue
   2초      3초      8초     1초       1초

총 15초
```

#### 병렬 가능성 검토
```python
# guardrail과 router는 독립적?
# → No: guardrail이 차단하면 router 불필요

# children과 image_manager는 독립적?
# → Yes: 동시 실행 가능!

async def parallel_generation():
    results = await asyncio.gather(
        children_agent.run(state),      # 대사 생성
        image_manager.select(state),    # 이미지 선택
    )
    return results
```

**기대 효과**: 1-2초 단축 (children과 image_manager 중 느린 쪽만큼만 대기)

**단점**: LangGraph 구조 수정 필요

---

## 📊 최적화 우선순위 및 기대 효과

### 높은 우선순위 (High Impact, Low Risk)

| 번호 | 최적화 | 예상 단축 | 구현 난이도 | 위험도 | 추천도 |
|------|--------|----------|------------|--------|--------|
| 1 | Dialogue Validation Rule-based | 1.8-2.7초 | 쉬움 | 낮음 | ⭐⭐⭐⭐⭐ |
| 2 | Intent Detection Rule화 | 1-2초 | 쉬움 | 낮음 | ⭐⭐⭐⭐⭐ |
| 3 | OpenAI 캐싱 활성화 | 0-7초* | 쉬움 | 없음 | ⭐⭐⭐⭐⭐ |
| 4 | Image Selection Default | 0.8-1.6초 | 중간 | 낮음 | ⭐⭐⭐⭐ |

*캐시 히트 시에만

### 중간 우선순위 (Medium Impact)

| 번호 | 최적화 | 예상 단축 | 구현 난이도 | 위험도 | 추천도 |
|------|--------|----------|------------|--------|--------|
| 5 | DB 쿼리 최적화 | 0.5-1.5초 | 중간 | 낮음 | ⭐⭐⭐ |
| 6 | State 직렬화 최적화 | 0.1-0.3초 | 어려움 | 중간 | ⭐⭐ |
| 7 | Parallel Agent 실행 | 1-2초 | 어려움 | 높음 | ⭐⭐ |

### 총 예상 개선 효과

**보수적 추정** (1+2+3+4만 적용):
```
현재: 7-12초
최적화 후: 3-6초
개선: 약 40-50% 추가 단축 🚀
```

**적극적 추정** (1~6 모두 적용):
```
현재: 7-12초
최적화 후: 2-5초
개선: 약 60-70% 추가 단축 🚀🚀
```

---

## 🎯 즉시 적용 가능한 Quick Wins

### 1단계: Rule-based Pre-filters (30분 구현)

```python
# backend/src/utils/performance_helpers.py (새 파일)

def quick_validate_dialogue(dialogue: dict) -> bool:
    """빠른 rule-based 대사 검증 (0.001초)"""
    text = dialogue.get("text", "")

    if not text or len(text) < 5:
        return False
    if "~라고 말한다" in text or "~고 말했다" in text:
        return False  # 설명체 금지
    if text.count('"') % 2 != 0:
        return False  # 따옴표 짝

    return True


def is_obviously_off_topic(user_input: str) -> bool:
    """명백한 off_topic 빠르게 판단 (0.001초)"""
    off_topic_keywords = [
        "날씨", "뉴스", "유튜브", "검색", "알려줘",
        "설정", "시스템", "종료", "나가기", "재시작"
    ]

    user_lower = user_input.lower()
    for keyword in off_topic_keywords:
        if keyword in user_lower:
            return True

    return False


def get_stage_default_image(stage_tag: str, scenario_id: str) -> str:
    """Stage별 기본 이미지 (0초)"""
    # 시나리오별 기본 이미지 매핑
    DEFAULTS = {
        "cutscene5_llm_driven": {
            "TRAIN_ARRIVAL": "bg_train_station.jpg",
            "FOREST_PATH": "bg_forest_01.jpg",
            "BOSS_ENCOUNTER": "bg_boss_arena.jpg",
        }
    }

    scenario_map = DEFAULTS.get(scenario_id, {})
    return scenario_map.get(stage_tag, "bg_default.jpg")
```

### 2단계: Agent에 적용 (1시간)

```python
# dialogue_agent.py
from src.utils.performance_helpers import quick_validate_dialogue

def validate_dialogue(self, dialogue):
    # Rule-based 빠른 체크
    if quick_validate_dialogue(dialogue):
        return dialogue  # LLM 스킵! ⚡

    # 문제 있을 때만 LLM
    return self._validate_with_llm(dialogue)
```

```python
# router_agent.py
from src.utils.performance_helpers import is_obviously_off_topic

def classify_topic(self, user_input):
    # Rule-based 빠른 체크
    if is_obviously_off_topic(user_input):
        return "off_topic"  # LLM 스킵! ⚡

    # 애매할 때만 LLM
    return self._classify_with_llm(user_input)
```

### 3단계: .env 설정 추가

```bash
# backend/.env

# 🚀 성능 최적화: Quick Pre-filters
USE_RULE_BASED_VALIDATION=true
USE_RULE_BASED_TOPIC_CLASSIFICATION=true
USE_STAGE_DEFAULT_IMAGES=true

# 🚀 OpenAI 캐싱 최적화
OPENAI_USE_CACHING=true
```

---

## 💡 구현 로드맵

### Week 1: Quick Wins (즉시 효과)
```
Day 1-2: Rule-based pre-filters 구현
  - dialogue validation
  - topic classification
  - image selection

Day 3: 테스트 및 검증
  - 성능 측정
  - 품질 확인

예상 개선: 3-5초 단축
```

### Week 2: OpenAI 캐싱 최적화
```
Day 1: llm_client.py 캐싱 로직 확인
Day 2: 시스템 프롬프트 고정화
Day 3: 캐시 히트율 모니터링

예상 개선: 캐시 히트 시 50% 단축
```

### Week 3: Database 최적화
```
Day 1: 쿼리 프로파일링
Day 2: N+1 문제 해결
Day 3: 인덱스 추가

예상 개선: 0.5-1.5초 단축
```

### Week 4: 고급 최적화 (선택)
```
Day 1-3: Parallel agent 실행 검토
Day 4-5: State 직렬화 최적화

예상 개선: 1-2초 단축
```

---

## 📈 성능 목표

### 최종 목표
```
Before (최초): 17-24초
After Phase 1-3: 7-12초 (19_performance_optimization_journey.md)
After Quick Wins: 3-6초 (이 문서)

총 개선: 약 75-85% 🎉
```

### 목표 달성 시
```
사용자 경험:
- 거의 실시간 응답 (3-6초)
- 자연스러운 대화 흐름

비용 절감:
- API 호출 감소: 약 70%
- 토큰 사용량: 약 75%
- 월 비용 절감: 수백 달러
```

---

## 🔍 성능 모니터링

### 측정 지표
```python
# 각 최적화 적용 전후 측정
metrics = {
    "total_response_time": "전체 응답 시간",
    "llm_call_count": "LLM 호출 횟수",
    "cache_hit_rate": "캐시 히트율",
    "db_query_time": "DB 쿼리 시간",
    "validation_skip_rate": "Validation 스킵 비율",
}
```

### A/B 테스트
```python
# 일부 요청은 기존 방식, 일부는 최적화 방식
if random.random() < 0.5:
    result = optimized_flow(state)  # 최적화 버전
else:
    result = original_flow(state)   # 기존 버전

# 성능 및 품질 비교
```

---

## 📚 참고 자료

- [19. 성능 최적화 여정](./19_performance_optimization_journey.md)
- [OpenAI API Best Practices](https://platform.openai.com/docs/guides/production-best-practices)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/advanced/performance/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

## ✅ 다음 단계

1. ✅ 문서 검토 및 승인
2. ⏳ Quick Wins 구현 (1-2일)
3. ⏳ 성능 테스트 및 측정
4. ⏳ 추가 최적화 진행

**최종 목표**: 3-6초 응답 시간 달성! 🚀
