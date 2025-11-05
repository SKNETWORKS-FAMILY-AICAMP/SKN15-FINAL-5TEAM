# 🎮 Kime Chat

귀멸의 칼날 인터랙티브 챗봇 프로젝트

---

## 🚀 Quick Start

### 1. 백엔드 실행

```bash
cd backend

# Python 환경 활성화 (conda 사용 시)
conda activate openai

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python api_server.py
```

**서버 실행 확인**: http://localhost:8000/docs

### 2. 프론트엔드 실행

```bash
cd front

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

**프론트엔드 접속**: http://localhost:3000 (또는 3001)

---

## ⚙️ 환경 설정

### Backend 환경 변수

`backend/.env` 파일 생성:

```env
# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here

# Database
DB_HOST=localhost
DB_PORT=5433
DB_NAME=kimedb
DB_USER=kime
DB_PASSWORD=dev123

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Frontend 환경 변수

`front/.env` 파일 생성:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📊 프로젝트 구조

```
workspace/
├── backend/           # FastAPI 백엔드
│   ├── api_server.py  # 메인 서버
│   ├── src/
│   │   ├── agents/    # LangGraph agents
│   │   ├── services/  # 비즈니스 로직
│   │   ├── api/       # API routers
│   │   └── utils/     # 유틸리티
│   └── data/
│       └── scenarios/ # 시나리오 JSON 파일
│
├── front/             # React + Vite 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
│   └── dist/          # 빌드 결과물
│
└── docs/              # 문서
```

---

## 🔧 문제 해결

### Chrome 콘솔에 에러가 많이 보여요

```
Failed to load resource: net::ERR_FILE_NOT_FOUND
- utils.js:1
- extensionState.js:1
```

**이것은 Chrome Extension 에러입니다** (앱 자체의 문제 아님!)

**해결 방법**:
1. **콘솔 필터 설정** (추천)
   - Chrome DevTools → Console 탭
   - Filter에 입력: `-utils.js -extensionState.js -heuristicsRedefinitions.js`

2. **시크릿 모드 사용**: `Cmd + Shift + N` (Mac)

자세한 내용은 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) 참조

---

## 📈 성능 최적화

최근 적용된 최적화:
- ✅ LLM max_tokens 40-50% 감소
- ✅ 캐싱 추가 (300-800ms 절약)
- ✅ 프롬프트 간소화 (20-30% 감소)
- ✅ 성능 로깅 추가

**결과**: 전체 응답 시간 **30-35초 → 18-23초** (40% 개선)

---

## 🧪 API 테스트

### Swagger UI로 직접 테스트

http://localhost:8000/docs

### curl로 테스트

```bash
# Health check
curl http://localhost:8000/health

# 시나리오 목록
curl http://localhost:8000/api/scenarios
```

---

## 📚 문서

- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 문제 해결 가이드
- [API Docs](http://localhost:8000/docs) - API 문서 (서버 실행 후)

---

## 🛠 기술 스택

### Backend
- FastAPI
- LangGraph
- OpenAI GPT-4
- PostgreSQL + pgvector
- Redis (optional)

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router

---

## 📝 라이센스

MIT License

---

**마지막 업데이트**: 2025-11-05
