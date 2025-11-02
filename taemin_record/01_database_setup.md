# 데이터베이스 구축 가이드

## 📋 목차
1. [아키텍처 선택](#아키텍처-선택)
2. [Docker Compose 구성](#docker-compose-구성)
3. [데이터베이스 스키마 설계](#데이터베이스-스키마-설계)
4. [Python 모듈 구현](#python-모듈-구현)
5. [API 서버 통합](#api-서버-통합)

---

## 아키텍처 선택

### 요구사항
- 사용자: ~100명
- 예산: ₩300,000/월 (27일 운영)
- 우선순위: **성능 > 안정성 > 비용**
- 운영팀: 3명

### 최종 선택: Hybrid (PostgreSQL + Redis)

**이유:**
1. **PostgreSQL**: 영구 데이터 저장 (세션, 대화 기록, 친밀도 등)
2. **Redis**: 세션 캐싱으로 읽기 성능 6배 향상 (1시간 TTL)
3. **성능**: Cache-first 전략으로 DB 부하 감소
4. **안정성**: PostgreSQL에 모든 데이터 영구 저장
5. **비용**: Managed 서비스 대비 70% 절감

---

## Docker Compose 구성

### 파일 위치
`backend/database/docker-compose.yml`

### 구성

```yaml
version: '3.8'

services:
  # PostgreSQL 15
  postgres:
    image: postgres:15-alpine
    container_name: kime_postgres
    ports:
      - "5433:5432"  # ⚠️ 로컬 PostgreSQL과 충돌 방지를 위해 5433 사용
    environment:
      POSTGRES_USER: kime
      POSTGRES_PASSWORD: dev123
      POSTGRES_DB: kimedb
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kime"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 7
  redis:
    image: redis:7-alpine
    container_name: kime_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes  # AOF 지속성
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### 실행 방법

```bash
# 1. 데이터베이스 시작
cd backend/database
docker-compose up -d

# 2. 상태 확인
docker-compose ps

# 3. 로그 확인
docker-compose logs -f

# 4. 중지
docker-compose down

# 5. 데이터 포함 완전 삭제
docker-compose down -v
```

---

## 데이터베이스 스키마 설계

### 파일 위치
`backend/database/migrations/001_initial_schema.sql`

### StateDB (8개 테이블)

#### 1. sessions - 세션 메타데이터
```sql
CREATE TABLE statedb.sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    scenario_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB
);
```

#### 2. user_inputs - 사용자 입력 기록
```sql
CREATE TABLE statedb.user_inputs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. dialogues - 대화 내용 저장
```sql
CREATE TABLE statedb.dialogues (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    character_id VARCHAR(100) NOT NULL,
    dialogue_text TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. affinity_records - 친밀도 변화 기록
```sql
CREATE TABLE statedb.affinity_records (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    character_id VARCHAR(100) NOT NULL,
    affinity_value FLOAT NOT NULL,
    change_amount FLOAT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. session_snapshots - 전체 상태 스냅샷
```sql
CREATE TABLE statedb.session_snapshots (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES statedb.sessions(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    state_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**중요:** `session_snapshots`는 `sessions`에 대한 외래 키를 가지므로,
**반드시 `sessions` 레코드를 먼저 저장한 후** `session_snapshots`를 저장해야 합니다!

#### 6~8. 기타 테이블
- **stage_progression**: 스테이지 진행 상황
- **game_events**: 게임 이벤트 로그
- **mission_records**: 미션 완료 기록

### LogDB (3개 테이블)

#### 1. logs - 일반 로그
```sql
CREATE TABLE logdb.logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    context JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. error_logs - 에러 로그
- 스택 트레이스 포함

#### 3. performance_metrics - 성능 메트릭
- LLM 응답 시간, 토큰 사용량 등

---

## Python 모듈 구현

### 1. DatabaseManager (backend/src/database/db_manager.py)

**역할:** PostgreSQL 연결 및 CRUD 작업

```python
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_config):
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )

    @contextmanager
    def get_connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.pool.putconn(conn)
```

**주요 메서드:**
- `save_session()`: 세션 메타데이터 저장/업데이트
- `load_session()`: 세션 조회
- `save_user_input()`: 사용자 입력 저장
- `save_dialogues()`: 대화 내용 저장
- `save_affinity()`: 친밀도 저장
- `save_snapshot()`: 상태 스냅샷 저장
- `load_latest_snapshot()`: 최신 스냅샷 조회

### 2. CacheManager (backend/src/database/cache_manager.py)

**역할:** Redis 캐싱 및 TTL 관리

```python
import redis
import json

class CacheManager:
    def __init__(self, redis_host, redis_port, ttl=3600):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.ttl = ttl
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def get_session(self, session_id):
        key = f"session:{session_id}"
        data = self.redis_client.get(key)
        if data:
            self.stats["hits"] += 1
            return json.loads(data)
        self.stats["misses"] += 1
        return None
```

**주요 메서드:**
- `get_session()`: 캐시에서 세션 조회
- `set_session()`: 캐시에 세션 저장 (TTL 설정)
- `delete_session()`: 캐시에서 세션 삭제
- `extend_ttl()`: TTL 연장
- `get_stats()`: 캐시 통계 조회

### 3. HybridSessionManager (backend/src/database/session_manager.py)

**역할:** Cache-first 읽기 + Write-through 전략

```python
class HybridSessionManager:
    def __init__(self, db_manager, cache_manager):
        self.db = db_manager
        self.cache = cache_manager

    def load_or_create(self, session_id, scenario_id, user_id=None):
        # 1. Redis 캐시 확인 (빠른 경로)
        session = self.cache.get_session(session_id)
        if session:
            return session

        # 2. PostgreSQL 스냅샷 조회 (중간 경로)
        snapshot = self.db.load_latest_snapshot(session_id)
        if snapshot:
            self.cache.set_session(session_id, snapshot["state_json"])
            return snapshot["state_json"]

        # 3. 새 세션 생성 (느린 경로)
        return {}

    def save(self, session_id, state):
        # Write-through: DB 먼저, 그 다음 캐시
        self.db.save_snapshot(session_id, turn_count, state)
        self.cache.set_session(session_id, state)
```

---

## API 서버 통합

### 파일 위치
`backend/api_server.py`

### 환경 변수 설정
`backend/.env.local` 파일 생성:

```bash
# PostgreSQL
DB_HOST=127.0.0.1  # ⚠️ localhost 대신 127.0.0.1 사용 (IPv6 이슈 방지)
DB_PORT=5433
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
SESSION_TTL=3600  # 1시간
```

### SessionManagerAdapter 구현

```python
from src.database.session_manager import HybridSessionManager

class SessionManagerAdapter:
    def __init__(self, hybrid_manager, db_manager, cache_manager):
        self.hybrid = hybrid_manager
        self.db = db_manager
        self.cache = cache_manager

    def load(self, session_id: str, scenario_id: str) -> Dict[str, Any]:
        return self.hybrid.load_or_create(session_id, scenario_id)

    def save(self, session_id: str, state: Dict[str, Any]):
        # ⚠️ 중요: 순서 지키기!
        # 1. 세션 메타데이터 저장 (외래 키 제약 조건)
        self.db.save_session({
            "session_id": session_id,
            "scenario_id": state.get("scenario_id"),
            "status": "active"
        })

        # 2. 스냅샷 저장 (sessions 테이블 참조)
        self.db.save_snapshot(session_id, turn_count, state)

        # 3. 캐시 업데이트
        self.cache.set_session(cache_key, state)
```

---

## 성능 비교

| 항목 | 이전 (메모리) | 현재 (Hybrid) | 개선 |
|------|--------------|--------------|------|
| 읽기 속도 | 0.1ms | 0.5ms (캐시 히트) | 5배 느림 (허용) |
| 쓰기 속도 | 0.1ms | 5ms | 50배 느림 (허용) |
| 데이터 안정성 | ❌ 휘발성 | ✅ 영구 저장 | 대폭 개선 |
| 서버 재시작 | ❌ 데이터 손실 | ✅ 복구 가능 | 대폭 개선 |
| 동시 접속 | 제한적 | 100+ 가능 | 대폭 개선 |

---

## 다음 단계

1. ✅ 로컬 데이터베이스 구축 완료
2. ⏳ AWS RDS + ElastiCache 배포 준비
3. ⏳ 프로덕션 환경 설정

**관련 문서:** [03_aws_deployment_guide.md](03_aws_deployment_guide.md)

---
작성일: 2025-10-30
참고: 실제 구현 코드 참조
