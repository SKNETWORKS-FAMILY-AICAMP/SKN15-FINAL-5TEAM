# Docker Compatibility - 4-Layer Architecture

## 변경 사항 요약

리팩토링된 4-layer 아키텍처가 `docker-compose up` 명령으로 정상 작동하도록 Docker 설정을 업데이트했습니다.

## 주요 변경사항

### 1. Dockerfile 수정

**변경 전:**
```dockerfile
CMD ["python", "api_server.py"]
```

**변경 후:**
```dockerfile
# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Run the application (new 4-layer architecture)
CMD ["python", "-m", "src.application.server"]
```

**이유:**
- 기존 `api_server.py`는 삭제된 `src.api` 모듈을 참조
- 새로운 Application 레이어의 `src/application/server.py`가 올바른 진입점
- `PYTHONPATH=/app` 설정으로 `from src.*` 형태의 절대 import 지원

### 2. Application Server 수정 (src/application/server.py)

**Import 경로 수정:**
```python
# 변경 전 (잘못된 경로)
from src.middleware import setup_rate_limiting
from api.routes import system_routes
from api.dependencies.api_deps import cleanup_dependencies

# 변경 후 (4-layer 구조)
from src.application.middleware.rate_limiter import setup_rate_limiting
from src.application.routes import system_routes
from src.application.dependencies.api_deps import cleanup_dependencies
```

**Uvicorn 실행 경로 수정:**
```python
uvicorn.run(
    "src.application.server:app",  # 4-layer 아키텍처에 맞게 수정
    host=os.getenv("API_HOST", "0.0.0.0"),
    port=int(os.getenv("API_PORT", "8000")),
    ...
)
```

### 3. 기존 api_server.py 처리

기존 파일을 삭제하는 대신 **deprecated 경고**로 대체:
- 실수로 실행 시 명확한 에러 메시지 출력
- 새로운 진입점 안내
- 이후 정리 시 쉽게 식별 가능

## Docker 실행 방법

### 개발 환경
```bash
# Backend 디렉토리에서 직접 실행
cd backend
python -m src.application.server

# 또는 Docker Compose로 전체 스택 실행
cd ..
docker-compose up
```

### 프로덕션 환경
```bash
docker-compose -f docker-compose.yml up -d
```

## 디렉토리 구조

```
backend/
├── api_server.py              # ⚠️ DEPRECATED (경고 메시지만 출력)
├── Dockerfile                 # ✅ 수정됨 (새 진입점 사용)
├── docker-compose.yml         # ✅ 변경 없음 (기존 설정 호환)
└── src/
    ├── application/           # Application Layer (API)
    │   ├── server.py          # ✅ 새 진입점
    │   ├── routes/            # API 라우터
    │   ├── dependencies/      # FastAPI Dependencies
    │   ├── middleware/        # Rate limiting 등
    │   └── security/          # JWT 처리
    ├── domain/                # Domain Layer (비즈니스 로직)
    │   ├── use_cases/         # Use Case 패턴
    │   ├── services/          # Domain 서비스
    │   └── agents/            # AI 에이전트
    ├── infrastructure/        # Infrastructure Layer (구현)
    │   ├── database/          # PostgreSQL 구현
    │   ├── cache/             # Redis 구현
    │   └── llm/               # LLM Provider 구현
    └── core/                  # Core Layer (인터페이스)
        ├── interfaces/        # Repository 인터페이스
        ├── exceptions/        # 도메인 예외
        └── config/            # 설정
```

## Import 경로 규칙

### Application Layer에서
```python
# 같은 레이어 내 상대 import
from ..middleware.rate_limiter import setup_rate_limiting
from ..security.jwt_utils import create_access_token

# 하위 레이어 절대 import
from src.infrastructure.database.db_manager import DatabaseManager
from src.domain.use_cases.auth.login_user import LoginUserUseCase
```

### Domain Layer에서
```python
# Core 인터페이스 import (의존성 역전)
from core.interfaces.repositories.user_repository import IUserRepository
from core.exceptions.domain_exceptions import ValidationError

# Infrastructure 구현은 DI Container를 통해 주입받음
# ❌ 직접 import 금지: from src.infrastructure.database.repositories...
```

### Infrastructure Layer에서
```python
# Core 인터페이스 구현
from core.interfaces.repositories.user_repository import IUserRepository
from psycopg2.extras import RealDictCursor
```

## 검증 방법

### 1. Docker 빌드 테스트
```bash
cd backend
docker build -t kime-backend:test .
```

### 2. Docker Compose 실행 테스트
```bash
docker-compose up backend
```

### 3. Health Check 확인
```bash
curl http://localhost:8000/health
```

예상 응답:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-07T..."
}
```

### 4. API 문서 확인
브라우저에서 http://localhost:8000/docs 접속

## 트러블슈팅

### "ModuleNotFoundError: No module named 'src'" 에러
**원인:** PYTHONPATH가 설정되지 않음
**해결:** Dockerfile에 `ENV PYTHONPATH=/app:$PYTHONPATH` 추가됨

### "No module named 'api'" 에러
**원인:** 기존 `api_server.py` 실행 중
**해결:** Dockerfile CMD를 `python -m src.application.server`로 변경

### Routes에서 import 에러
**원인:** Application layer routes가 상대/절대 경로 혼용
**해결:** 현재 fallback import로 처리됨 (추후 정리 필요)

## 다음 단계 (선택사항)

1. **Routes 파일 Import 정리**
   - 현재: 다중 try/except fallback
   - 목표: 단일 절대 경로로 통일

2. **api_server.py 삭제**
   - deprecated 경고 충분히 표시 후 제거

3. **Import Linter 추가**
   - 계층 간 의존성 규칙 자동 검증
   - CI/CD 파이프라인에 통합

## 참고 문서

- [REFACTORING_COMPLETE.md](./REFACTORING_COMPLETE.md) - Sprint 1-3 전체 요약
- [ARCHITECTURE_PERFECT_4LAYER.md](../ARCHITECTURE_PERFECT_4LAYER.md) - 100점 아키텍처 설계
- [docker-compose.yml](../docker-compose.yml) - 전체 스택 구성
