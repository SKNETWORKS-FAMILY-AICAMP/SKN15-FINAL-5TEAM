# Graph RAG 시스템 - 데이터베이스 포트 설정 수정

**날짜**: 2025-10-31
**문제**: 엔티티 추출은 작동하지만 엔티티가 저장되지 않음
**근본 원인**: `.env.local`의 잘못된 데이터베이스 포트

## 문제 요약

완전한 Graph RAG 시스템(Phase 0-8)을 구현한 후, 엔티티 추출은 작동했지만 엔티티가 데이터베이스에 저장되지 않았습니다. 에러 메시지는 다음과 같았습니다:

```
Database error: relation "statedb.entities" does not exist
LINE 2:                   INSERT INTO statedb.entities (
```

이것은 혼란스러웠습니다. 왜냐하면:
- `statedb.entities` 테이블이 데이터베이스에 명백히 존재했음
- `DatabaseManager.save_entity()`의 수동 테스트가 완벽하게 작동했음
- search_path가 올바르게 구성되었음
- 모든 마이그레이션이 성공적으로 실행되었음

## 조사 과정

### 1. 초기 디버깅
- 엔티티 테이블 존재 확인: ✅
- 마이그레이션 실행 확인: ✅
- search_path 설정 추가: 여전히 실패 ❌
- 서버 여러 번 재시작: 여전히 실패 ❌

### 2. 직접 테스트
동일한 파라미터로 `DatabaseManager`를 직접 인스턴스화한 테스트 스크립트 생성:
```python
db = DatabaseManager(
    host="localhost",
    port=5433,
    dbname="kimedb",
    user="kime",
    password="dev123"
)
entity_id = db.save_entity(...)  # ✅ 성공!
```

이것은 `DatabaseManager`가 서버 컨텍스트 밖에서 올바르게 작동함을 증명했습니다.

### 3. 디버그 로깅
`TrainingLogger`에 실제 연결 파라미터를 출력하는 디버그 로깅을 추가:

```python
print(f"[TrainingLogger DEBUG] DB connection: {db_user}@{db_host}:{db_port}/{db_name}")
```

출력 결과:
```
[TrainingLogger DEBUG] DB connection: kime@127.0.0.1:5432/kimedb
```

**5433이 아닌 포트 5432!** 이것은 완전히 다른 데이터베이스 인스턴스에 연결하고 있었습니다.

### 4. 근본 원인 발견

`DB_PORT`가 정의된 곳을 검색:
```bash
$ grep -r "DB_PORT" backend/.env*
backend/.env.local:DB_PORT=5432  # ❌ 잘못된 포트
```

`.env.local` 파일에 `DB_PORT=5432`(표준 PostgreSQL 포트)가 있었지만, Docker 데이터베이스는 `DB_PORT=5433`에서 실행되고 있었습니다.

## 해결 방법

[.env.local](../backend/.env.local)을 변경:
```bash
# 이전
DB_PORT=5432  # ❌

# 이후
DB_PORT=5433  # ✅
```

## 검증

포트 수정 및 서버 재시작 후:

1. **엔티티 추출**: ✅ 작동
   ```
   [TrainingLogger] Processed 3 entities for log 67
   ```

2. **엔티티 저장**: ✅ 작동
   ```sql
   SELECT COUNT(*) FROM statedb.entities;
   -- 결과: 8개 엔티티
   ```

3. **엔티티 멘션 생성**: ✅ 작동
   ```sql
   SELECT COUNT(*) FROM statedb.entity_mentions;
   -- 결과: 12개 멘션
   ```

4. **훈련 로그 업데이트**: ✅ 작동
   ```sql
   SELECT mentioned_entity_ids, embedding IS NOT NULL
   FROM training_logs
   ORDER BY id DESC LIMIT 3;

   -- 결과:
   -- {1,2,3}, true
   -- {1,2,3}, true
   -- {1,2,3}, true
   ```

## 변경된 주요 파일

1. [backend/.env.local](../backend/.env.local)
   - `DB_PORT=5432`를 `DB_PORT=5433`으로 변경

2. [backend/src/database/db_manager.py](../backend/src/database/db_manager.py#L70-L72)
   - 이미 search_path 설정을 가지고 있었음 (도움이 되었지만 근본 원인은 아님)

3. [backend/src/tools/training_logger.py](../backend/src/tools/training_logger.py#L86-L97)
   - 수정 확인 후 디버그 로깅 제거

## 교훈

1. **환경 변수 우선순위가 중요함**: `.env.local`이 예상되는 기본값을 오버라이드하고 있었음
2. **디버그 로깅이 매우 유용함**: 연결 파라미터 로깅을 추가하여 문제를 즉시 발견했음
3. **직접 테스트가 문제를 분리함**: `DatabaseManager`를 직접 테스트하여 코드 문제가 아님을 증명했음
4. **에러 메시지가 오해를 불러일으킬 수 있음**: "relation does not exist"는 테이블이 누락되었음을 의미하지 않고, 완전히 다른 데이터베이스에 연결되어 있었음을 의미했음

## 현재 상태

✅ **Graph RAG 시스템 완전 작동 중**

- 엔티티 추출: 규칙 60% + LLM 40%
- 관계 추출: 동시 발생 60% + 규칙 20% + LLM 20%
- 임베딩: text-embedding-3-small (1536 차원)
- 벡터 검색: 코사인 거리를 사용한 IVFFlat 인덱스
- 그래프 탐색: 양방향 관계 쿼리
- Auto-labeling: 규칙 30% + LLM 30% + 그래프 40% 준비 완료

모든 컴포넌트가 통합되어 end-to-end로 작동 중입니다.
