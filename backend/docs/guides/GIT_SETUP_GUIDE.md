# 🚀 Git 설정 및 팀 공유 가이드

## 📋 목차
1. [GitHub Repository 생성](#1-github-repository-생성)
2. [로컬 Git 초기화](#2-로컬-git-초기화)
3. [원격 저장소 연결 (메인 브랜치에 영향 없이)](#3-원격-저장소-연결)
4. [팀원들을 위한 설치 가이드](#4-팀원들을-위한-설치-가이드)

---

## 1. GitHub Repository 생성

### 1-1. GitHub에서 새 Repository 생성
1. https://github.com 접속 후 로그인
2. 우측 상단 **"+"** 클릭 → **"New repository"** 선택
3. 설정:
   - **Repository name**: `kime-chat-agent` (또는 원하는 이름)
   - **Description**: "귀멸의 칼날 멀티 캐릭터 대화 시스템"
   - **Visibility**:
     - 🔒 **Private** (팀원만 접근) - **추천**
     - 🌍 **Public** (누구나 접근)
   - ⚠️ **중요**: "Add a README file" 체크 **해제** (이미 README가 있음)
4. **"Create repository"** 클릭

### 1-2. Repository URL 확인
생성 후 나오는 URL을 복사해두세요:
```
https://github.com/YOUR_USERNAME/kime-chat-agent.git
```

---

## 2. 로컬 Git 초기화

현재 폴더에서 다음 명령어들을 실행하세요:

```bash
# Git 초기화
git init

# 현재 상태 확인 (.gitignore가 잘 작동하는지 확인)
git status

# 모든 파일 추가 (민감한 파일은 .gitignore로 자동 제외됨)
git add .

# 첫 커밋
git commit -m "Initial commit: KIME Chat Agent with natural dialogue system

- Multi-character dialogue system
- LLM-based natural language intent matching
- Progressive hints for character persuasion
- Auto-branching narrative system
- Implemented by Team [팀 이름]"
```

---

## 3. 원격 저장소 연결 (메인 브랜치에 영향 없이)

### ⚠️ 중요: 기존 Repository에 추가하는 경우

**메인 브랜치를 덮어쓰지 않으려면** 새 브랜치를 만들어서 푸시하세요:

```bash
# 방법 A: 완전히 새로운 Repository인 경우
git remote add origin https://github.com/YOUR_USERNAME/kime-chat-agent.git
git branch -M main
git push -u origin main

# 방법 B: 기존 Repository가 있는 경우 (메인 브랜치 보호)
git remote add origin https://github.com/YOUR_USERNAME/EXISTING_REPO.git

# 새 브랜치 생성 (예: team-release)
git checkout -b team-release

# 새 브랜치로 푸시
git push -u origin team-release

# GitHub에서 Pull Request 생성하여 리뷰 후 병합
```

### 🔐 인증 방법

#### Personal Access Token 사용 (추천)
1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" 클릭
3. 권한 선택: `repo` 전체 체크
4. 토큰 생성 후 **반드시 복사** (다시 볼 수 없음)
5. Push 시 비밀번호 대신 토큰 입력

---

## 4. 팀원들을 위한 설치 가이드

팀원들에게 다음 안내를 공유하세요:

### 4-1. Repository 클론

```bash
# Repository 클론
git clone https://github.com/YOUR_USERNAME/kime-chat-agent.git
cd kime-chat-agent
```

### 4-2. 환경 설정

```bash
# 1. 가상환경 생성 (선택사항이지만 권장)
python -m venv venv

# 2. 가상환경 활성화
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 필요한 패키지 설치
pip install -r requirements.txt

# 4. 환경 변수 파일 생성
cp .env.example .env

# 5. .env 파일을 열어서 OpenAI API 키 입력
# OPENAI_API_KEY=sk-YOUR_ACTUAL_KEY_HERE
```

### 4-3. 실행

```bash
# 게임 실행
python play.py

# 또는 실행 스크립트 사용
./RUN.sh
```

### 4-4. 테스트 실행

```bash
# 전체 테스트
./RUN_TESTS.sh

# 특정 테스트
python test_natural_dialogue.py
python test_complete_flow.py
```

---

## 5. 협업 워크플로우

### 팀원이 변경사항을 받는 방법

```bash
# 최신 변경사항 받기
git pull origin main  # 또는 team-release

# 변경사항 확인
git log --oneline -5
```

### 팀원이 변경사항을 올리는 방법

```bash
# 1. 변경사항 확인
git status

# 2. 변경된 파일 추가
git add [파일명]
# 또는 모두 추가
git add .

# 3. 커밋
git commit -m "설명: 무엇을 변경했는지"

# 4. 푸시
git push origin main  # 또는 team-release
```

---

## 6. 브랜치 전략 (선택사항)

더 안전한 협업을 위해 브랜치를 나눌 수 있습니다:

```bash
# 새 기능 개발 시
git checkout -b feature/새기능이름

# 작업 후 푸시
git push -u origin feature/새기능이름

# GitHub에서 Pull Request 생성 → 리뷰 → 병합
```

---

## 🆘 문제 해결

### Q1: ".env 파일이 없다"는 오류가 나요
**A:** `.env.example`을 복사하여 `.env`로 만들고 API 키를 입력하세요.

### Q2: "git push" 시 인증 오류가 나요
**A:** Personal Access Token을 생성하여 비밀번호 대신 사용하세요.

### Q3: "ModuleNotFoundError" 오류가 나요
**A:** `pip install -r requirements.txt` 명령어를 실행하세요.

### Q4: 메인 브랜치를 실수로 덮어썼어요
**A:** GitHub에서 이전 커밋으로 되돌릴 수 있습니다:
```bash
# 특정 커밋으로 되돌리기
git reset --hard [커밋해시]
git push -f origin main
```

---

## 📞 연락처

문제가 있으면 팀 채널에 문의하세요!

- 📧 이메일: [팀 이메일]
- 💬 Discord/Slack: [채널 링크]
- 📝 Issues: GitHub Issues 탭 활용
