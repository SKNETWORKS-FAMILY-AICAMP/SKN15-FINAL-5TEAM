# 🚀 원클릭 설치 가이드

## 방법 1: 자동 설치 스크립트 (가장 쉬움) ⭐

### Linux / Mac
```bash
curl -fsSL https://raw.githubusercontent.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM/devlopment/INSTALL_AND_RUN.sh | bash
```

또는

```bash
wget -qO- https://raw.githubusercontent.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM/devlopment/INSTALL_AND_RUN.sh | bash
```

---

## 방법 2: 수동 설치 (명령어 복사 붙여넣기)

### 전체 명령어 (한 번에 복사)

```bash
# 저장소 클론
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git ~/kime_chat_agent && \
cd ~/kime_chat_agent && \
git checkout devlopment && \

# 환경 변수 설정
cp .env.example .env && \
echo "⚠️  .env 파일을 수정하여 API 키를 입력하세요:" && \
echo "nano .env" && \
echo "" && \

# Docker 실행
docker-compose up --build
```

### 단계별 명령어

**1. 클론 및 이동**
```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git ~/kime_chat_agent
cd ~/kime_chat_agent
git checkout devlopment
```

**2. 환경 변수 설정**
```bash
cp .env.example .env
nano .env  # API 키 입력: OPENAI_API_KEY=sk-...
```

**3. Docker 실행**
```bash
docker-compose up --build
```

---

## 방법 3: Python 직접 실행

```bash
# 저장소 클론
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git ~/kime_chat_agent
cd ~/kime_chat_agent
git checkout devlopment

# 환경 변수 설정
cp .env.example .env
nano .env  # API 키 입력

# Python 패키지 설치
pip install -r requirements.txt

# 게임 실행
python play.py
```

---

## 방법 4: 특정 폴더에 설치

원하는 폴더 경로를 지정하여 설치:

```bash
# 설치 경로 지정 (예: /workspace/my_project)
INSTALL_PATH="/workspace/my_project"

git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git "$INSTALL_PATH" && \
cd "$INSTALL_PATH" && \
git checkout devlopment && \
cp .env.example .env && \
echo "⚠️  .env 파일 수정 필요: nano $INSTALL_PATH/.env" && \
docker-compose up --build
```

---

## Windows 사용자

### PowerShell
```powershell
# 저장소 클론
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git $HOME\kime_chat_agent
cd $HOME\kime_chat_agent
git checkout devlopment

# 환경 변수 설정
Copy-Item .env.example .env
notepad .env  # API 키 입력

# Docker 실행
docker-compose up --build
```

---

## API 키 입력 방법

`.env` 파일 편집:

```bash
nano .env
```

다음과 같이 수정:
```bash
OPENAI_API_KEY=sk-your-actual-api-key-here  # ← 여기에 실제 키 입력
OPENAI_API_BASE=https://api.openai.com/v1
DEBUG=false
USE_LLM=true
```

저장: `Ctrl + O` → `Enter` → 종료: `Ctrl + X`

---

## 실행 확인

성공적으로 실행되면 다음과 같은 화면이 나타납니다:

```
╔════════════════════════════════════════════════════════════╗
║          🔥 키메츠노야이바: 아카자 조우 🔥                 ║
╚════════════════════════════════════════════════════════════╝

플레이어 이름을 입력하세요:
```

---

## 문제 해결

### "git: command not found"
```bash
# Ubuntu/Debian
sudo apt-get install git

# macOS
brew install git
```

### "docker: command not found"
```bash
# Docker 설치
# https://docs.docker.com/get-docker/

# 또는 Python으로 실행
pip install -r requirements.txt
python play.py
```

### "Permission denied"
```bash
# 스크립트 실행 권한 부여
chmod +x INSTALL_AND_RUN.sh
./INSTALL_AND_RUN.sh
```

### 포트 충돌
```bash
# docker-compose.yml 수정
# ports: "8001:8000"  # 포트 변경
```

---

## 빠른 재실행

이미 설치했다면:

```bash
cd ~/kime_chat_agent
docker-compose up
```

또는

```bash
cd ~/kime_chat_agent
python play.py
```

---

## 업데이트

최신 코드로 업데이트:

```bash
cd ~/kime_chat_agent
git pull origin devlopment
docker-compose up --build
```

---

**문제가 있으면 TEAM_ONBOARDING.md를 참고하세요!**
