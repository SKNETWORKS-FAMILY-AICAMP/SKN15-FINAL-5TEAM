# Project Structure Overview

이 문서는 백엔드와 프론트엔드 전체 흐름을 한눈에 이해할 수 있도록 각 디렉터리/파일의 역할을 요약합니다.  
깊이 2~3단계까지만 표시하고, 이미지 폴더는 대표 예시만 기재했습니다.

---

## Backend (`backend/`)

FastAPI 기반 API 서버와 도메인 로직이 위치합니다.

````text
backend/
├── src/
│   ├── api/                  # FastAPI 엔트리 계층
│   │   ├── middleware/       # 레이트 리미팅 등 미들웨어
│   │   ├── routes/           # REST 엔드포인트 모음
│   │   ├── dependencies/     # FastAPI Depends 팩토리
│   │   ├── schemas/          # Pydantic 모델
│   │   ├── security/         # JWT 유틸
│   │   └── server.py         # FastAPI 앱 초기화
│   │
│   ├── core/                 # 공용 코어 로직
│   │   ├── config/           # YAML 기반 설정 (settings.yaml, prompts.yaml)
│   │   ├── utils/            # Config 로더, LLM 클라이언트 등 유틸
│   │   ├── graph_state.py    # LangGraph 상태 정의
│   │   └── workflow.py       # LangGraph 워크플로우 구성
│   │
│   ├── domain/               # 비즈니스 도메인 계층
│   │   ├── agents/           # LLM 에이전트(Router, Parent, Dialogue ...)
│   │   ├── handlers/         # 스테이지/미션 등 세부 처리 로직
│   │   ├── services/         # Generation / Evaluation 등 서비스 모듈
│   │   └── models/           # 도메인 모델 정의
│   │
│   └── infrastructure/       # DB/캐시/LLM Provider 등 외부 연동
│       ├── database/         # Postgres 세션/로그 저장소
│       ├── cache/            # Redis 캐시 매니저
│       ├── llm/              # OpenAI 등 LLM provider
│       └── shared/           # DI 컨테이너 등 공용 인프라
│
├── Refactoring_backend.md
└── REFACTORING_SUMMARY.md
````

### Backend Flow (요약)
1. `src/api/server.py`에서 FastAPI 앱을 초기화하고 레이트 리미팅/라우터를 등록합니다.
2. HTTP 요청은 `src/api/routes/*` 엔드포인트로 유입됩니다.
3. 각 라우트는 `dependencies/api_deps.py`를 통해 DB/세션 매니저/워크플로우를 주입받습니다.
4. 비즈니스 로직은 `domain/agents` 및 `domain/services`에서 처리되며, LangGraph 워크플로우(`core/workflow.py`)가 에이전트 실행을 orchestrate 합니다.
5. 상태 저장·로그 적재는 `infrastructure/database`와 `core/utils/tools/training_logger.py`가 담당합니다.

---

## Frontend (`front/`)

Vite + React SPA. 백엔드 API와 연동해 챗 UI를 제공합니다.

````text
front/
├── public/
│   ├── images/
│   │   ├── backgrounds/      # 시나리오별 배경 이미지
│   │   └── kimechatlogo.png  # 대표 예시
│   └── Kime_Chat_Logo.png
│
├── src/
│   ├── components/           # Chat 인터페이스, 모달 등 UI 컴포넌트
│   ├── pages/                # 라우트 컴포넌트(Home, Chat, ...)
│   ├── services/             # 백엔드 API 통신 (`api.ts`)
│   ├── contexts/             # 전역 상태(AppContext)
│   ├── hooks/                # 커스텀 훅(배경, 효과음 등)
│   ├── utils/                # 토큰/axios 유틸
│   ├── App.tsx               # 라우팅 엔트리
│   └── main.tsx              # ReactDOM 렌더링
│
├── package.json
├── vite.config.ts
└── 기타 설정 파일(tsconfig, tailwind 등)
````

### Frontend Flow (요약)
1. `main.tsx`에서 `App.tsx`를 렌더링하며 `react-router-dom`으로 페이지를 관리합니다.
2. `services/api.ts`는 JWT 토큰을 포함해 백엔드 `/api/*` 엔드포인트와 통신합니다.
3. `components/ChatInterface.tsx`가 SSE 스트림을 처리하며 대화 UI를 구성합니다.
4. 이미지/사운드·설정 값은 `config/`와 `hooks/`를 통해 로드됩니다.

---