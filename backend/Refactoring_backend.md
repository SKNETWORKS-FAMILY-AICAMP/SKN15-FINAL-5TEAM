# KIME Backend 개요

이 프로젝트는 FastAPI 기반 챗봇 백엔드로, `backend/api`는 API 계층을, `backend/domain`은 비즈니스 도메인 로직을 담당합니다. 아래는 두 주요 디렉터리의 구조와 핵심 기능 요약입니다.

## 디렉터리 구조

```text
backend/
├─ api/                  # FastAPI 애플리케이션 계층
│  ├─ server.py          # 앱 초기화 및 라우터 등록
│  ├─ dependencies/      # FastAPI Depends 팩토리 (DB, 인증, 워크플로 등)
│  ├─ routes/            # 엔드포인트 모듈 (auth, chat, user, scenario, 등)
│  ├─ schemas/           # 요청·응답 Pydantic 모델 정의
│  └─ security/          # JWT 등 API 보안 유틸
└─ domain/               # 핵심 비즈니스 로직
   ├─ agents/            # 대화 에이전트 구성 요소
   ├─ handlers/          # 에이전트/서비스 간 orchestration
   ├─ models/            # 도메인 데이터 모델
   └─ services/          # 분류, 생성, 평가 등 세부 서비스 모듈
```

## 주요 기능

- **인증/보안**: `api/security/jwt_utils.py`와 `api/dependencies/auth_deps.py`가 JWT 발급·검증, 인증 Depends 제공.
- **챗봇 라우팅**: `api/routes/chat_routes.py`가 LangGraph 워크플로 기반 대화 흐름 처리, SSE 스트리밍 지원.
- **사용자 관리**: `api/routes/user_routes.py`에서 크레딧, 경험치, 장비, 시나리오 진행도 API 제공.
- **시나리오/메모리/세션**: 각 도메인별 라우트와 `domain/services`의 로직을 활용해 콘텐츠 조회·추적 기능 구현.
- **모니터링/리더보드**: `api/routes/monitoring_routes.py`, `leaderboard_routes.py`로 운영 지표와 경험치 순위 노출.
- **도메인 서비스 레이어**: `domain/services/*`가 대화 요약, 메모리 추출, 분류, 검증 등 모델/비즈니스 연산 담당.

필요한 세부 로직은 `backend/api` 라우터에서 의존성을 주입받아 `backend/domain` 서비스를 호출하는 구조로 구성되어 있습니다.
