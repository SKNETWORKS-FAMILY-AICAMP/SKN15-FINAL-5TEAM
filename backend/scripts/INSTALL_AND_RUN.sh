#!/bin/bash

# 키메 채팅 에이전트 - 자동 설치 및 실행 스크립트
# SKN15-FINAL-5TEAM

set -e  # 오류 발생 시 중단

echo "=================================="
echo "🎮 키메 채팅 에이전트 설치 시작"
echo "=================================="
echo ""

# 1. 작업 디렉토리 설정
INSTALL_DIR="$HOME/kime_chat_agent"
echo "📁 설치 경로: $INSTALL_DIR"

# 기존 디렉토리 확인
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  기존 디렉토리가 존재합니다."
    read -p "삭제하고 새로 설치하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
        echo "✅ 기존 디렉토리 삭제 완료"
    else
        echo "❌ 설치 취소"
        exit 1
    fi
fi

# 2. 저장소 클론
echo ""
echo "📥 저장소 클론 중..."
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN15-FINAL-5TEAM.git "$INSTALL_DIR"

# 3. 디렉토리 이동
cd "$INSTALL_DIR"

# 4. 브랜치 전환
echo ""
echo "🔀 devlopment 브랜치로 전환 중..."
git checkout devlopment

# 5. .env 파일 설정
echo ""
echo "🔑 환경 변수 설정"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  .env 파일이 생성되었습니다."
    echo "❗ OpenAI API 키를 입력해야 합니다."
    echo ""

    read -p "지금 API 키를 입력하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "OpenAI API 키 입력: " api_key
        if [ ! -z "$api_key" ]; then
            sed -i "s/YOUR_API_KEY_HERE/$api_key/" .env
            echo "✅ API 키 설정 완료"
        else
            echo "⚠️  API 키가 입력되지 않았습니다. 나중에 .env 파일을 직접 수정하세요."
        fi
    else
        echo "⚠️  나중에 .env 파일을 직접 수정하세요:"
        echo "   nano $INSTALL_DIR/.env"
    fi
else
    echo "✅ .env 파일이 이미 존재합니다."
fi

# 6. Docker 확인
echo ""
echo "🐳 Docker 확인 중..."
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker 설치 확인 완료"

    # Docker 실행 여부 확인
    read -p "Docker로 바로 실행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Docker 실행 중..."
        echo "=================================="
        docker-compose up --build
    else
        echo ""
        echo "✅ 설치 완료!"
        echo ""
        echo "실행 방법:"
        echo "  cd $INSTALL_DIR"
        echo "  docker-compose up --build"
    fi
else
    echo "⚠️  Docker가 설치되어 있지 않습니다."
    echo ""
    echo "Python으로 직접 실행하시겠습니까?"
    read -p "(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "📦 Python 패키지 설치 중..."
        pip install -r requirements.txt

        echo ""
        echo "🚀 게임 실행 중..."
        echo "=================================="
        python play.py
    else
        echo ""
        echo "✅ 설치 완료!"
        echo ""
        echo "실행 방법:"
        echo "  cd $INSTALL_DIR"
        echo "  pip install -r requirements.txt"
        echo "  python play.py"
    fi
fi
