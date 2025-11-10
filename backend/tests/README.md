# KIME Chat Backend - Tests

이 디렉토리는 KIME Chat Backend API의 테스트 스위트입니다.

## 📁 디렉토리 구조

```
tests/
├── e2e/                    # End-to-End 테스트
│   ├── conftest.py         # E2E 테스트 fixtures
│   ├── test_auth_e2e.py    # 인증 플로우 테스트
│   ├── test_scenarios_e2e.py  # 시나리오 플로우 테스트
│   └── test_sessions_e2e.py   # 세션 플로우 테스트
└── README.md               # This file
```

## 🧪 테스트 종류

### E2E (End-to-End) Tests

전체 API 워크플로우를 테스트합니다:
- **Auth Flow**: 회원가입 → 로그인 → 프로필 조회
- **Scenarios Flow**: 목록 조회 → 상세 → 좋아요 → 댓글
- **Sessions Flow**: 세션 생성 → 조회 → 삭제

## 🚀 테스트 실행

### 필수 패키지 설치

```bash
pip install pytest pytest-asyncio httpx
```

### 전체 테스트 실행

```bash
# 백엔드 디렉토리에서 실행
cd /Users/jtm427/Desktop/workspace/backend

# 모든 테스트 실행
pytest

# E2E 테스트만 실행
pytest tests/e2e/

# 특정 테스트 파일 실행
pytest tests/e2e/test_auth_e2e.py

# 특정 테스트 함수 실행
pytest tests/e2e/test_auth_e2e.py::test_auth_flow

# 상세 출력 (verbose)
pytest -v

# 실패 시 즉시 중단
pytest -x

# 마커로 필터링
pytest -m e2e
```

## 📋 테스트 전제 조건

### 1. 데이터베이스 설정

E2E 테스트는 실제 PostgreSQL 데이터베이스에 연결합니다:
- `.env` 파일에 올바른 `DATABASE_URL` 설정 필요
- 테스트 실행 시 테이블이 자동으로 생성/삭제됩니다

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123
```

### 2. OpenAI API 키 (이미지 생성 테스트용)

```env
OPENAI_API_KEY=your-api-key-here
```

### 3. API 서버 실행 불필요

E2E 테스트는 ASGI transport를 사용하므로 별도로 API 서버를 실행할 필요 없습니다.

## 🔧 Fixtures

### `conftest.py`에서 제공하는 공통 fixtures:

- **`client`**: HTTP 클라이언트 (AsyncClient)
- **`db_session`**: 데이터베이스 세션 (자동 롤백)
- **`auth_headers`**: 인증 헤더 (테스트 사용자 자동 생성)
- **`test_user_id`**: 테스트 사용자 ID
- **`test_scenario_id`**: 테스트 시나리오 ID
- **`test_session_id`**: 테스트 세션 ID

## 📊 테스트 커버리지

현재 E2E 테스트 커버리지:

### ✅ 구현된 테스트

1. **Auth (인증)**
   - [x] 전체 인증 플로우 (회원가입 → 로그인 → 프로필)
   - [x] 잘못된 자격증명 로그인 실패
   - [x] 인증 없이 프로필 조회 실패

2. **Scenarios (시나리오)**
   - [x] 시나리오 목록 조회
   - [x] 시나리오 상세 조회
   - [x] 시나리오 좋아요
   - [x] 댓글 작성 및 조회
   - [x] 존재하지 않는 시나리오 404

3. **Sessions (세션)**
   - [x] 세션 생성, 조회, 삭제
   - [x] 세션 목록 조회
   - [x] 잘못된 시나리오로 세션 생성 실패

### 🔮 향후 추가 예정

- [ ] Chat (채팅) E2E 테스트
- [ ] Gallery (갤러리) E2E 테스트
- [ ] Users (사용자) E2E 테스트
- [ ] Unit 테스트 (Services, Agents, Repositories)
- [ ] Integration 테스트

## 💡 테스트 작성 가이드

### 새로운 E2E 테스트 추가

1. `tests/e2e/` 디렉토리에 `test_<feature>_e2e.py` 파일 생성
2. `conftest.py`의 fixtures 활용
3. pytest-asyncio 사용 (`@pytest.mark.asyncio`)
4. 전체 사용자 플로우 시뮬레이션

예시:

```python
import pytest
from httpx import AsyncClient
from typing import Dict

@pytest.mark.asyncio
async def test_my_feature_flow(
    client: AsyncClient,
    auth_headers: Dict[str, str]
):
    \"\"\"
    E2E: My feature complete flow
    1. Step 1
    2. Step 2
    3. Step 3
    \"\"\"
    # 1. Step 1
    response1 = await client.get("/api/feature", headers=auth_headers)
    assert response1.status_code == 200

    # 2. Step 2
    response2 = await client.post(
        "/api/feature",
        json={"data": "value"},
        headers=auth_headers
    )
    assert response2.status_code == 201

    # 3. Step 3
    response3 = await client.get("/api/feature/result", headers=auth_headers)
    assert response3.status_code == 200
```

## 🐛 트러블슈팅

### 데이터베이스 연결 실패

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**해결**: PostgreSQL이 실행 중인지 확인하고 `.env` 설정을 검증하세요.

### 테이블이 없음 에러

```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

**해결**: 테스트는 자동으로 테이블을 생성합니다. 수동으로 마이그레이션을 실행할 필요 없습니다.

### OpenAI API 키 없음

```
ValueError: OPENAI_API_KEY가 설정되지 않았습니다
```

**해결**: `.env` 파일에 `OPENAI_API_KEY`를 추가하세요.

## 📚 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [HTTPX Async Client](https://www.python-httpx.org/async/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
