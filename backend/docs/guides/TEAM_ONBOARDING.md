# 🚀 팀원 온보딩 가이드

## 📋 3분 안에 실행하기

### Step 1: 저장소 클론

```bash
# 저장소 클론
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git
cd SKN15-FINAL-5TEAM

# development 브랜치로 전환
git checkout devlopment
```

### Step 2: 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (API 키 입력)
nano .env
```

**.env 파일에 다음 내용 입력:**
```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
DEBUG=false
USE_LLM=true
```

저장: `Ctrl + O` → `Enter` → 종료: `Ctrl + X`

### Step 3: 실행

**방법 1: Docker 실행 (권장)** 🐳
```bash
# Docker 설치 확인
docker --version
docker-compose --version

# 한 번에 빌드 & 실행
docker-compose up --build

# 또는 백그라운드 실행
docker-compose up -d
```

**방법 2: Python 직접 실행** 🐍
```bash
# Python 패키지 설치
pip install -r requirements.txt

# 게임 실행
python play.py
```

---

## 📝 빠른 명령어 정리

### 저장소 관리
```bash
# 최신 코드 받기
git pull origin devlopment

# 변경사항 확인
git status

# 브랜치 확인
git branch
```

### Docker 관리
```bash
# 실행
docker-compose up

# 백그라운드 실행
docker-compose up -d

# 중지
docker-compose down

# 로그 확인
docker-compose logs -f

# 재시작
docker-compose restart
```

### Python 로컬 실행
```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt

# 게임 실행
python play.py

# 테스트 실행
python test_complete_flow.py
```

---

## 🎮 게임 플레이 방법

### 시작하기
```bash
python play.py
```

### 게임 흐름
1. 사용자 이름 입력
2. 탄지로와 대화
3. 렌고쿠 등장
4. 아카자 등장 (전투 시작)
5. **선택의 순간**:
   - "동료를 찾아보자" → 설득 미션
   - "직접 도와야겠어" → 배드 엔딩
6. 이노스케 설득 (도발 필요)
7. 젠이츠 설득 (네즈코 언급)
8. 엔딩 확인

### 입력 예시
```
✅ 좋은 입력:
- "이노스케를 설득하러 가자"
- "렌고쿠를 도와야 해"
- "동료들을 찾아보자"

❌ 나쁜 입력:
- "씨발" (가드레일 차단)
- "오늘 날씨 어때?" (off-topic)
```

---

## 🔧 문제 해결

### Q1: "No module named 'openai'" 오류
```bash
pip install -r requirements.txt
```

### Q2: ".env 파일이 없습니다" 오류
```bash
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

### Q3: Docker 포트 충돌
```bash
# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 8001로 변경
```

### Q4: API 키 오류
```bash
# .env 파일 확인
cat .env

# OPENAI_API_KEY가 제대로 입력되었는지 확인
```

### Q5: LLM 없이 테스트하고 싶을 때
```bash
# .env 파일에서:
USE_LLM=false
```

---

## 📁 주요 파일 위치

```
SKN15-FINAL-5TEAM/
├── play.py                      # 🎮 게임 실행
├── .env.example                 # 🔑 환경 변수 예시
├── docker-compose.yml           # 🐳 Docker 설정
├── requirements.txt             # 📦 필요 패키지
│
├── src/                         # 소스 코드
│   ├── agents/
│   │   ├── router_agent.py      # Router (LLM 기반)
│   │   ├── guardrail_agent.py   # Guardrail (LLM 기반)
│   │   ├── parent_agent.py      # 게임 마스터
│   │   └── children_agent.py    # 캐릭터 대사
│   ├── core/
│   │   ├── workflow.py          # LangGraph 워크플로우
│   │   └── graph_state.py       # 상태 관리
│   └── utils/
│
├── data/
│   ├── scenarios/
│   │   └── cutscene5_simple.json  # 메인 시나리오
│   └── characters_db.json         # 캐릭터 데이터
│
└── configs/
    ├── prompts.yaml             # AI 프롬프트
    ├── settings.yaml            # 게임 설정
    └── characters.yaml          # 캐릭터 설정
```

---

## 📚 추가 문서

- 🐳 [Docker 가이드](DOCKER_GUIDE.md) - Docker 상세 가이드
- 📖 [빠른 시작](QUICK_START.md) - 기능 설명
- 🧪 [테스트 가이드](README_TESTING.md) - 테스트 실행

---

## 💡 개발 팁

### 시나리오 수정
```bash
# 시나리오 파일 편집
nano data/scenarios/cutscene5_simple.json
```

### 캐릭터 대사 수정
```bash
# 캐릭터 데이터 편집
nano data/characters_db.json
```

### AI 프롬프트 수정
```bash
# 프롬프트 편집
nano configs/prompts.yaml
```

### 로그 확인
```bash
# 로그 디렉토리 확인
ls -l logs/

# 최근 로그 보기
tail -f logs/game_*.log
```

---

## 🆘 도움이 필요하면

1. **GitHub Issues**: 버그 리포트
2. **팀 채널**: 질문 및 토론
3. **문서 참고**: DOCKER_GUIDE.md, QUICK_START.md

---

**즐거운 개발 되세요! 🎉**
