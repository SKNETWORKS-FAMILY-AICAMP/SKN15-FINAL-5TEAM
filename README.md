# KIME Chat - 귀멸의 칼날 인터랙티브 챗봇

LangGraph 기반 AI 대화 시스템 + React SPA 프론트엔드

---

## 📁 프로젝트 구조

```
workspace/
├── backend/          # 백엔드 (LangGraph + FastAPI)
│   ├── src/          # 소스 코드
│   ├── data/         # 시나리오 및 캐릭터 데이터
│   ├── api_server.py # FastAPI 서버
│   ├── requirements.txt
│   └── .env          # 환경 변수 (직접 생성 필요)
├── front/            # 프론트엔드 (React + Vite SPA)
│   ├── src/
│   ├── public/
│   └── package.json
└── venv/             # Python 가상환경
```

---

## 🚀 팀원용 환경 세팅 가이드

### 1️⃣ 저장소 클론

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git
cd SKN15-FINAL-5TEAM
```

### 2️⃣ Python 가상환경 설정

**필수 요구사항**: Python 3.9 ~ 3.13

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# pip 업그레이드
pip install --upgrade pip

# 백엔드 의존성 설치
pip install -r backend/requirements.txt
```

### 3️⃣ 백엔드 환경 변수 설정

```bash
# backend/.env 파일 생성
cd backend
cp .env.example .env  # .env.example이 있다면
# 또는 직접 생성:
nano .env  # 또는 vim, code 등 에디터 사용
```

**backend/.env 파일 내용**:
```env
# OpenAI API Configuration
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Server Configuration
PORT=8000
HOST=0.0.0.0

# Development / Production
ENVIRONMENT=development
```

⚠️ **중요**: `OPENAI_API_KEY`에 실제 OpenAI API 키를 입력하세요!

### 4️⃣ 프론트엔드 의존성 설치

**필수 요구사항**: Node.js 18 이상

```bash
cd ../front  # workspace/front로 이동

# 의존성 설치
npm install
```

### 5️⃣ 서버 실행

**터미널 2개를 열어서 각각 실행하세요!**

#### 터미널 1: 백엔드 서버
```bash
cd /path/to/workspace/backend
source ../venv/bin/activate  # Windows: ..\venv\Scripts\activate
python api_server.py
```

**백엔드 서버 실행 확인**:
- 콘솔: `🚀 Starting KIME Chat API Server...`
- URL: http://localhost:8000
- API Docs: http://localhost:8000/docs

#### 터미널 2: 프론트엔드 서버
```bash
cd /path/to/workspace/front
npm run dev
```

**프론트엔드 서버 실행 확인**:
- 콘솔: `VITE v5.x.x ready in xxx ms`
- URL: http://localhost:3000

---

## 🔧 문제 해결 (Troubleshooting)

### 백엔드 관련

#### 1. `ModuleNotFoundError: No module named 'fastapi'`
```bash
# 가상환경이 활성화되었는지 확인
which python  # 경로에 venv가 포함되어 있어야 함

# 의존성 재설치
pip install -r backend/requirements.txt
```

#### 2. `openai.OpenAIError: The api_key client option must be set`
```bash
# backend/.env 파일이 존재하는지 확인
ls backend/.env

# .env 파일에 실제 API 키가 있는지 확인
cat backend/.env
```

#### 3. Port 8000이 이미 사용 중
```bash
# Mac/Linux
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID번호> /F
```

### 프론트엔드 관련

#### 1. `npm install` 실패
```bash
# node_modules와 package-lock.json 삭제 후 재설치
rm -rf node_modules package-lock.json
npm install
```

#### 2. Port 3000이 이미 사용 중
```bash
# Mac/Linux
lsof -ti:3000 | xargs kill -9

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID번호> /F
```

#### 3. Vite 캐시 문제
```bash
# Vite 캐시 삭제 후 재시작
rm -rf node_modules/.vite
npm run dev
```

#### 4. `Failed to resolve import "@/components/..."`
```bash
# tsconfig.json과 vite.config.ts가 올바른지 확인 후 서버 재시작
npm run dev
```

---

## 📝 개발 워크플로우

### 새 브랜치 생성
```bash
git checkout -b feature/your-feature-name
```

### 변경사항 커밋
```bash
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin feature/your-feature-name
```

### Pull Request 생성
GitHub에서 PR 생성 후 리뷰 요청

---

## 🛠️ 기술 스택

### 백엔드
- **Framework**: FastAPI 0.109.0
- **LLM**: LangChain 1.0+ / LangGraph 1.0+
- **AI Provider**: OpenAI GPT-4o-mini
- **Database**: SQLite (aiosqlite)

### 프론트엔드
- **Framework**: React 18
- **Build Tool**: Vite 5
- **Language**: TypeScript
- **Routing**: React Router DOM
- **Styling**: Tailwind CSS

---

## 📞 문의

문제가 발생하면 팀 슬랙 채널 또는 GitHub Issues에 문의해주세요!

- GitHub: https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM
- Docs: http://localhost:8000/docs (서버 실행 후)
