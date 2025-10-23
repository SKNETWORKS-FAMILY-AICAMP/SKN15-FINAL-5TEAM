# 🚀 KIME Chat Agent - 빠른 시작 가이드

## 📌 이 프로젝트는?

**귀멸의 칼날(鬼滅の刃)** 세계관을 배경으로 한 **멀티 캐릭터 대화 시스템**입니다.
- 🎭 **자연스러운 대화**: LLM 기반 자연어 의도 파악
- 🎮 **동적 분기**: 플레이어의 선택에 따라 이야기가 달라짐
- 💬 **다중 캐릭터**: 탄지로, 렌고쿠, 이노스케, 젠이츠 등과 대화
- 🎯 **설득 시스템**: 점진적 힌트로 동료 규합

---

## ⚡ 5분 안에 시작하기

### 방법 1: Docker로 빠른 시작 (권장) 🐳

```bash
# 1. Repository 클론
git clone https://github.com/YOUR_USERNAME/kime-chat-agent.git
cd kime-chat-agent

# 2. 환경 변수 설정
cp .env.example .env
nano .env  # API 키 입력

# 3. Docker로 실행 (환경 설정 불필요!)
docker-compose up --build
```

**완료!** 별도의 Python 환경 설정이 필요 없습니다.

자세한 Docker 가이드: [DOCKER_GUIDE.md](DOCKER_GUIDE.md)

---

### 방법 2: 로컬 Python 환경 🐍

```bash
# 1. Repository 클론
git clone https://github.com/YOUR_USERNAME/kime-chat-agent.git
cd kime-chat-agent

# 2. Python 패키지 설치
pip install -r requirements.txt

# 3. 환경 변수 파일 생성
cp .env.example .env

# 4. .env 파일을 열어서 OpenAI API 키 입력
# OPENAI_API_KEY=sk-YOUR_KEY_HERE

# 5. 게임 실행
python play.py
```

---

## 📁 주요 파일 구조

```
kime_chat_agent/
├── play.py                 # 🎮 메인 실행 파일
├── requirements.txt        # 📦 필요한 패키지 목록
├── .env.example           # 🔑 환경 변수 예시
├── GIT_SETUP_GUIDE.md     # 📝 Git 설정 가이드
│
├── src/                   # 소스 코드
│   ├── agents/           # AI 에이전트
│   │   ├── parent_agent.py    # 게임 마스터
│   │   └── children_agent.py  # 캐릭터 대사 생성
│   ├── core/             # 핵심 시스템
│   │   ├── workflow.py        # LangGraph 워크플로우
│   │   └── graph_state.py     # 게임 상태 관리
│   └── utils/            # 유틸리티
│       └── scenario_loader.py # 시나리오 로더
│
├── data/                  # 게임 데이터
│   ├── scenarios/        # 시나리오 JSON
│   │   └── cutscene5_simple.json  # 메인 시나리오
│   └── characters_db.json # 캐릭터 데이터베이스
│
└── configs/               # 설정 파일
    ├── prompts.yaml      # AI 프롬프트
    └── settings.yaml     # 게임 설정
```

---

## 🎯 주요 기능

### 1. 자연스러운 대화 분기
- ❌ 번호 선택 없음: "1번", "2번" 대신 자유로운 대화
- ✅ 의도 파악: "동료들을 찾아보자" → 자동으로 recruit_mission 진행
- ✅ LLM 매칭: 70% 이상 확신도로 의도 파악

### 2. 점진적 힌트 시스템
```
실패 0회: "이노스케를 설득해봐!"
실패 1회: "이노스케는 강한 녀석을 좋아해!"
실패 2회: "이노스케는 약하다는 말을 싫어해!"
실패 3회: "겁쟁이라는 말도 싫어해!"
```

### 3. 다중 엔딩
- 🎭 **히든 엔딩**: 동료를 빠르게 설득하여 함께 싸움
- ⚔️ **일반 엔딩**: 동료를 설득했지만 시간 초과
- 💀 **배드 엔딩**: 혼자 돌진하여 실패

---

## 🧪 테스트 실행

```bash
# 자연스러운 대화 테스트
python test_natural_dialogue.py

# 전체 흐름 테스트
python test_complete_flow.py

# 분기 시스템 테스트
python test_branching.py
```

---

## ⚙️ 환경 변수 설정

`.env` 파일에서 설정 가능:

```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=sk-YOUR_KEY_HERE

# 디버그 모드 활성화 (상세 로그 출력)
DEBUG=true

# LLM 사용 여부 (false = 하드코딩 대사 사용)
USE_LLM=true
```

---

## 🐛 문제 해결

### Q: "No module named 'openai'" 오류
```bash
pip install -r requirements.txt
```

### Q: ".env 파일이 없습니다" 오류
```bash
cp .env.example .env
# 그 후 .env 파일에 API 키 입력
```

### Q: LLM 없이 테스트하고 싶어요
```bash
# .env 파일에서:
USE_LLM=false
```

---

## 📚 추가 문서

- 🐳 [Docker 가이드](DOCKER_GUIDE.md) - Docker로 빠른 실행
- 📖 [Git 설정 가이드](GIT_SETUP_GUIDE.md) - Git 초기화 및 협업 방법
- 🧪 [테스트 가이드](README_TESTING.md) - 테스트 실행 방법
- 📝 [시나리오 분석](SCENARIO_IMPLEMENTATION_PLAN.md) - 시나리오 구조 설명
- 🏗️ [시스템 분석](SYSTEM_ANALYSIS_AND_RECOMMENDATIONS.md) - 시스템 아키텍처

---

## 👥 팀원 추가

### Collaborator 추가 방법 (Private Repository)

1. GitHub Repository → **Settings**
2. 왼쪽 메뉴 → **Collaborators**
3. **Add people** 클릭
4. 팀원의 GitHub 사용자명 또는 이메일 입력
5. 팀원에게 초대 이메일 전송됨

---

## 🎮 게임 플레이 흐름

```
1. 게임 시작 → 사용자 이름 입력
   ↓
2. 탄지로와 대화
   ↓
3. 렌고쿠 등장
   ↓
4. 아카자 등장 → 렌고쿠의 명령
   ↓
5. 선택의 순간:
   - "내가 직접 도와야겠어" → 💀 배드 엔딩
   - "동료들을 찾아보자" → 🎯 설득 미션
     ↓
6. 이노스케 설득 (도발 필요)
   ↓
7. 젠이츠 설득 (네즈코 언급 필요)
   ↓
8. 엔딩 확인
```

---

## 💡 개발 팁

### 새 시나리오 추가하기
`data/scenarios/` 폴더에 JSON 파일 추가

### 캐릭터 데이터 수정
`data/characters_db.json` 파일 편집

### 프롬프트 조정
`configs/prompts.yaml` 파일에서 AI 행동 조정

---

## 📞 문의

- 📧 이메일: [팀 이메일]
- 💬 Discord/Slack: [채널 링크]
- 🐛 버그 리포트: GitHub Issues 탭

---

**즐거운 개발 되세요! 🎉**
