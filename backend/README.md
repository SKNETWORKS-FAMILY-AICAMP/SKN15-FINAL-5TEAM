# 🎮 Kime Chat Agent

**SK Networks Family AI Camp 15기 - 5.Andrew Team**

LangGraph 기반 멀티 에이전트 시스템을 활용한 인터랙티브 게임 챗봇

---

## 🚀 빠른 시작

### 3분 안에 실행하기

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git kime_chat_agent_dev && \
cd kime_chat_agent_dev && \
git checkout devlopment && \
cp .env.example .env && \
nano .env  # API 키 입력: OPENAI_API_KEY=sk-... && \
docker-compose up --build
```

**또는 Python 직접 실행:**
```bash
pip install -r requirements.txt
python play.py
```

자세한 설치 방법: [docs/guides/QUICK_INSTALL.md](docs/guides/QUICK_INSTALL.md)

---

## 📋 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [핵심 기능](#-핵심-기능)
3. [시스템 아키텍처](#-시스템-아키텍처)
4. [프로젝트 구조](#-프로젝트-구조)
5. [기술 스택](#-기술-스택)
6. [문서](#-문서)

---

## 🎯 프로젝트 개요

**귀멸의 칼날(鬼滅の刃)** 세계관을 배경으로 한 LLM 기반 인터랙티브 게임 챗봇입니다.

### 핵심 특징

✨ **LLM 기반 자연스러운 대화**
- OpenAI GPT를 활용한 캐릭터별 대사 생성
- Router Agent: on/off topic 자동 분류
- Guardrail Agent: 부적절한 표현 실시간 차단

🤖 **멀티 에이전트 시스템**
- Router → Guardrail → Parent → Children → Dialogue
- 5개의 전문화된 에이전트 협업

🎭 **동적 시나리오 처리**
- JSON 기반 완전 동적 시스템
- 하드코딩 없이 시나리오 추가/변경

🐳 **Docker 지원**
- 원클릭 실행 (`docker-compose up`)
- 환경 설정 자동화

---

## 🌟 핵심 기능

### 1. LLM 기반 Router Agent
- **on_topic / off_topic 자동 분류**
- LLM + 규칙 기반 하이브리드 방식
- 게임 관련 입력만 처리

### 2. LLM 기반 Guardrail Agent
- **부적절한 표현 실시간 차단**
- 욕설, 혐오 발언, 성적 표현 감지
- 금지 목록에 없는 우회 표현도 LLM이 감지

### 3. 멀티 캐릭터 대화 시스템
- 탄지로, 렌고쿠, 이노스케, 젠이츠, 아카자
- 각 캐릭터의 성격과 말투 반영
- 친밀도 시스템

### 4. 시나리오 분기 시스템
- 사용자 선택에 따른 다중 엔딩
- 히든 엔딩 / 일반 엔딩 / 배드 엔딩
- 설득 미션 (점진적 힌트)

---

## 🏗️ 시스템 아키텍처

```
User Input
    ↓
[Router Agent] ← LLM 기반 on/off topic 분류
    ↓
[Guardrail Agent] ← LLM 기반 안전성 검증
    ↓
[Parent Agent] ← 게임 마스터 (스테이지 관리)
    ↓
[Children Agent] ← 캐릭터 대사 생성
    ↓
[Dialogue Agent] ← 출력 포맷팅
    ↓
Output to User
```

### 워크플로우 상세
- **Router**: 입력을 게임 관련 / 일상 대화로 분류
- **Guardrail**: 부적절한 표현 차단
- **Parent**: 현재 스테이지 분석, 다음 행동 결정
- **Children**: LLM을 통한 캐릭터별 대사 생성
- **Dialogue**: 사용자 친화적 출력 포맷팅

---

## 📁 프로젝트 구조

```
kime_chat_agent_dev/
├── 📄 play.py                    # 🎮 메인 실행 파일
├── 📄 requirements.txt           # 📦 Python 패키지
├── 📄 Dockerfile                 # 🐳 Docker 이미지
├── 📄 docker-compose.yml         # 🐳 Docker Compose
├── 📄 .env.example               # 🔑 환경 변수 템플릿
│
├── 📂 src/                       # 소스 코드
│   ├── agents/                   # AI 에이전트
│   │   ├── router_agent.py       # Router (LLM 기반)
│   │   ├── guardrail_agent.py    # Guardrail (LLM 기반)
│   │   ├── parent_agent.py       # 게임 마스터
│   │   └── children_agent.py     # 캐릭터 대사
│   ├── core/                     # 핵심 시스템
│   │   ├── workflow.py           # LangGraph 워크플로우
│   │   └── graph_state.py        # 상태 관리
│   ├── tools/                    # 도구
│   └── utils/                    # 유틸리티
│
├── 📂 data/                      # 게임 데이터
│   ├── scenarios/                # 시나리오 JSON
│   │   └── cutscene5_simple.json
│   └── characters_db.json        # 캐릭터 데이터
│
├── 📂 configs/                   # 설정 파일
│   ├── prompts.yaml              # AI 프롬프트
│   ├── settings.yaml             # 게임 설정
│   └── characters.yaml           # 캐릭터 설정
│
├── 📂 tests/                     # 테스트 코드
├── 📂 tests_archive/             # 개별 테스트 아카이브
│
├── 📂 docs/                      # 문서
│   ├── guides/                   # 가이드 문서
│   │   ├── QUICK_INSTALL.md      # 빠른 설치
│   │   ├── TEAM_ONBOARDING.md    # 팀원 온보딩
│   │   ├── DOCKER_GUIDE.md       # Docker 가이드
│   │   └── ...
│   └── analysis/                 # 분석 문서
│       ├── SYSTEM_ANALYSIS_AND_RECOMMENDATIONS.md
│       └── ...
│
└── 📂 scripts/                   # 유틸리티 스크립트
    ├── INSTALL_AND_RUN.sh        # 자동 설치
    ├── RUN.sh                    # 실행 스크립트
    └── RUN_TESTS.sh              # 테스트 실행
```

---

## 🛠️ 기술 스택

### Core
- **Python 3.10+**
- **LangGraph**: 멀티 에이전트 워크플로우
- **OpenAI API**: GPT-4/3.5 for LLM

### Agent Framework
- **Router Agent**: LLM + 규칙 기반 분류
- **Guardrail Agent**: LLM 기반 안전성 검증
- **Parent Agent**: 게임 로직 관리
- **Children Agent**: 캐릭터 대사 생성

### Infrastructure
- **Docker & Docker Compose**: 컨테이너화
- **YAML/JSON**: 설정 및 시나리오

### Testing
- **pytest**: 단위 테스트
- **Custom Test Suite**: 통합 테스트

---

## 📚 문서

### 가이드
- [빠른 설치 가이드](docs/guides/QUICK_INSTALL.md) - 3분 안에 실행
- [팀원 온보딩](docs/guides/TEAM_ONBOARDING.md) - 신규 팀원용
- [Docker 가이드](docs/guides/DOCKER_GUIDE.md) - Docker 상세 사용법
- [Git 설정 가이드](docs/guides/GIT_SETUP_GUIDE.md) - Git 협업
- [테스트 가이드](docs/guides/README_TESTING.md) - 테스트 실행

### 분석 및 설계
- [시스템 분석](docs/analysis/SYSTEM_ANALYSIS_AND_RECOMMENDATIONS.md)
- [시나리오 구현 계획](docs/analysis/SCENARIO_IMPLEMENTATION_PLAN.md)
- [시스템 아키텍처](docs/analysis/system_architecture.md)
- [구현 완료 보고서](docs/analysis/IMPLEMENTATION_COMPLETE.md)

---

## 🎮 게임 플레이

### 실행
```bash
python play.py
```

### 게임 흐름
1. 사용자 이름 입력
2. 탄지로와 대화
3. 렌고쿠 등장
4. 아카자 등장 (전투 시작)
5. **선택의 순간**
6. 설득 미션
7. 엔딩

### 입력 예시
```
✅ "이노스케를 설득하러 가자"
✅ "동료들을 찾아보자"
✅ "렌고쿠를 도와야 해"

❌ "씨발" (Guardrail 차단)
❌ "오늘 날씨 어때?" (Router가 off-topic 분류)
```

---

## 🧪 테스트

```bash
# 전체 테스트
pytest

# 특정 테스트
python tests_archive/test_complete_flow.py
python tests_archive/test_natural_dialogue.py

# 테스트 스크립트
./scripts/RUN_TESTS.sh
```

---

## 🤝 기여

### 코드 수정
1. `devlopment` 브랜치 체크아웃
2. 수정 후 커밋
3. Pull Request 생성

### 시나리오 추가
```bash
# 새 시나리오 파일 생성
nano data/scenarios/new_scenario.json

# 시나리오 JSON 구조는 cutscene5_simple.json 참고
```

---

## 📄 라이센스

This project is part of SK Networks Family AI Camp 15th - Team 5 (Andrew Team)

---

## 👥 팀원

**SK Networks Family AI Camp 15기 - 5.Andrew Team**

---

## 🆘 문제 해결

### "No module named 'openai'"
```bash
pip install -r requirements.txt
```

### ".env 파일이 없습니다"
```bash
cp .env.example .env
nano .env  # API 키 입력
```

### Docker 포트 충돌
```yaml
# docker-compose.yml 수정
ports:
  - "8001:8000"
```

더 많은 문제 해결: [docs/guides/TEAM_ONBOARDING.md](docs/guides/TEAM_ONBOARDING.md)

---

**즐거운 개발 되세요! 🎉**
