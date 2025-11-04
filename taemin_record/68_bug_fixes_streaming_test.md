# 100. 백엔드 버그 수정 및 스트리밍 테스트

**날짜**: 2025-11-04
**작업자**: Claude (with 태민)
**키워드**: `버그 수정`, `스트리밍`, `디버깅`, `children_agent`, `db_manager`

## 📋 개요

이전 세션에서 LLM 스트리밍 구현을 완료한 후, 테스트 중 발견된 백엔드 버그 2개를 수정하고 서버를 재시작했습니다.

---

## 🐛 발견된 버그

### 1. children_agent.py:434 - AttributeError

**에러 내용**:
```python
AttributeError: 'str' object has no attribute 'get'
```

**원인**:
- `stages` 리스트의 항목이 문자열일 수 있는데, 딕셔너리로 가정하고 `.get()` 메서드 호출
- 시나리오 데이터의 `stages` 필드가 혼합 타입을 허용하고 있었음

**수정 위치**: `backend/src/agents/children_agent.py:434-437`

**수정 전**:
```python
# 현재 스테이지의 context 찾기
stages = scenario_ref.get("stages", [])
for stage in stages:
    if stage.get("tag") == stage_tag:  # ❌ stage가 문자열이면 에러
        stage_context = stage.get("context", "")
        break
```

**수정 후**:
```python
# 현재 스테이지의 context 찾기
stages = scenario_ref.get("stages", [])
for stage in stages:
    # stage가 딕셔너리인지 확인 (문자열일 수도 있음)
    if isinstance(stage, dict) and stage.get("tag") == stage_tag:  # ✅ 타입 체크 추가
        stage_context = stage.get("context", "")
        break
```

### 2. db_manager.py:1586 - AttributeError

**에러 내용**:
```python
AttributeError: 'DatabaseManager' object has no attribute 'execute_query'
```

**원인**:
- `DatabaseManager` 클래스에 `execute_query` 메서드가 존재하지 않음
- 다른 메서드들은 `with self.get_connection()` 패턴을 사용하는데, credits 관련 메서드만 존재하지 않는 메서드를 호출

**수정 위치**:
- `backend/src/database/db_manager.py:1579-1593` (get_user_credits)
- `backend/src/database/db_manager.py:1595-1619` (consume_credits)
- `backend/src/database/db_manager.py:1621-1645` (add_credits)

**수정 전** (get_user_credits):
```python
def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 크레딧 조회"""
    query = """
    SELECT bubble_count, total_purchased, total_consumed, last_updated
    FROM statedb.user_credits
    WHERE user_id = %s
    """
    results = self.execute_query(query, (user_id,))  # ❌ 존재하지 않는 메서드
    return results[0] if results else None
```

**수정 후** (get_user_credits):
```python
def get_user_credits(self, user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 크레딧 조회"""
    try:
        with self.get_connection() as conn:  # ✅ 올바른 패턴 사용
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT bubble_count, total_purchased, total_consumed, last_updated
                    FROM statedb.user_credits
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                return dict(result) if result else None
    except Exception as e:
        logger.error(f"Failed to get user credits: {e}")
        return None
```

**수정 후** (consume_credits, add_credits):
- 동일한 패턴으로 `self.execute_query()` 호출을 `with self.get_connection()` 패턴으로 변경
- 에러 핸들링 추가 (`try-except`)
- 로깅 추가

---

## 🔧 수정 작업 프로세스

### 1. 버그 발견
```bash
# 테스트 중 서버 로그에서 에러 발견
❌ Error in chat endpoint: 'str' object has no attribute 'get'
❌ AttributeError: 'DatabaseManager' object has no attribute 'execute_query'
```

### 2. 원인 분석
- children_agent.py: `isinstance()` 타입 체크 누락
- db_manager.py: 일관성 없는 메서드 호출 패턴

### 3. 수정 및 테스트
```bash
# 모든 백엔드 프로세스 종료
lsof -ti:8000 | xargs kill -9

# 서버 재시작
cd /Users/jtm427/Desktop/workspace/backend
/Users/jtm427/miniconda3/envs/openai/bin/python api_server.py

# 서버 정상 실행 확인
lsof -ti:8000  # ✅ 88299, 88323 (정상 실행 중)
```

---

## ✅ 수정 완료 항목

1. **children_agent.py:434** - `isinstance(stage, dict)` 타입 체크 추가
2. **db_manager.py:1586** - `get_user_credits()` 메서드 수정
3. **db_manager.py:1612** - `consume_credits()` 메서드 수정
4. **db_manager.py:1632** - `add_credits()` 메서드 수정
5. **백엔드 서버** - 재시작 완료 (port 8000)
6. **프론트엔드 서버** - 정상 실행 중 (port 3000)

---

## 🎯 현재 상태

### 서버 상태
- ✅ 백엔드 서버: http://localhost:8000 (실행 중)
- ✅ 프론트엔드 서버: http://localhost:3000 (실행 중)

### LLM 스트리밍 구현 상태
- ✅ 백엔드: SSE (Server-Sent Events) 방식 구현 완료
- ✅ 프론트엔드: Fetch Streaming API 구현 완료
- ✅ 타이핑 효과: 0.8초 간격으로 대화 전송
- ⚠️ 테스트: 버그 수정 완료, 실제 스트리밍 테스트 필요

### 다음 작업
1. 브라우저에서 http://localhost:3000 접속
2. 로그인 후 시나리오 선택
3. 스트리밍 응답 확인 (0.8초 간격 타이핑 효과)
4. 에러 발생 시 추가 디버깅

---

## 📚 참고 자료

**이전 문서**:
- 이전 세션에서 LLM 스트리밍 구현 완료 (문서 번호 미확인)

**관련 파일**:
- [backend/src/agents/children_agent.py:434](backend/src/agents/children_agent.py#L434)
- [backend/src/database/db_manager.py:1579-1645](backend/src/database/db_manager.py#L1579-L1645)
- [backend/api_server.py:2469-2520](backend/api_server.py#L2469-L2520) (스트리밍 구현 부분)
- [front/src/services/api.ts:188-308](front/src/services/api.ts#L188-L308) (프론트엔드 스트리밍)

**에러 로그**:
```
[INFO] [CHILDREN] 🎭 LLM Beats mode enabled for stage=HEROES_ARRIVE
Traceback (most recent call last):
  ...
  File "backend/src/agents/children_agent.py", line 434, in _generate_beats_from_context
    if stage.get("tag") == stage_tag:
       ^^^^^^^^^
AttributeError: 'str' object has no attribute 'get'
```

---

## 💡 배운 점

1. **타입 안정성**: Python의 동적 타이핑 특성상 `isinstance()` 체크가 중요
2. **일관성**: 코드베이스 전체에서 일관된 패턴 사용의 중요성
3. **에러 핸들링**: try-except와 로깅을 통한 디버깅 용이성 향상
4. **테스트 중요성**: 스트리밍 구현 후 실제 테스트 중 버그 발견

---

**다음 문서**: 실제 스트리밍 테스트 결과 및 성능 측정 예정
