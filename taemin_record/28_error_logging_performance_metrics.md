# 프로덕션 로깅 시스템 통합 (Error Logging + Performance Metrics + General Logs)

## 📅 Date: 2025-10-31

## 🎯 Overview

이 문서는 프로덕션 안정성과 최적화를 위해 추가된 **Error Logging**, **Performance Metrics**, **General Logs** 통합 작업을 정리합니다.

**작업 목표:**
- 🔥 HIGH Priority: Error Logging 시스템 통합
- 🔥 HIGH Priority: Performance Metrics 수집 시스템 통합
- 🟡 MEDIUM Priority: General Logs 시스템 통합

**작업 범위:**
1. `api_server.py` - 워크플로우, DB 작업, 주요 이벤트 추적
2. `router_agent.py` - LLM 호출 에러 추적
3. `children_agent.py` - LLM 대화 생성 및 Beats 생성 에러 추적
4. `parent_agent.py` - 스테이지 핸들링 성능 추적

---

## ✅ 완료된 작업

### 1. api_server.py - Error Logging (5개 추가)

#### 1.1 워크플로우 실행 실패 에러
**위치:** [api_server.py:1108-1125](../backend/api_server.py#L1108-L1125)
```python
try:
    result_state = workflow_instance.invoke(state)
except Exception as e:
    # 🚨 Workflow 실행 실패 에러 로깅
    try:
        SESSION_MANAGER.save_error_log(
            error_type="workflow_execution_failed",
            error_message=str(e),
            session_id=session_id,
            metadata={
                "stage": state.get("current_stage"),
                "turn_count": state.get("turn_count"),
                "user_input": user_input[:100] if user_input else None
            }
        )
    except:
        pass
    raise
```

**중요도:** 🔥🔥🔥 CRITICAL
- 워크플로우 전체가 실패하는 치명적 오류 추적
- 스테이지, 턴 수, 유저 입력 컨텍스트 저장

#### 1.2 Memory 추출 실패 에러
**위치:** [api_server.py:1171-1180](../backend/api_server.py#L1171-L1180)
```python
except Exception as e:
    print(f"⚠️ Failed to extract memories: {e}")
    # 🚨 Memory 추출 실패 에러 로깅
    try:
        SESSION_MANAGER.save_error_log(
            error_type="memory_extraction_failed",
            error_message=str(e),
            session_id=session_id,
            metadata={"user_id": user_id}
        )
    except:
        pass
```

**중요도:** 🟡 MEDIUM
- LLM 기반 장기기억 자동 추출 실패 추적
- 사용자별 장기기억 시스템 문제 파악

#### 1.3 Affinity 추적 실패 에러
**위치:** [api_server.py:1212-1221](../backend/api_server.py#L1212-L1221)
```python
except Exception as e:
    print(f"⚠️ Failed to track affinity changes: {e}")
    # 🚨 Affinity 추적 실패 에러 로깅
    try:
        SESSION_MANAGER.save_error_log(
            error_type="affinity_tracking_failed",
            error_message=str(e),
            session_id=session_id,
            metadata={"affinity_scores": new_affinity}
        )
    except:
        pass
```

**중요도:** 🟡 MEDIUM
- 친밀도 자동 추적 실패 감지
- 게임 상태 변화 감지 오류 파악

#### 1.4 Stage 추적 실패 에러
**위치:** [api_server.py:1241-1253](../backend/api_server.py#L1241-L1253)
```python
except Exception as e:
    print(f"⚠️ Failed to track stage progression: {e}")
    # 🚨 Stage 추적 실패 에러 로깅
    try:
        SESSION_MANAGER.save_error_log(
            error_type="stage_tracking_failed",
            error_message=str(e),
            session_id=session_id,
            metadata={
                "old_stage": old_stage,
                "new_stage": new_stage
            }
        )
    except:
        pass
```

**중요도:** 🟡 MEDIUM
- 스테이지 진행 자동 추적 실패 감지
- 스테이지 전환 로직 문제 파악

---

### 2. api_server.py - Performance Metrics (2개 추가)

#### 2.1 워크플로우 실행 시간
**위치:** [api_server.py:1130-1142](../backend/api_server.py#L1130-L1142)
```python
workflow_start = time.perf_counter()
result_state = workflow_instance.invoke(state)
workflow_end = time.perf_counter()
workflow_duration_ms = (workflow_end - workflow_start) * 1000.0

# 📊 Performance Metric 저장: Workflow 실행 시간
try:
    SESSION_MANAGER.save_performance_metric(
        metric_name="workflow_execution_time",
        metric_value=workflow_duration_ms,
        session_id=session_id,
        metadata={
            "stage": result_state.get("current_stage"),
            "turn_count": result_state.get("turn_count")
        }
    )
except Exception as e:
    print(f"⚠️ Failed to save performance metric: {e}")
```

**중요도:** 🔥🔥 HIGH
- 전체 워크플로우 처리 시간 측정
- 병목 구간 파악의 기준선 제공
- 스테이지별, 턴별 성능 비교 가능

#### 2.2 세션 저장 시간
**위치:** [api_server.py:1255-1272](../backend/api_server.py#L1255-L1272)
```python
# 📊 세션 저장 성능 측정
session_save_start = time.perf_counter()
SESSION_MANAGER.save(session_id, result_state)
session_save_duration_ms = (time.perf_counter() - session_save_start) * 1000.0

# 📊 Performance Metric 저장: 세션 저장 시간
try:
    SESSION_MANAGER.save_performance_metric(
        metric_name="session_save_time",
        metric_value=session_save_duration_ms,
        session_id=session_id,
        metadata={
            "stage": result_state.get("current_stage"),
            "turn_count": turn_count
        }
    )
except Exception as e:
    print(f"⚠️ Failed to save performance metric: {e}")
```

**중요도:** 🔥 HIGH
- DB 저장 작업 시간 측정
- 세션 상태 크기에 따른 성능 변화 파악
- Redis vs PostgreSQL 성능 비교 가능

#### 2.3 Router Agent 실행 시간
**위치:** [router_agent.py:540-556](../backend/src/agents/router_agent.py#L540-L556)
```python
# 📊 Performance Metric 저장: Router Agent 실행 시간
if self._session_manager:
    try:
        execution_time_ms = (time.perf_counter() - start_time) * 1000.0
        session_id = state.get("session_id")
        if session_id:
            self._session_manager.save_performance_metric(
                metric_name="router_agent_execution_time",
                metric_value=execution_time_ms,
                session_id=session_id,
                metadata={
                    "classification": result.get("classification"),
                    "next_node": result.get("next_node")
                }
            )
    except Exception as e:
        log("router", "performance_metric_save_failed", error=str(e))
```

**중요도:** 🔥 HIGH
- 토픽 분류 및 Intent 감지 총 시간 측정
- On/Off topic 판단 성능 추적
- Embedding vs LLM 분류 방식 성능 비교

#### 2.4 Parent Agent 실행 시간
**위치:** [parent_agent.py:636-658](../backend/src/agents/parent_agent.py#L636-L658)
```python
# 📊 Performance Metric 저장: Parent Agent 실행 시간
try:
    from src.session.hybrid_session_manager import HybridSessionManager
    from src.database.db_manager import DatabaseManager

    execution_time_ms = (time.perf_counter() - start_time) * 1000.0
    session_id = result.get("session_id")

    if session_id:
        db = DatabaseManager()
        session_manager = HybridSessionManager(db_manager=db)
        session_manager.save_performance_metric(
            metric_name="parent_agent_execution_time",
            metric_value=execution_time_ms,
            session_id=session_id,
            metadata={
                "stage_tag": result.get("stage_tag"),
                "current_stage": result.get("current_stage"),
                "next_node": result.get("next_node")
            }
        )
except Exception as e:
    log("parent", "performance_metric_save_failed", error=str(e))
```

**중요도:** 🔥🔥 HIGH
- 스테이지 핸들링 및 컨텍스트 구성 시간 측정
- 스테이지별 성능 비교
- Mission/Scene/Free Intent 핸들러별 성능 파악

#### 2.5 Children Agent 실행 시간
**위치:** [children_agent.py:563-585](../backend/src/agents/children_agent.py#L563-L585)
```python
# 📊 Performance Metric 저장: Children Agent 실행 시간
try:
    from src.session.hybrid_session_manager import HybridSessionManager
    from src.database.db_manager import DatabaseManager

    execution_time_ms = (time.perf_counter() - start_time) * 1000.0
    session_id = state.get("session_id")

    if session_id:
        db = DatabaseManager()
        session_manager = HybridSessionManager(db_manager=db)
        session_manager.save_performance_metric(
            metric_name="children_agent_execution_time",
            metric_value=execution_time_ms,
            session_id=session_id,
            metadata={
                "dialogue_count": len(result.get("agent_responses", [])),
                "has_more": result.get("has_more_dialogues", False),
                "next_node": result.get("next_node")
            }
        )
except Exception as e:
    log("children", "performance_metric_save_failed", error=str(e))
```

**중요도:** 🔥🔥🔥 CRITICAL
- LLM 기반 대화 생성 시간 측정
- 대화 개수에 따른 성능 영향 파악
- LLM API 호출 시간의 주요 지표

---

### 3. router_agent.py - Error Logging (1개 추가)

#### 3.1 Router LLM 호출 실패 에러
**위치:** [router_agent.py:195-222](../backend/src/agents/router_agent.py#L195-L222)

**초기화:**
```python
def __init__(self) -> None:
    self._llm_client: LLMClient = get_llm_client()
    self._embedding_client: EmbeddingClient = get_embedding_client()
    self._session_manager: Optional[HybridSessionManager] = None

    # Initialize session manager for error logging
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        self._session_manager = HybridSessionManager(db_manager=db)
    except Exception as e:
        log("router", "session_manager_init_failed", error=str(e))
```

**에러 로깅:**
```python
except Exception as exc:
    log("router", "LLM topic classification failed", error=str(exc))

    # 🚨 LLM 호출 실패 에러 로깅
    if self._session_manager:
        try:
            session_id = state.get("session_id")
            if session_id:
                self._session_manager.save_error_log(
                    error_type="router_llm_call_failed",
                    error_message=str(exc),
                    session_id=session_id,
                    metadata={
                        "agent": "router",
                        "scenario_id": scenario_id,
                        "current_stage": current_stage,
                        "user_input": text[:100] if text else None
                    }
                )
        except Exception as e:
            log("router", "error_log_save_failed", error=str(e))
```

**중요도:** 🔥 HIGH
- LLM 기반 토픽 분류 실패 추적
- 사용자 입력과 컨텍스트 정보 저장
- On/Off topic 판단 실패 원인 파악

---

### 4. children_agent.py - Error Logging (2개 추가)

#### 4.1 Children LLM 대화 생성 실패 에러
**위치:** [children_agent.py:299-319](../backend/src/agents/children_agent.py#L299-L319)

**초기화:**
```python
def __init__(self):
    """LLM 클라이언트 초기화"""
    self._llm = get_llm_client()
    self._session_manager: Optional[HybridSessionManager] = None

    # Initialize session manager for error logging
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        self._session_manager = HybridSessionManager(db_manager=db)
    except Exception as e:
        log("children", "session_manager_init_failed", error=str(e))
```

**에러 로깅:**
```python
except Exception as exc:
    log("children", f"❌ LLM call failed: {exc}")

    # 🚨 LLM 호출 실패 에러 로깅
    if self._session_manager:
        try:
            session_id = state.get("session_id")
            if session_id:
                self._session_manager.save_error_log(
                    error_type="children_llm_call_failed",
                    error_message=str(exc),
                    session_id=session_id,
                    metadata={
                        "agent": "children",
                        "stage_tag": ctx.get("stage_tag"),
                        "stage_type": ctx.get("stage_type"),
                        "speaker_pool": ctx.get("speaker_pool")
                    }
                )
        except Exception as e:
            log("children", "error_log_save_failed", error=str(e))
```

**중요도:** 🔥🔥 HIGH
- 가장 빈번한 LLM 호출 지점 (대화 생성)
- Fallback으로 beats 사용 시 품질 저하 원인 파악
- Speaker별, Stage별 실패 패턴 분석 가능

#### 4.2 Children LLM Beats 생성 실패 에러
**위치:** [children_agent.py:470-492](../backend/src/agents/children_agent.py#L470-L492)
```python
except Exception as exc:
    log("children", f"❌ LLM beats generation failed: {exc}")

    # 🚨 LLM beats 생성 실패 에러 로깅
    if self._session_manager:
        try:
            session_id = state.get("session_id")
            if session_id:
                self._session_manager.save_error_log(
                    error_type="children_llm_beats_failed",
                    error_message=str(exc),
                    session_id=session_id,
                    metadata={
                        "agent": "children",
                        "operation": "llm_beats_generation",
                        "stage_tag": stage_tag,
                        "speaker_pool": speaker_pool
                    }
                )
        except Exception as e:
            log("children", "error_log_save_failed", error=str(e))
```

**중요도:** 🟡 MEDIUM
- LLM이 실시간으로 beats를 생성하는 경우 (llm_beats=true)
- 즉흥 대화 생성 실패 추적
- Open narrative 스테이지 안정성 파악

---

### 5. api_server.py - General Logs (7개 추가)

General Logs는 프로덕션 환경에서 **주요 이벤트를 추적하고 검색 가능한 형태로 저장**하는 시스템입니다. print() 문과 달리 DB에 저장되어 SQL로 검색, 집계, 분석이 가능합니다.

#### 5.1 SessionManagerAdapter에 save_log() 메서드 추가

**위치:** [api_server.py:265-281](../backend/api_server.py#L265-L281)

```python
def save_log(self, log_level: str, log_message: str, session_id: str = None, metadata: Dict[str, Any] = None) -> None:
    """
    일반 로그 저장 (logdb.logs 테이블)
    """
    self._hybrid.save_log(log_level, log_message, session_id, metadata)
```

#### 5.2 인증/익명 사용자 로그

**위치:** [api_server.py:1020-1040](../backend/api_server.py#L1020-L1040)

```python
if current_user:
    print(f"🔐 Authenticated user: {current_user.get('username')} (ID: {user_id})")
    # 📝 General Log: 인증 사용자
    try:
        SESSION_MANAGER.save_log(
            log_level="info",
            log_message=f"Authenticated user: {current_user.get('username')}",
            session_id=None,
            metadata={"user_id": user_id, "username": current_user.get('username')}
        )
    except Exception as e:
        print(f"⚠️ Failed to save user auth log: {e}")
else:
    print(f"👤 Anonymous user: {user_name}")
    # 📝 General Log: 익명 사용자
    try:
        SESSION_MANAGER.save_log(
            log_level="info",
            log_message=f"Anonymous user: {user_name}",
            session_id=None,
            metadata={"user_name": user_name}
        )
    except Exception as e:
        print(f"⚠️ Failed to save anonymous user log: {e}")
```

**중요도:** 🔥 HIGH
- 사용자별 활동 추적
- 인증 vs 익명 사용 패턴 분석

#### 5.3 세션 생성/재사용 로그

**위치:** [api_server.py:1048-1068](../backend/api_server.py#L1048-L1068)

```python
if not session_id:
    session_id = str(uuid.uuid4())
    print(f"🆕 Creating new session: {session_id}")
    # 📝 General Log: 새 세션 생성
    try:
        SESSION_MANAGER.save_log(
            log_level="info",
            log_message="New session created",
            session_id=session_id,
            metadata={"user_id": user_id, "scenario_id": scenario_id}
        )
    except Exception as e:
        print(f"⚠️ Failed to save session creation log: {e}")
else:
    print(f"🔁 Reusing session: {session_id}")
    # 📝 General Log: 세션 재사용
    try:
        SESSION_MANAGER.save_log(
            log_level="info",
            log_message="Session reused",
            session_id=session_id,
            metadata={"user_id": user_id}
        )
    except Exception as e:
        print(f"⚠️ Failed to save session reuse log: {e}")
```

**중요도:** 🔥🔥 HIGH
- 세션 생명주기 추적
- 새 세션 vs 재사용 비율 분석

#### 5.4 사용자 메모리 로딩 로그

**위치:** [api_server.py:1115-1143](../backend/api_server.py#L1115-L1143)

```python
# 📝 General Log: 메모리 로딩 성공
try:
    SESSION_MANAGER.save_log(
        log_level="info",
        log_message=f"User memories loaded: {rel_count + pref_count + story_count + fact_count} total",
        session_id=session_id,
        metadata={
            "user_id": user_id,
            "username": current_user.get('username'),
            "relationships": rel_count,
            "preferences": pref_count,
            "story_progress": story_count,
            "facts": fact_count
        }
    )
except Exception as log_err:
    print(f"⚠️ Failed to save memory load log: {log_err}")
```

**중요도:** 🔥 HIGH
- 장기기억 시스템 활용도 추적
- 사용자별 메모리 축적 패턴 파악

#### 5.5 메모리 추출 성공 로그

**위치:** [api_server.py:1256-1268](../backend/api_server.py#L1256-L1268)

```python
# 📝 General Log: 메모리 추출 성공
try:
    SESSION_MANAGER.save_log(
        log_level="info",
        log_message=f"Extracted {saved_count} memories from conversation",
        session_id=session_id,
        metadata={
            "user_id": user_id,
            "memory_count": saved_count,
            "turn_count": result_state.get("summary_turn_count")
        }
    )
except Exception as log_err:
    print(f"⚠️ Failed to save memory extraction log: {log_err}")
```

**중요도:** 🔥 HIGH
- 자동 메모리 추출 성공률 추적
- 대화 턴 수에 따른 메모리 생성 패턴 분석

#### 5.6 친밀도 변경 로그

**위치:** [api_server.py:1314-1328](../backend/api_server.py#L1314-L1328)

```python
# 📝 General Log: 친밀도 변경
try:
    SESSION_MANAGER.save_log(
        log_level="info",
        log_message=f"Affinity changed: {character} {old_score}→{new_score}",
        session_id=session_id,
        metadata={
            "character": character,
            "old_score": old_score,
            "new_score": new_score,
            "change": change_amount,
            "turn_count": turn_count
        }
    )
except Exception as log_err:
    print(f"⚠️ Failed to save affinity log: {log_err}")
```

**중요도:** 🟡 MEDIUM
- 캐릭터별 친밀도 변화 추적
- 게임 밸런스 분석 데이터

#### 5.7 스테이지 전환 로그

**위치:** [api_server.py:1360-1373](../backend/api_server.py#L1360-L1373)

```python
# 📝 General Log: 스테이지 전환
try:
    SESSION_MANAGER.save_log(
        log_level="info",
        log_message=f"Stage changed: {old_stage}→{new_stage}",
        session_id=session_id,
        metadata={
            "old_stage": old_stage,
            "new_stage": new_stage,
            "stage_order": stage_order,
            "turn_count": turn_count
        }
    )
except Exception as log_err:
    print(f"⚠️ Failed to save stage transition log: {log_err}")
```

**중요도:** 🔥🔥 HIGH
- 스토리 진행 흐름 추적
- 스테이지별 소요 시간 분석

---

## 📊 통합 결과 요약

### Error Logging

| 파일 | 에러 타입 | 중요도 | 설명 |
|------|----------|--------|------|
| api_server.py | workflow_execution_failed | 🔥🔥🔥 | 워크플로우 전체 실패 |
| api_server.py | memory_extraction_failed | 🟡 | 장기기억 자동 추출 실패 |
| api_server.py | affinity_tracking_failed | 🟡 | 친밀도 자동 추적 실패 |
| api_server.py | stage_tracking_failed | 🟡 | 스테이지 진행 추적 실패 |
| router_agent.py | router_llm_call_failed | 🔥 | 토픽 분류 LLM 호출 실패 |
| children_agent.py | children_llm_call_failed | 🔥🔥 | 대화 생성 LLM 호출 실패 |
| children_agent.py | children_llm_beats_failed | 🟡 | Beats 생성 LLM 호출 실패 |

**Total:** 7개 에러 로깅 포인트 추가

### Performance Metrics

| 파일 | 메트릭 이름 | 중요도 | 설명 |
|------|------------|--------|------|
| api_server.py | workflow_execution_time | 🔥🔥 | 워크플로우 전체 실행 시간 |
| api_server.py | session_save_time | 🔥 | 세션 DB 저장 시간 |
| router_agent.py | router_agent_execution_time | 🔥 | Router Agent 실행 시간 |
| parent_agent.py | parent_agent_execution_time | 🔥🔥 | Parent Agent 실행 시간 |
| children_agent.py | children_agent_execution_time | 🔥🔥🔥 | Children Agent 실행 시간 |

**Total:** 5개 성능 메트릭 추가

### General Logs

| 파일 | 로그 이벤트 | 중요도 | 설명 |
|------|------------|--------|------|
| api_server.py | Authenticated/Anonymous user | 🔥 | 사용자 인증 상태 |
| api_server.py | New session created | 🔥🔥 | 세션 생성 |
| api_server.py | Session reused | 🔥🔥 | 세션 재사용 |
| api_server.py | User memories loaded | 🔥 | 장기기억 로딩 |
| api_server.py | Extracted memories | 🔥 | 메모리 추출 성공 |
| api_server.py | Affinity changed | 🟡 | 친밀도 변경 |
| api_server.py | Stage changed | 🔥🔥 | 스테이지 전환 |

**Total:** 7개 General Logs 추가

---

## 🎯 실전 활용 방법

### 1. 에러 모니터링 쿼리
```sql
-- 최근 1시간 동안 발생한 에러 유형별 통계
SELECT
    error_type,
    COUNT(*) as count,
    AVG(LENGTH(error_message)) as avg_msg_length
FROM logdb.error_logs
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY error_type
ORDER BY count DESC;

-- 특정 세션의 모든 에러 로그
SELECT
    timestamp,
    error_type,
    error_message,
    metadata
FROM logdb.error_logs
WHERE session_id = 'xxx'
ORDER BY timestamp;

-- LLM 호출 실패가 가장 많은 스테이지
SELECT
    metadata->>'stage_tag' as stage,
    COUNT(*) as llm_failures
FROM logdb.error_logs
WHERE error_type LIKE '%llm%failed'
GROUP BY stage
ORDER BY llm_failures DESC
LIMIT 10;
```

### 2. 성능 분석 쿼리
```sql
-- 워크플로우 실행 시간 평균 (스테이지별)
SELECT
    metadata->>'stage' as stage,
    AVG(metric_value) as avg_ms,
    MAX(metric_value) as max_ms,
    MIN(metric_value) as min_ms,
    COUNT(*) as count
FROM logdb.performance_metrics
WHERE metric_name = 'workflow_execution_time'
GROUP BY stage
ORDER BY avg_ms DESC;

-- 세션 저장 시간 추세 (시간대별)
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(metric_value) as avg_save_time_ms,
    COUNT(*) as session_count
FROM logdb.performance_metrics
WHERE metric_name = 'session_save_time'
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;

-- 특정 임계값 초과 세션 찾기 (느린 워크플로우)
SELECT
    session_id,
    metric_value as duration_ms,
    metadata->>'stage' as stage,
    metadata->>'turn_count' as turn
FROM logdb.performance_metrics
WHERE metric_name = 'workflow_execution_time'
  AND metric_value > 3000  -- 3초 초과
ORDER BY metric_value DESC
LIMIT 20;
```

### 3. 알림 설정 제안
```python
# 프로덕션 모니터링 예시
def check_system_health():
    """시스템 헬스 체크 - 5분마다 실행"""

    # 1. 최근 5분간 워크플로우 실패율 체크
    workflow_failures = db.execute("""
        SELECT COUNT(*) FROM logdb.error_logs
        WHERE error_type = 'workflow_execution_failed'
        AND timestamp > NOW() - INTERVAL '5 minutes'
    """).fetchone()[0]

    if workflow_failures > 5:
        send_alert("CRITICAL: 5+ workflow failures in 5 minutes")

    # 2. LLM 호출 실패율 체크
    llm_failures = db.execute("""
        SELECT COUNT(*) FROM logdb.error_logs
        WHERE error_type LIKE '%llm%failed'
        AND timestamp > NOW() - INTERVAL '5 minutes'
    """).fetchone()[0]

    if llm_failures > 10:
        send_alert("WARNING: High LLM failure rate")

    # 3. 평균 응답 시간 체크
    avg_time = db.execute("""
        SELECT AVG(metric_value) FROM logdb.performance_metrics
        WHERE metric_name = 'workflow_execution_time'
        AND timestamp > NOW() - INTERVAL '5 minutes'
    """).fetchone()[0]

    if avg_time > 5000:  # 5초 초과
        send_alert("WARNING: Average response time > 5s")
```

### 4. General Logs 분석 쿼리

```sql
-- 세션 생성 vs 재사용 비율
SELECT
    log_message,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM logdb.logs
WHERE log_message IN ('New session created', 'Session reused')
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY log_message;

-- 사용자별 메모리 로딩 통계
SELECT
    metadata->>'username' as username,
    COUNT(*) as load_count,
    AVG((metadata->>'relationships')::int +
        (metadata->>'preferences')::int +
        (metadata->>'story_progress')::int +
        (metadata->>'facts')::int) as avg_total_memories
FROM logdb.logs
WHERE log_message LIKE 'User memories loaded%'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY username
ORDER BY load_count DESC
LIMIT 10;

-- 친밀도 변화 추적 (캐릭터별)
SELECT
    metadata->>'character' as character,
    COUNT(*) as change_count,
    AVG((metadata->>'change')::int) as avg_change,
    MAX((metadata->>'new_score')::int) as max_score
FROM logdb.logs
WHERE log_message LIKE 'Affinity changed%'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY character
ORDER BY change_count DESC;

-- 스테이지별 진입 횟수
SELECT
    metadata->>'new_stage' as stage,
    COUNT(*) as entry_count,
    AVG((metadata->>'turn_count')::int) as avg_turn_at_entry
FROM logdb.logs
WHERE log_message LIKE 'Stage changed%'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY stage
ORDER BY entry_count DESC;

-- 인증 vs 익명 사용자 비율
SELECT
    CASE
        WHEN log_message LIKE 'Authenticated user%' THEN 'Authenticated'
        WHEN log_message LIKE 'Anonymous user%' THEN 'Anonymous'
    END as user_type,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM logdb.logs
WHERE log_message LIKE '%user%'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY user_type;
```

---

## 🔄 다음 단계

### ⏳ 남은 작업 (우선순위 순)

#### 1. Password Reset 테스트 (LOW Priority)
- SMTP 설정 구성
- 전체 플로우 테스트 (요청 → 이메일 → 토큰 → 리셋)

**예상 작업량:** 1시간

---

## 📈 기대 효과

### 1. 프로덕션 안정성 향상
- ✅ 실시간 에러 감지 및 알림
- ✅ 에러 발생 컨텍스트 완벽 보존 (session, stage, user input)
- ✅ 에러 패턴 분석으로 근본 원인 파악

### 2. 성능 최적화 기반 확보
- ✅ 병목 구간 정확한 식별
- ✅ 스테이지/턴별 성능 비교
- ✅ DB 작업 최적화 지표 확보

### 3. 데이터 기반 의사결정
- ✅ 어떤 스테이지에서 LLM이 가장 많이 실패하는지
- ✅ 어떤 시간대에 시스템 부하가 높은지
- ✅ 사용자 경험에 영향을 주는 bottleneck 파악

---

## ✅ 체크리스트

- [x] api_server.py 에러 로깅 (5개)
- [x] api_server.py 성능 메트릭 (2개)
- [x] router_agent.py 에러 로깅 (1개)
- [x] children_agent.py 에러 로깅 (2개)
- [x] HybridSessionManager 통합 (agents)
- [x] router_agent.py 성능 메트릭 (1개)
- [x] parent_agent.py 성능 메트릭 (1개)
- [x] children_agent.py 성능 메트릭 (1개)
- [x] SessionManagerAdapter에 save_log() 추가
- [x] General Logs 통합 (7개)
- [x] General Logs 실전 쿼리 예시 작성
- [x] 문서화 완료
- [ ] Password Reset 테스트

---

**작성일:** 2025-10-31
**작성자:** Claude (Phase 5 - Production Readiness)
**관련 문서:** [27_missing_integrations_analysis.md](./27_missing_integrations_analysis.md)
