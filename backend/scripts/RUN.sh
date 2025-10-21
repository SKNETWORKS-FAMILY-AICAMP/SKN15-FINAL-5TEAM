#!/bin/bash

echo "============================================"
echo "🎮 Kime Chat Agent - Quick Start"
echo "============================================"
echo ""

# 1. 구조 테스트
echo "📋 [1/3] 시스템 구조 테스트 중..."
python3 run_simple_test.py > /tmp/test_output.txt 2>&1

if [ $? -eq 0 ]; then
    echo "✅ 시스템 정상 작동"
    tail -5 /tmp/test_output.txt
else
    echo "❌ 오류 발생"
    cat /tmp/test_output.txt
    exit 1
fi

echo ""
echo "============================================"
echo "📡 [2/3] API 서버 시작 방법"
echo "============================================"
echo ""
echo "방법 1: LLM 없이 실행 (추천 - 빠름)"
echo "  export USE_LLM=false"
echo "  python3 run_api_server.py"
echo ""
echo "방법 2: OpenAI 사용"
echo "  export OPENAI_API_KEY='your-key'"
echo "  export USE_LLM=true"
echo "  python3 run_api_server.py"
echo ""
echo "============================================"
echo "🧪 [3/3] API 테스트 예시"
echo "============================================"
echo ""
echo "1. 세션 생성:"
echo "  curl -X POST http://localhost:8000/api/session/create \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"session_id\":\"test\",\"scenario_file\":\"cutscene5_akaza_encounter.json\"}'"
echo ""
echo "2. 메시지 전송:"
echo "  curl -X POST http://localhost:8000/api/message \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"session_id\":\"test\",\"message\":\"계속\"}'"
echo ""
echo "============================================"
echo "✅ 준비 완료! 위 명령어로 서버를 시작하세요."
echo "============================================"
