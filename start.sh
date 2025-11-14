#!/bin/bash
# KIME Chat 개발 환경 시작 스크립트
# 사용법: ./start.sh

set -e

echo "============================================================"
echo "🚀 KIME Chat 개발 환경 시작"
echo "============================================================"

# 1. 기존 컨테이너 정리
echo "📦 기존 컨테이너 정리 중..."
docker-compose down

# 2. 컨테이너 시작
echo "🐳 Docker 컨테이너 시작 중..."
docker-compose up -d

# 3. 백엔드 준비 대기
echo "⏳ 백엔드 서버 준비 대기 중..."
MAX_RETRIES=30
RETRY_COUNT=0

while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ 백엔드 서버 시작 실패 (타임아웃)"
        exit 1
    fi
    echo "   시도 ${RETRY_COUNT}/${MAX_RETRIES}..."
    sleep 2
done

echo "✅ 백엔드 서버 준비 완료!"

# 4. 서비스 상태 확인
echo ""
echo "============================================================"
echo "📊 서비스 상태"
echo "============================================================"
docker-compose ps

# 5. 브라우저 열기
echo ""
echo "============================================================"
echo "🌐 브라우저 열기"
echo "============================================================"
echo "   프론트엔드: http://localhost"
echo "   API 문서: http://localhost:8000/docs"
echo ""

# macOS에서 브라우저 열기
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🖥️  macOS에서 브라우저를 엽니다..."
    open http://localhost
    sleep 1
    open http://localhost:8000/docs
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Linux에서 브라우저를 엽니다..."
    xdg-open http://localhost 2>/dev/null || echo "   수동으로 브라우저를 열어주세요: http://localhost"
    xdg-open http://localhost:8000/docs 2>/dev/null || echo "   수동으로 브라우저를 열어주세요: http://localhost:8000/docs"
else
    echo "⚠️  자동으로 브라우저를 열 수 없습니다."
    echo "   수동으로 열어주세요: http://localhost"
fi

echo ""
echo "============================================================"
echo "✅ KIME Chat 개발 환경이 시작되었습니다!"
echo "============================================================"
echo ""
echo "📝 유용한 명령어:"
echo "   - 로그 확인: docker-compose logs -f"
echo "   - 백엔드 로그: docker-compose logs -f backend"
echo "   - 중지: docker-compose down"
echo "   - 재시작: docker-compose restart"
echo ""
