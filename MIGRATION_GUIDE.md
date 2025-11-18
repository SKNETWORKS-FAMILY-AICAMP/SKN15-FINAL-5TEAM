# Memory System v2 마이그레이션 가이드

> **중요**: `tm-merge-all-logic` 브랜치를 pull 받은 후 **반드시 아래 단계를 따라주세요!**

---

## 🚨 필수 작업

### 1. Git Pull
```bash
git checkout tm-merge-all-logic
git pull origin tm-merge-all-logic
```

### 2. Alembic 마이그레이션 실행 (필수!)
```bash
# Docker 컨테이너 내부에서 실행
docker-compose exec backend alembic upgrade head
```

또는

```bash
# 로컬에서 실행 (가상환경 활성화 후)
cd backend
alembic upgrade head
```

### 3. 마이그레이션 확인
```bash
# 새로운 테이블 4개가 생성되었는지 확인
docker-compose exec postgres psql -U kime -d kimedb -c "
SELECT schemaname, tablename
FROM pg_tables
WHERE tablename IN ('user_profiles', 'short_term_memories', 'scenario_buffers', 'user_memories')
ORDER BY schemaname, tablename;
"
```

**예상 결과:**
```
 schemaname |      tablename
------------+---------------------
 auth       | user_profiles        ← NEW!
 knowledge  | scenario_buffers     ← NEW!
 knowledge  | short_term_memories  ← NEW!
 knowledge  | user_memories        ← 기존 테이블 (컬럼 추가됨)
```

---

## 📊 새로 추가된 테이블

### 1. `auth.user_profiles` (NEW)
- **목적**: 사용자 최소 프로필 정보 (이름, 말투, 취향)
- **주요 컬럼**: `display_name`, `speaking_style`, `likes`, `dislikes`, `personality_traits`

### 2. `knowledge.short_term_memories` (NEW)
- **목적**: 세션별 단기 기억 (5턴 단위 chunk 요약)
- **주요 컬럼**: `user_id`, `scenario_id`, `session_id`, `chunk_summaries` (JSONB)

### 3. `knowledge.scenario_buffers` (NEW)
- **목적**: 시나리오 진행 정보 추적 (시나리오 모드 전용)
- **주요 컬럼**: `user_id`, `scenario_id`, `buffer_summary`, `progress_data` (JSONB)

### 4. `knowledge.user_memories` (컬럼 추가)
- **추가된 컬럼**:
  - `scenario_id` (VARCHAR) - 시나리오 구분 (free-talk/시나리오명)
  - `source_session_id` (UUID) - 출처 세션 ID
  - `tags` (VARCHAR[]) - 태그 배열
  - `confidence` (FLOAT) - 신뢰도 (0.0-1.0)

---

## 🔍 마이그레이션 파일 목록

```
backend/migrations/versions/
├── 20251117_0001_create_user_profiles.py
├── 20251117_0002_create_short_term_memories.py
├── 20251117_0003_create_scenario_buffers.py
└── 20251117_0004_add_scenario_id_to_user_memories.py
```

---

## ⚠️ 문제 해결

### Q1. `alembic upgrade head` 실행 시 에러 발생
```bash
# 현재 마이그레이션 상태 확인
docker-compose exec backend alembic current

# 마이그레이션 히스토리 확인
docker-compose exec backend alembic history

# 특정 버전으로 다운그레이드 후 재시도
docker-compose exec backend alembic downgrade <revision_id>
docker-compose exec backend alembic upgrade head
```

### Q2. "relation already exists" 에러
- 테이블이 이미 존재하는 경우
- 해결: `alembic stamp head`로 현재 상태를 마킹

```bash
docker-compose exec backend alembic stamp head
```

### Q3. Docker 컨테이너가 재시작되면 테이블이 사라짐
- Volume 마운트 확인
- `docker-compose.yml`의 `postgres` 볼륨 설정 확인

```yaml
postgres:
  volumes:
    - postgres_data:/var/lib/postgresql/data  # 영구 저장
```

---

## 🧪 테스트 방법

### 1. STM 생성 테스트
```bash
# free-talk 모드로 5턴 대화 → STM chunk 자동 생성
bash /tmp/test_same_session_v3.sh
```

### 2. LTM 생성 테스트
```bash
# 10턴 대화 → 2개의 STM chunk → LTM 자동 추출
bash /tmp/test_complete_memory_flow.sh
```

### 3. Scenario Buffer 테스트
```bash
# mugen-train 시나리오 5턴 → Scenario Buffer 생성
bash /tmp/test_scenario_buffer.sh
```

### 4. DB 데이터 확인
```bash
# STM 확인
docker-compose exec postgres psql -U kime -d kimedb -c "
SELECT user_id, scenario_id, turn_count,
       jsonb_array_length(chunk_summaries) as chunks
FROM knowledge.short_term_memories
LIMIT 5;
"

# LTM 확인
docker-compose exec postgres psql -U kime -d kimedb -c "
SELECT memory_type, memory_key, tags, confidence,
       source_session_id IS NOT NULL as has_session
FROM knowledge.user_memories
LIMIT 5;
"

# Scenario Buffer 확인
docker-compose exec postgres psql -U kime -d kimedb -c "
SELECT user_id, scenario_id,
       LEFT(buffer_summary, 100) as summary_preview
FROM knowledge.scenario_buffers
LIMIT 5;
"
```

---

## 📚 관련 문서

- [Memory System v2 원리 설명](/tmp/memory_system_principles.md)
- [Memory System v2 개선 사항](/tmp/memory_system_improvements.md)

---

## 💬 문의

마이그레이션 중 문제가 발생하면:
1. 위 문제 해결 섹션 참고
2. 팀 채널에 에러 메시지 공유
3. `alembic current` 및 `alembic history` 결과도 함께 공유

---

**마지막 업데이트**: 2025-01-18
**작성자**: Memory System v2 개발팀
