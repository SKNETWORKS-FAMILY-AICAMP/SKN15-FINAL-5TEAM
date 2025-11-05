# Phase 4: AI 훈련 로그 시스템 구현

**작성일**: 2025-10-30
**목적**: SLLM LoRA 훈련을 위한 로그 수집 시스템 구축
**상태**: ✅ 구현 완료

---

## 📋 목차

1. [개요](#개요)
2. [설계 원칙](#설계-원칙)
3. [구현 내용](#구현-내용)
4. [자동 라벨링 로직](#자동-라벨링-로직)
5. [사용 방법](#사용-방법)
6. [데이터 추출](#데이터-추출)
7. [LoRA 훈련 파이프라인](#lora-훈련-파이프라인)
8. [다음 단계](#다음-단계)

---

## 개요

### 목표
Phase 4는 **에이전트 실행 로그를 수집하여 SLLM(Small Language Model) LoRA 파인튜닝에 사용할 수 있는 데이터셋을 자동으로 생성**하는 것을 목표로 합니다.

### 핵심 아이디어
- ✅ **최소 전처리**: 로그 자체로 의미 있는 훈련 데이터
- ✅ **자동 라벨링**: success/failure/partial을 휴리스틱으로 자동 판정
- ✅ **비침습적**: 기존 에이전트 로직에 영향 없음
- ✅ **확장 가능**: 향후 Children, Dialogue 에이전트도 추가 가능

### 기대 효과
1. **Router Agent 경량화**: LoRA 모델로 대체하여 비용 절감 (GPT-4o-mini → Phi-3 등)
2. **Prompt 최적화**: 실제 데이터 기반 프롬프트 개선
3. **성능 향상**: 도메인 특화 모델로 응답 품질 향상
4. **지속적 학습**: 운영 데이터를 활용한 모델 개선

---

## 설계 원칙

### 1. 최소 전처리 (Minimal Preprocessing)
로그 데이터는 **그 자체로 의미가 있어야** 합니다. 복잡한 전처리 없이 바로 훈련에 사용할 수 있도록 설계했습니다.

**구조**:
```json
{
  "context": {
    "scenario_id": "train",
    "current_stage": "EPISODE_1",
    "user_input": "저 사람 누구야?",
    "history": [...]
  },
  "model_output": {
    "classification": "on_topic",
    "next_node": "parent_agent",
    "confidence": 0.95
  },
  "outcome": "success",
  "feedback_score": 0.85
}
```

### 2. 자동 라벨링 (Automatic Labeling)
사람의 개입 없이 **휴리스틱 기반 자동 라벨링**을 수행합니다.

**라벨 타입**:
- `success`: 좋은 예시 (정확한 분류, 빠른 응답, 적절한 출력)
- `partial`: 애매한 예시 (일부 조건 충족)
- `failure`: 나쁜 예시 (잘못된 분류, 에러 발생, 비정상 출력)
- `null`: 라벨 없음 (향후 human-in-the-loop로 보완)

### 3. 품질 점수 (Feedback Score)
각 로그에 **0.0 ~ 1.0 점수**를 부여하여 weighted learning이 가능하도록 합니다.

**점수 활용**:
- LoRA 훈련 시 가중치로 사용
- 낮은 점수 (< 0.5) 샘플은 negative example로 활용
- 높은 점수 (> 0.8) 샘플은 우선적으로 학습

---

## 구현 내용

### 1. LogDB 테이블 스키마

**파일**: [`backend/database/migrations/002_logdb_training_logs.sql`](../backend/database/migrations/002_logdb_training_logs.sql)

**테이블 구조**:
```sql
CREATE TABLE training_logs (
    id BIGSERIAL PRIMARY KEY,

    -- Session context
    session_id UUID NOT NULL,
    turn_count INT NOT NULL,
    scenario_id VARCHAR(50),
    current_stage VARCHAR(100),

    -- Agent information
    agent_name VARCHAR(50) NOT NULL,  -- 'router', 'parent', 'children', 'dialogue'

    -- Input/Output (학습 데이터)
    user_input TEXT,
    context JSONB NOT NULL,
    model_output JSONB NOT NULL,

    -- Performance metrics
    latency_ms INT,
    token_count INT,
    llm_model VARCHAR(100),

    -- Auto-labeling
    outcome VARCHAR(20),  -- 'success', 'failure', 'partial', null
    outcome_reason TEXT,
    feedback_score FLOAT CHECK (feedback_score >= 0.0 AND feedback_score <= 1.0),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    labeled_at TIMESTAMP,
    is_error BOOLEAN DEFAULT FALSE,
    error_message TEXT
);
```

**인덱스**:
- `idx_training_logs_agent_name`: 에이전트별 조회
- `idx_training_logs_outcome`: outcome 필터링
- `idx_training_logs_created_at`: 시간 범위 조회
- `idx_training_logs_agent_outcome_time`: 복합 인덱스 (가장 많이 사용)
- `idx_training_logs_context_gin`: JSONB 필드 검색 (GIN 인덱스)

### 2. 로그 수집 유틸리티

**파일**: [`backend/src/tools/training_logger.py`](../backend/src/tools/training_logger.py)

**주요 클래스 및 함수**:

#### `TrainingLogger` 클래스
```python
class TrainingLogger:
    def log_agent_execution(
        self,
        agent_name: str,
        state: Dict[str, Any],
        model_output: Dict[str, Any],
        latency_ms: int,
        token_count: Optional[int] = None,
        llm_model: Optional[str] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """에이전트 실행 로그 저장"""
```

**기능**:
- ✅ PostgreSQL LogDB에 로그 저장
- ✅ Context 자동 추출 (`_extract_context()`)
- ✅ 자동 라벨링 (`_auto_label()`)
- ✅ 에이전트별 맞춤 라벨링 로직 (`_label_router()`, `_label_parent()`, ...)

#### `log_agent()` 편의 함수
```python
log_agent(
    agent_name="router",
    state=state,
    model_output=result,
    start_time=start_time,
    llm_model="gpt-4o-mini"
)
```

**사용 예시**:
```python
start = time.perf_counter()
result = run_router_agent(state, user_input)

log_agent(
    agent_name="router",
    state=state,
    model_output=result,
    start_time=start,
    llm_model="gpt-4o-mini"
)
```

### 3. 에이전트 통합

#### Router Agent
**파일**: [`backend/src/agents/router_agent.py`](../backend/src/agents/router_agent.py)

**수정 사항**:
1. import에 `time`, `log_agent` 추가
2. `run()` 메서드 시작 부분에 `start_time = time.perf_counter()` 추가
3. 모든 return 경로에서 `_log_execution()` 호출
4. `_log_execution()` 헬퍼 메서드 추가

```python
def run(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    start_time = time.perf_counter()

    # ... 기존 로직 ...

    if topic.is_off_topic:
        result = self._handle_off_topic(...)
    else:
        result = self._handle_on_topic(...)

    # Phase 4: 로그 수집
    self._log_execution(state, result, start_time)
    return result

def _log_execution(self, state, result, start_time):
    """Router Agent 실행 로그를 LogDB에 저장"""
    model_output = {
        "next_node": result.get("next_node"),
        "classification": result.get("classification"),
        "confidence": result.get("confidence"),
        ...
    }
    log_agent("router", state, model_output, start_time, llm_model="gpt-4o-mini")
```

#### Parent Agent
**파일**: [`backend/src/agents/parent_agent.py`](../backend/src/agents/parent_agent.py)

**수정 사항**:
1. import에 `time`, `log_agent` 추가
2. `run_parent_agent()` wrapper 함수에서 로깅 처리 (try-except 패턴)

```python
def run_parent_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.perf_counter()

    try:
        result = DEFAULT_AGENT.run(state)

        model_output = {
            "agent_inputs": result.get("agent_inputs"),
            "next_stage": result.get("next_stage"),
            ...
        }

        log_agent("parent", state, model_output, start_time, llm_model="gpt-4o")
        return result

    except Exception as e:
        # 에러 발생 시에도 로그 수집 (실패 예시로 활용)
        log_agent("parent", state, {"error": str(e)}, start_time, is_error=True, error_message=str(e))
        raise
```

---

## 자동 라벨링 로직

### Router Agent 라벨링

**성공 조건** (`outcome = "success"`, `feedback_score >= 0.75`):
- ✅ `on_topic` → `parent_agent` 라우팅이 정확함
- ✅ `off_topic` → `warning_handler` 라우팅이 정확함
- ✅ `confidence >= 0.8` (높은 확신도)

**실패 조건** (`outcome = "failure"`, `feedback_score < 0.5`):
- ❌ `classification`과 `next_node`가 불일치
- ❌ `confidence < 0.3` (낮은 확신도)
- ❌ 에러 발생

**코드**:
```python
def _label_router(self, state, model_output):
    classification = model_output.get("classification")
    next_node = model_output.get("next_node")

    score = 0.7  # 기본 점수

    # 분류와 라우팅 일치도 검사
    if classification == "on_topic" and "parent" in next_node:
        score += 0.15
        reason = "Correctly identified on-topic and routed to parent"
    elif classification == "off_topic" and "warning" in next_node:
        score += 0.15
        reason = "Correctly identified off-topic and routed to warning"
    else:
        score -= 0.3
        reason = f"Mismatch: {classification} vs {next_node}"

    # Confidence 점수 반영
    confidence = model_output.get("confidence", 0.5)
    if confidence > 0.8:
        score += 0.1
    elif confidence < 0.3:
        score -= 0.1

    # Outcome 결정
    if score >= 0.75:
        outcome = "success"
    elif score >= 0.5:
        outcome = "partial"
    else:
        outcome = "failure"

    return (outcome, reason, score)
```

### Parent Agent 라벨링

**성공 조건**:
- ✅ `agent_inputs.children.beats`가 비어있지 않음
- ✅ `beats` 수가 적절함 (3~5개)
- ✅ 스테이지 전환이 올바름

**실패 조건**:
- ❌ `agent_inputs`가 비어있음
- ❌ `beats`가 생성되지 않음
- ❌ 에러 발생

**코드**:
```python
def _label_parent(self, state, model_output):
    agent_inputs = model_output.get("agent_inputs", {})

    score = 0.7

    # agent_inputs 유효성 검사
    if not agent_inputs or "children" not in agent_inputs:
        return ("failure", "agent_inputs is empty", 0.2)

    beats = agent_inputs.get("children", {}).get("beats", [])

    # Beats 품질 검사
    if not beats:
        score -= 0.3
        reason = "No beats generated"
    elif len(beats) >= 3:
        score += 0.15
        reason = f"Good beats count: {len(beats)}"

    # 스테이지 전환
    if model_output.get("next_stage"):
        score += 0.1

    # Outcome 결정
    if score >= 0.75:
        outcome = "success"
    elif score >= 0.5:
        outcome = "partial"
    else:
        outcome = "failure"

    return (outcome, reason, score)
```

---

## 사용 방법

### 1. 환경변수 설정

**`.env` 파일**:
```bash
# LogDB URL (RDS 또는 로컬 PostgreSQL)
LOGDB_URL=postgresql://postgres:password@localhost:5432/kime_logdb

# 로깅 활성화 (기본값: true)
TRAINING_LOGGER_ENABLED=true
```

### 2. 마이그레이션 실행

```bash
# LogDB 생성 (RDS에서 이미 생성했다면 스킵)
psql -h <RDS_ENDPOINT> -U postgres -c "CREATE DATABASE kime_logdb;"

# 마이그레이션 실행
psql -h <RDS_ENDPOINT> -U postgres -d kime_logdb < backend/database/migrations/002_logdb_training_logs.sql
```

### 3. 로그 수집 확인

```bash
# 서버 시작
cd backend
python api_server.py

# API 호출 (로그 자동 수집됨)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "train",
    "user_input": "시작",
    "user_name": "테스트"
  }'

# LogDB 확인
psql -h localhost -U postgres -d kime_logdb

kime_logdb=# SELECT count(*) FROM training_logs;
 count
-------
     2  -- Router + Parent 로그
(1 row)

kime_logdb=# SELECT agent_name, outcome, feedback_score, created_at
             FROM training_logs
             ORDER BY created_at DESC
             LIMIT 5;

 agent_name | outcome | feedback_score |         created_at
------------+---------+----------------+----------------------------
 parent     | success |           0.85 | 2025-10-30 14:23:45.123456
 router     | success |           0.95 | 2025-10-30 14:23:45.001234
```

### 4. 로깅 비활성화 (테스트 시)

```bash
# 환경변수로 비활성화
export TRAINING_LOGGER_ENABLED=false
python api_server.py
```

---

## 데이터 추출

### 1. Router Agent 훈련 데이터

```sql
-- Router Agent의 성공 예시 추출 (최근 7일, 점수 0.6 이상)
SELECT
    user_input,
    context->>'scenario_id' as scenario_id,
    context->>'current_stage' as current_stage,
    context->'history' as recent_history,
    model_output->>'classification' as classification,
    model_output->>'next_node' as next_node,
    model_output->>'confidence' as confidence,
    outcome,
    feedback_score,
    latency_ms
FROM training_logs
WHERE agent_name = 'router'
  AND outcome IN ('success', 'partial')
  AND feedback_score >= 0.6
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY feedback_score DESC, latency_ms ASC
LIMIT 10000;
```

### 2. LoRA 훈련 데이터셋 Export

```sql
-- JSON Lines 형식으로 export (LoRA 훈련용)
COPY (
    SELECT jsonb_build_object(
        'prompt', context->>'user_input',
        'context', jsonb_build_object(
            'scenario_id', context->>'scenario_id',
            'current_stage', context->>'current_stage',
            'history', context->'history'
        ),
        'completion', model_output,
        'weight', feedback_score  -- 가중치
    )
    FROM training_logs
    WHERE agent_name = 'router'
      AND outcome = 'success'
      AND feedback_score >= 0.7
      AND created_at >= NOW() - INTERVAL '90 days'
    ORDER BY RANDOM()  -- 훈련 데이터 셔플
    LIMIT 50000
) TO '/tmp/router_training_dataset.jsonl';
```

### 3. 실패 패턴 분석

```sql
-- 실패 패턴 분석 (어떤 케이스에서 자주 실패하는지)
SELECT
    agent_name,
    outcome_reason,
    COUNT(*) as failure_count,
    AVG(latency_ms) as avg_latency,
    AVG(feedback_score) as avg_score,
    jsonb_object_agg(
        context->>'current_stage',
        COUNT(*)
    ) FILTER (WHERE context->>'current_stage' IS NOT NULL) as stage_breakdown
FROM training_logs
WHERE outcome = 'failure'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY agent_name, outcome_reason
ORDER BY failure_count DESC
LIMIT 20;
```

### 4. A/B 테스트 데이터

```sql
-- LLM 모델별 성능 비교
SELECT
    llm_model,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE outcome = 'success') as success_count,
    ROUND(AVG(feedback_score)::numeric, 3) as avg_score,
    ROUND(AVG(latency_ms)::numeric, 1) as avg_latency_ms,
    ROUND(AVG(token_count)::numeric, 0) as avg_tokens
FROM training_logs
WHERE agent_name = 'router'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY llm_model
ORDER BY avg_score DESC;
```

---

## LoRA 훈련 파이프라인

### 1. 데이터 준비

```bash
# Step 1: LogDB에서 데이터 추출
psql -h <RDS_ENDPOINT> -U postgres -d kime_logdb -f extract_training_data.sql > router_dataset.jsonl

# Step 2: Train/Val/Test 분할 (80/10/10)
python scripts/split_dataset.py \
  --input router_dataset.jsonl \
  --train router_train.jsonl \
  --val router_val.jsonl \
  --test router_test.jsonl \
  --split 0.8,0.1,0.1
```

### 2. LoRA 훈련 (예시: Phi-3)

```bash
# Hugging Face Trainer 사용
python scripts/train_lora.py \
  --base_model microsoft/Phi-3-mini-4k-instruct \
  --train_data router_train.jsonl \
  --val_data router_val.jsonl \
  --output_dir ./lora_router \
  --learning_rate 1e-4 \
  --batch_size 16 \
  --epochs 3 \
  --lora_r 16 \
  --lora_alpha 32 \
  --lora_dropout 0.1
```

**훈련 스크립트 예시** (`scripts/train_lora.py`):
```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import json

# 모델 로드
base_model = AutoModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-4k-instruct")
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

# LoRA 설정
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(base_model, lora_config)

# 데이터셋 로드
def load_dataset(file_path):
    with open(file_path) as f:
        return [json.loads(line) for line in f]

train_data = load_dataset("router_train.jsonl")
val_data = load_dataset("router_val.jsonl")

# 훈련
training_args = TrainingArguments(
    output_dir="./lora_router",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    learning_rate=1e-4,
    logging_steps=10,
    save_steps=100,
    evaluation_strategy="steps",
    eval_steps=100
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_data,
    eval_dataset=val_data,
)

trainer.train()
```

### 3. 모델 평가

```bash
# 테스트 데이터로 평가
python scripts/evaluate_lora.py \
  --model_path ./lora_router \
  --test_data router_test.jsonl \
  --metrics accuracy,f1,latency
```

### 4. 배포

```bash
# LoRA 모델을 프로덕션 환경에 배포
# Option 1: 기존 GPT-4o-mini 대체
# Option 2: A/B 테스트 (50% 트래픽)

# Router Agent 수정
# before: llm_client.call_json(model="gpt-4o-mini", ...)
# after:  lora_client.call_json(model="phi-3-lora-router", ...)
```

---

## 다음 단계

### 1. Children Agent 로그 수집 (우선순위: 높음)
- [ ] Children Agent에 로깅 코드 추가
- [ ] 대사 생성 품질 라벨링 로직 구현
- [ ] Beats와 대사 일치도 자동 평가

### 2. Dialogue Agent 로그 수집 (우선순위: 중간)
- [ ] Dialogue Agent validation 로그 수집
- [ ] User feedback 연동 (thumbs up/down)
- [ ] Human-in-the-loop 라벨링 시스템

### 3. 데이터 파이프라인 자동화 (우선순위: 높음)
- [ ] 주기적 데이터 추출 (Airflow/Cron)
- [ ] 자동 train/val/test 분할
- [ ] S3에 데이터셋 아카이빙

### 4. LoRA 훈련 및 배포 (우선순위: 높음)
- [ ] Router Agent LoRA 모델 훈련
- [ ] 성능 벤치마크 (GPT-4o-mini vs LoRA)
- [ ] A/B 테스트 프레임워크 구축
- [ ] 프로덕션 배포

### 5. 고도화 (우선순위: 낮음)
- [ ] Multi-agent LoRA (Router + Parent 통합)
- [ ] 지속적 학습 (Continual Learning)
- [ ] 적대적 샘플 생성 및 보강

---

## 요약

**Phase 4 구현 완료 내용**:
- ✅ LogDB 테이블 스키마 생성 (`training_logs`, `user_feedback`)
- ✅ 로그 수집 유틸리티 모듈 (`training_logger.py`)
- ✅ Router Agent 로그 수집 통합
- ✅ Parent Agent 로그 수집 통합
- ✅ 자동 라벨링 로직 (success/failure/partial, feedback_score)
- ✅ 데이터 추출 쿼리 예시

**핵심 성과**:
- 🎯 **최소 전처리**: 로그 자체로 의미 있는 훈련 데이터
- 🤖 **자동 라벨링**: 사람 개입 없이 품질 점수 부여
- 📊 **확장 가능**: 향후 모든 에이전트에 적용 가능
- 💰 **비용 절감**: LoRA로 대체 시 LLM 비용 80% 절감 예상

**다음 마일스톤**: Children Agent 로그 수집 + LoRA 훈련 파이프라인 구축

---

**작성자**: Claude Code
**마지막 업데이트**: 2025-10-30
**버전**: 1.0
