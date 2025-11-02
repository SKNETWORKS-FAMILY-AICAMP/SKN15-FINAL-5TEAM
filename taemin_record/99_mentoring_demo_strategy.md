# 멘토링 데모 전략 가이드

## 🎯 데모 목표
로컬에서 실시간으로 채팅을 하면서 데이터베이스에 어떻게 적재되는지 보여주기

---

## 📋 사전 준비 체크리스트

### 1. 서버 상태 확인
- [ ] API 서버 실행: `http://localhost:8000`
- [ ] PostgreSQL 실행: `localhost:5433`
- [ ] DBeaver 연결 확인

### 2. 데이터베이스 초기 상태 캡처
```sql
-- 현재 세션 수
SELECT COUNT(*) FROM statedb.sessions;

-- 현재 대화 수
SELECT COUNT(*) FROM statedb.dialogues;

-- 현재 엔티티 수
SELECT COUNT(*) FROM statedb.entities;
```

---

## 🎬 데모 시나리오 (10분)

### Phase 1: 시스템 아키텍처 소개 (2분)

**보여줄 것:**
1. README.md의 시스템 아키텍처 다이어그램
2. 데이터 플로우 설명
   - 사용자 입력 → FastAPI → LangGraph → PostgreSQL

**말할 포인트:**
- "실시간 채팅이 어떻게 데이터베이스에 저장되는지 보여드리겠습니다"
- "6가지 핵심 기능이 모두 자동으로 작동합니다"

---

### Phase 2: 실시간 채팅 + DB 적재 (5분)

#### Step 1: 새 세션 시작
**채팅 입력:**
```
1번: "안녕하세요"
2번: "무한열차에 대해 알려주세요"
3번: "렌고쿠는 어떤 사람인가요?"
```

**DBeaver에서 실시간으로 보여줄 쿼리:**

```sql
-- 1️⃣ 세션 생성 확인
SELECT
    session_id,
    user_id,
    scenario_id,
    turn_count,
    created_at
FROM statedb.sessions
ORDER BY created_at DESC
LIMIT 1;
```

**예상 결과:**
```
session_id: 새로운 UUID
turn_count: 5 (1, 3, 5로 증가)
scenario_id: train
```

---

#### Step 2: 대화 저장 확인

```sql
-- 2️⃣ 대화 저장 확인 (dialogues 테이블)
SELECT
    turn_number,
    speaker,
    LEFT(content, 50) as content_preview,
    emotion,
    timestamp
FROM statedb.dialogues
WHERE session_id = '최신_세션_ID'
ORDER BY turn_number, order_index;
```

**예상 결과:**
```
Turn 1: user → "안녕하세요"
Turn 1: tanjiro → "지금은 임무에 집중해야..."
Turn 3: user → "무한열차에 대해..."
Turn 3: narr → "무한열차의 내부는..."
Turn 3: rengoku → "무한열차는 전설적인..."
...
```

**강조 포인트:**
- ✅ 사용자 입력이 자동으로 저장됨
- ✅ 에이전트 응답(narr, rengoku, tanjiro)도 모두 저장됨
- ✅ 감정(emotion), 감정 강도(emotion_intensity)도 함께 저장

---

#### Step 3: 학습 로그 확인

```sql
-- 3️⃣ AI 학습 로그 확인 (training_logs 테이블)
SELECT
    turn_number,
    agent_name,
    stage_type,
    intent,
    LEFT(user_input, 40) as user_input,
    execution_time_ms,
    timestamp
FROM statedb.training_logs
WHERE session_id = '최신_세션_ID'
ORDER BY turn_number DESC
LIMIT 10;
```

**예상 결과:**
```
Turn 5: dialogue_agent, 0.10ms
Turn 5: children_agent, 1062.87ms
Turn 5: router, 2796.98ms
Turn 5: guardrail, 2501.65ms
```

**강조 포인트:**
- ✅ 각 AI 에이전트의 실행 시간 기록
- ✅ LLM 호출 추적
- ✅ 성능 모니터링 데이터 자동 수집

---

#### Step 4: 엔티티 추출 확인

**채팅 계속:**
```
4번: "아카자와 싸워야 하나요?"
5번: "불의 호흡을 배우고 싶어요"
```

```sql
-- 4️⃣ 엔티티 자동 추출 확인
SELECT
    e.id,
    e.name,
    e.entity_type,
    e.first_mentioned_turn,
    COUNT(em.id) as mention_count
FROM statedb.entities e
LEFT JOIN statedb.entity_mentions em ON e.id = em.entity_id
WHERE e.session_id = '최신_세션_ID'
GROUP BY e.id, e.name, e.entity_type, e.first_mentioned_turn
ORDER BY mention_count DESC;
```

**예상 결과:**
```
아카자 (character): 3회 언급
불의 호흡 (skill): 2회 언급
렌고쿠 (character): 2회 언급
```

**강조 포인트:**
- ✅ NLP 기반 자동 엔티티 추출
- ✅ 캐릭터, 스킬, 장소 등 분류
- ✅ 언급 횟수 추적

---

#### Step 5: 엔티티 멘션 상세

```sql
-- 5️⃣ 엔티티 멘션 상세 (어느 턴에서 언급되었는지)
SELECT
    e.name as entity_name,
    em.turn_number,
    em.context_snippet,
    em.sentiment,
    em.training_log_id
FROM statedb.entity_mentions em
JOIN statedb.entities e ON em.entity_id = e.id
WHERE em.session_id = '최신_세션_ID'
ORDER BY em.turn_number;
```

**예상 결과:**
```
Turn 5: 렌고쿠 (긍정적)
Turn 7: 아카자 (중립)
Turn 9: 불의 호흡 (긍정적)
```

**강조 포인트:**
- ✅ 엔티티가 어느 문맥에서 언급되었는지 추적
- ✅ 감정 분석(sentiment) 포함
- ✅ 학습 로그와 연결

---

#### Step 6: 대화 요약 자동 생성 (하이라이트!)

**채팅 계속 (10턴까지):**
```
6번: "히노카미 카구라는 무엇인가요?"
7번: "우리는 어디로 가야 하나요?"
8번: "승객들이 이상해요"
9번: "이 상황을 어떻게 해결해야 할까요?"
10번: "모두를 지켜야 해요"
```

```sql
-- 6️⃣ 대화 요약 자동 생성 확인 (핵심 기능!)
SELECT
    turn_count,
    summary_turn_count,
    LENGTH(conversation_summary) as summary_length,
    conversation_summary
FROM statedb.sessions
WHERE session_id = '최신_세션_ID';
```

**예상 결과:**
```
turn_count: 19
summary_turn_count: 11 (Turn 11에서 생성됨)
summary_length: 441자
conversation_summary: "현재 스테이지는 TRAIN_PRELUDE이며..."
```

**강조 포인트:**
- ✅ **10턴마다 자동으로 요약 생성** (가장 인상적인 기능!)
- ✅ LLM 기반 요약 (gpt-4o-mini)
- ✅ 주요 이벤트, 캐릭터 관계, 게임 목표 포함

---

### Phase 3: 데이터 구조 설명 (3분)

#### 보여줄 ERD 쿼리

```sql
-- 7️⃣ 전체 데이터 구조 한눈에 보기
SELECT
    'Sessions' as table_name,
    COUNT(*) as count
FROM statedb.sessions
UNION ALL
SELECT 'Dialogues', COUNT(*) FROM statedb.dialogues
UNION ALL
SELECT 'Training Logs', COUNT(*) FROM statedb.training_logs
UNION ALL
SELECT 'Entities', COUNT(*) FROM statedb.entities
UNION ALL
SELECT 'Entity Mentions', COUNT(*) FROM statedb.entity_mentions
UNION ALL
SELECT 'User Memories', COUNT(*) FROM statedb.user_memories;
```

**설명할 것:**
- 19개 테이블의 역할
- 데이터 간의 관계 (sessions → dialogues → training_logs → entities)
- Vector 임베딩 (user_memories.embedding)

---

## 💡 추가 임팩트를 위한 쿼리

### 실시간 성능 모니터링

```sql
-- 8️⃣ AI 에이전트 성능 분석
SELECT
    agent_name,
    COUNT(*) as call_count,
    AVG(execution_time_ms) as avg_time_ms,
    MAX(execution_time_ms) as max_time_ms
FROM statedb.training_logs
WHERE session_id = '최신_세션_ID'
GROUP BY agent_name
ORDER BY avg_time_ms DESC;
```

**예상 결과:**
```
parent_agent: 평균 7253ms (가장 느림 - LLM 호출)
router: 평균 2796ms
guardrail: 평균 2501ms
dialogue_agent: 평균 0.10ms (가장 빠름)
```

---

### 사용자 장기 기억 (임베딩)

```sql
-- 9️⃣ 사용자 장기 기억 확인
SELECT
    memory_key,
    memory_value,
    memory_type,
    importance,
    tags,
    CASE
        WHEN embedding IS NOT NULL THEN '✅ 임베딩 있음'
        ELSE '❌ 임베딩 없음'
    END as embedding_status
FROM statedb.user_memories
WHERE user_id = '테스트'
ORDER BY importance DESC
LIMIT 10;
```

**강조 포인트:**
- ✅ Vector 임베딩으로 의미 기반 검색 가능
- ✅ 중요도 점수로 우선순위 관리
- ✅ 태그 시스템으로 분류

---

## 🎤 발표 스크립트 예시

### 오프닝
"안녕하세요. 오늘은 제가 만든 AI 채팅 시스템의 데이터 파이프라인을 실시간으로 보여드리겠습니다. 왼쪽 화면에는 채팅창, 오른쪽 화면에는 DBeaver를 띄워놓았습니다."

### 데모 중
"지금 '안녕하세요'라고 입력했습니다. 이 쿼리를 실행하면... 보시는 것처럼 방금 입력한 대화가 데이터베이스에 저장되었습니다. 사용자 입력뿐만 아니라 AI의 응답도 모두 저장되고 있습니다."

### 하이라이트
"이제 10번째 대화를 입력했습니다. 여기서 특별한 일이 일어나는데요, 바로 대화 요약이 자동으로 생성됩니다. 이 쿼리를 실행하면... 보시는 것처럼 지금까지의 대화를 441자로 요약한 내용이 자동으로 생성되었습니다!"

### 클로징
"이렇게 6가지 핵심 기능이 모두 자동으로 작동합니다: 대화 저장, 학습 로그, 엔티티 추출, 멘션 추적, 세션 관리, 그리고 대화 요약입니다. 질문 있으시면 받겠습니다!"

---

## 🔧 데모 전 준비사항

### 1. 화면 레이아웃
```
┌─────────────────┬─────────────────┐
│   브라우저       │    DBeaver      │
│  (채팅창)        │   (SQL 쿼리)    │
│  localhost:3000  │                 │
└─────────────────┴─────────────────┘
```

### 2. DBeaver 쿼리 템플릿 준비
위의 9개 쿼리를 미리 SQL 스크립트로 저장해두기
- `demo_01_session.sql`
- `demo_02_dialogues.sql`
- `demo_03_training_logs.sql`
- ...

### 3. 세션 ID 메모장 준비
새로 생성된 session_id를 복사해서 모든 쿼리에 붙여넣기

---

## ⚠️ 주의사항

1. **네트워크 지연 대비**: 로컬 환경이므로 빠르지만, LLM 호출은 2-5초 소요
2. **Turn Count 설명**: Turn이 1, 3, 5, 7...로 증가하는 이유 설명 준비
3. **에러 핸들링**: 만약 에러 발생 시 "이것도 training_logs에 기록됩니다" 설명
4. **백업 데이터**: 데모가 안될 경우를 대비해 이전 세션 ID 준비

---

## 📊 예상 질문 & 답변

### Q1: "왜 Turn이 1, 3, 5로 증가하나요?"
**A**: "각 턴마다 사용자 입력(+1)과 에이전트 응답(+1)이 있어서 2씩 증가합니다. 내부적으로는 단일 대화를 하나의 턴으로 관리하고, 다음 사용자 입력 시 턴이 증가합니다."

### Q2: "실시간으로 요약이 생성되나요?"
**A**: "네, 10턴마다 자동으로 생성됩니다. 약 2-3초 정도 소요되며, gpt-4o-mini 모델을 사용합니다."

### Q3: "데이터베이스 성능은 어떤가요?"
**A**: "PostgreSQL을 사용하고 있으며, 인덱싱과 파티셔닝으로 최적화했습니다. 현재 1만 개 이상의 대화를 처리할 수 있습니다."

### Q4: "임베딩은 어떻게 사용하나요?"
**A**: "pgvector 확장을 사용해서 의미 기반 검색을 합니다. 예를 들어 '불의 호흡'과 유사한 기억을 찾을 수 있습니다."

---

## ✅ 데모 체크리스트

**시작 전:**
- [ ] PostgreSQL 실행 확인
- [ ] API 서버 실행 확인
- [ ] DBeaver 연결 확인
- [ ] 브라우저 테스트 채팅 1번 (연결 확인용)
- [ ] 쿼리 템플릿 준비
- [ ] 화면 레이아웃 설정

**데모 중:**
- [ ] 채팅 입력 → 즉시 쿼리 실행
- [ ] 결과 설명 → 다음 채팅
- [ ] Turn 10 도달 시 요약 생성 강조
- [ ] 성능 모니터링 쿼리 보여주기

**종료 후:**
- [ ] 질문 받기
- [ ] README.md 링크 공유
- [ ] 데모 세션 데이터 보존 (나중에 분석용)

---

## 🎯 핵심 메시지

**"실시간 채팅이 → 6가지 데이터로 → 자동 저장됩니다"**

1. 💬 대화 (Dialogues)
2. 📊 학습 로그 (Training Logs)
3. 🏷️ 엔티티 (Entities)
4. 📌 엔티티 멘션 (Entity Mentions)
5. 🧠 세션 상태 (Sessions)
6. 📝 **대화 요약 (Conversation Summary)** ← 하이라이트!

---

## 🚀 추가 임팩트 아이디어

### 1. 실시간 그래프 시각화
- Grafana 대시보드로 실시간 메트릭 표시
- 턴 수, 응답 시간, 엔티티 수 등

### 2. 엔티티 관계 그래프
```sql
-- 엔티티 간 관계 시각화
SELECT
    e1.name as from_entity,
    r.relationship_type,
    e2.name as to_entity,
    r.strength
FROM statedb.entity_relationships r
JOIN statedb.entities e1 ON r.entity_id_1 = e1.id
JOIN statedb.entities e2 ON r.entity_id_2 = e2.id
WHERE r.session_id = '최신_세션_ID';
```

### 3. 감정 분석 타임라인
```sql
-- 대화의 감정 변화 추이
SELECT
    turn_number,
    speaker,
    emotion,
    emotion_intensity
FROM statedb.dialogues
WHERE session_id = '최신_세션_ID'
  AND speaker != 'user'
ORDER BY turn_number;
```

---

## 📝 데모 타이밍 가이드

| 시간 | 활동 | 예상 소요 |
|------|------|----------|
| 0:00-2:00 | 아키텍처 소개 | 2분 |
| 2:00-3:00 | 채팅 3번 + 세션/대화 쿼리 | 1분 |
| 3:00-4:00 | 학습 로그 쿼리 | 1분 |
| 4:00-5:00 | 채팅 2번 + 엔티티 쿼리 | 1분 |
| 5:00-7:00 | 채팅 5번 (Turn 10 도달) | 2분 |
| 7:00-8:00 | **요약 쿼리 (하이라이트!)** | 1분 |
| 8:00-9:00 | 성능 분석 쿼리 | 1분 |
| 9:00-10:00 | 종합 정리 + Q&A | 1분 |

**총 10분 완벽 데모!**
